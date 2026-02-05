/**
 * ============================================================================
 * Seeed HA Discovery BLE - Low Power Motion Detection Example
 * Seeed HA Discovery BLE - 低功耗运动检测示例
 * ============================================================================
 *
 * This example demonstrates how to:
 * 本示例展示如何：
 * 1. Detect motion via LSM6DS3 IMU Z-axis acceleration
 *    通过 LSM6DS3 IMU 的 Z 轴加速度检测运动
 * 2. Broadcast motion status to Home Assistant via BTHome protocol
 *    通过 BTHome 协议向 Home Assistant 广播运动状态
 * 3. Enter ultra-low power deep sleep (System OFF) when idle
 *    空闲时进入超低功耗深度睡眠（System OFF）
 * 4. Wake up automatically when motion is detected
 *    检测到运动时自动唤醒
 *
 * Hardware Requirements:
 * 硬件要求：
 * - Seeed XIAO nRF52840 (with built-in LSM6DS3 IMU)
 *   Seeed XIAO nRF52840（内置 LSM6DS3 IMU）
 *
 * Software Dependencies:
 * 软件依赖：
 * - Seeed nRF52 Boards (Adafruit BSP)
 *   Seeed nRF52 开发板包（Adafruit BSP）
 * - Seeed Arduino LSM6DS3 library
 *   Seeed Arduino LSM6DS3 库
 *
 * Board Selection in Arduino IDE:
 * Arduino IDE 中的开发板选择：
 * Tools -> Board -> Seeed nRF52 Boards -> Seeed XIAO nRF52840
 * 工具 -> 开发板 -> Seeed nRF52 Boards -> Seeed XIAO nRF52840
 *
 * Power Consumption:
 * 功耗：
 * - Deep Sleep: < 5 µA
 *   深度睡眠：< 5 µA
 * - Advertising: ~3 mA
 *   广播中：~3 mA
 *
 * IMPORTANT: Disconnect USB to measure actual power consumption!
 * 重要：测量实际功耗时必须断开 USB 连接！
 *
 * @author limengdu
 * @version 1.0.0
 */

#include <LSM6DS3.h>
#include <Wire.h>
#include <bluefruit.h>
#include "config.h"

// =============================================================================
// Debug Macros | 调试宏
// =============================================================================
#if DEBUG_ENABLED
  #define DEBUG_PRINT(x)    Serial.print(x)
  #define DEBUG_PRINTLN(x)  Serial.println(x)
  #define DEBUG_PRINTF(...) Serial.printf(__VA_ARGS__)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
  #define DEBUG_PRINTF(...)
#endif

// =============================================================================
// Hardware Pin Definitions | 硬件引脚定义
// =============================================================================

// IMU interrupt pin (INT1)
// IMU 中断引脚 (INT1)
#define IMU_INT1_PIN 11  // P0.11

// LED pin definitions (active LOW for Adafruit BSP)
// LED 引脚定义（Adafruit BSP 使用低电平点亮）
#define LED_BLUE_PIN  12
#define LED_GREEN_PIN 13

// =============================================================================
// BTHome Protocol Definitions | BTHome 协议定义
// =============================================================================

// BTHome v2 device info byte: trigger-based device, no encryption
// BTHome v2 设备信息字节：触发型设备，无加密
#define BTHOME_DEVICE_INFO    0x44

// BTHome binary motion sensor object ID
// BTHome 二进制运动传感器对象 ID
#define BTHOME_BINARY_MOTION  0x21

// BLE GAP AD type for service data (16-bit UUID)
// BLE GAP AD 类型：服务数据（16 位 UUID）
#define BLE_GAP_AD_TYPE_SERVICE_DATA 0x16

// =============================================================================
// Derived Constants (from config.h) | 派生常量（来自 config.h）
// =============================================================================
const unsigned long BROADCAST_DURATION = BROADCAST_DURATION_MS;
const unsigned long TAIL_WINDOW_DURATION = TAIL_WINDOW_MS;

// =============================================================================
// Global Variables | 全局变量
// =============================================================================

// IMU object (I2C address 0x6A)
// IMU 对象（I2C 地址 0x6A）
LSM6DS3 myIMU(I2C_MODE, 0x6A);

// Interrupt counter for wake-up detection
// 唤醒检测的中断计数器
volatile uint8_t interruptCount = 0;

// Motion interrupt flag for tail window handling
// 尾随窗口运动中断标志
volatile bool motionDetected = false;

// Device name and MAC address strings
// 设备名称和 MAC 地址字符串
char deviceName[20] = {0};
char macStr[18] = {0};  // "AA:BB:CC:DD:EE:FF"

// Timing variable for sleep countdown
// 睡眠倒计时计时变量
unsigned long lastAdvertiseTime = 0;

// =============================================================================
// Interrupt Service Routine | 中断服务程序
// =============================================================================

/**
 * IMU INT1 interrupt handler
 * IMU INT1 中断处理程序
 */
void int1ISR() {
    interruptCount++;
    motionDetected = true;
}

// =============================================================================
// LED Control Functions | LED 控制函数
// =============================================================================

/**
 * Set green LED state (active LOW)
 * 设置绿色 LED 状态（低电平点亮）
 */
void setGreenLed(bool on) {
    digitalWrite(LED_GREEN_PIN, on ? LOW : HIGH);
}

/**
 * Set blue LED state (active LOW)
 * 设置蓝色 LED 状态（低电平点亮）
 */
void setBlueLed(bool on) {
    digitalWrite(LED_BLUE_PIN, on ? LOW : HIGH);
}

/**
 * Turn off all LEDs
 * 关闭所有 LED
 */
void ledsOff() {
    setGreenLed(false);
    setBlueLed(false);
}

// =============================================================================
// Power Mode Detection | 供电模式检测
// =============================================================================

/**
 * Check if USB power is connected (VBUS present)
 * 检测是否连接 USB 供电（VBUS 存在）
 * 
 * @return true if USB powered, false if battery powered
 *         true 表示 USB 供电，false 表示电池供电
 */
bool isUsbPowered() {
    return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk);
}

// =============================================================================
// BTHome BLE Functions | BTHome BLE 函数
// =============================================================================

/**
 * Update BLE advertising data with motion state
 * 使用运动状态更新 BLE 广播数据
 * 
 * @param motionDetected true for motion=1, false for motion=0
 *                       true 表示 motion=1，false 表示 motion=0
 */
void updateAdvertising(bool motionDetected) {
    Bluefruit.Advertising.stop();
    Bluefruit.Advertising.clearData();
    
    // Build BTHome Service Data
    // 构建 BTHome 服务数据
    uint8_t serviceData[8];
    uint8_t len = 0;
    serviceData[len++] = 0xD2;  // UUID 0xFCD2 (little-endian)
    serviceData[len++] = 0xFC;
    serviceData[len++] = BTHOME_DEVICE_INFO;
    serviceData[len++] = BTHOME_BINARY_MOTION;
    serviceData[len++] = motionDetected ? 0x01 : 0x00;
    
    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addName();
    Bluefruit.Advertising.addData(BLE_GAP_AD_TYPE_SERVICE_DATA, serviceData, len);
    Bluefruit.Advertising.setInterval(32, 32);  // Fast advertising (20ms interval)
                                                 // 快速广播（20ms 间隔）
    Bluefruit.Advertising.start(0);
}

/**
 * Stop BLE advertising
 * 停止 BLE 广播
 */
void stopBLE() {
    Bluefruit.Advertising.stop();
    delay(10);
}

// =============================================================================
// IMU Wake-up Configuration | IMU 唤醒配置
// =============================================================================

/**
 * Configure IMU wake-up interrupt for ultra-low power mode
 * 为超低功耗模式配置 IMU 唤醒中断
 */
void setupWakeUpInterrupt() {
    // 1. Configure accelerometer: 26Hz, 2g (better responsiveness, still low power)
    //    12.5Hz = 0x10, 26Hz = 0x20, 52Hz = 0x30
    // 1. 配置加速度计：26Hz, 2g（更好的响应性，仍然低功耗）
    //    12.5Hz = 0x10, 26Hz = 0x20, 52Hz = 0x30
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL1_XL, 0x20);
    
    // 2. Disable gyroscope
    // 2. 关闭陀螺仪
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_CTRL2_G, 0x00);
    
    // 3. Enable interrupts with latching (LIR)
    //    Bit 7: INTERRUPTS_ENABLE=1, Bit 0: LIR=1 (latch until WAKE_UP_SRC read)
    // 3. 启用中断并锁存 (LIR)
    //    位 7: INTERRUPTS_ENABLE=1, 位 0: LIR=1 (锁存直到读取 WAKE_UP_SRC)
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_TAP_CFG1, 0x81);
    
    // 4. Wake-up threshold + enable Activity state machine
    //    Bit 6: SLEEP_ON_OFF=1 (enable state machine), Bits 5:0=threshold
    //    Uses IMU_WAKEUP_THRESHOLD from deployment config section
    // 4. 唤醒阈值 + 启用活动状态机
    //    位 6: SLEEP_ON_OFF=1 (启用状态机), 位 5:0=阈值
    //    使用部署配置区的 IMU_WAKEUP_THRESHOLD
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_WAKE_UP_THS, 0x40 | (IMU_WAKEUP_THRESHOLD & 0x3F));
    
    // 5. Wake-up duration
    // 5. 唤醒持续时间
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_WAKE_UP_DUR, 0x00);
    
    // 6. Route wake-up to INT1
    // 6. 将唤醒路由到 INT1
    myIMU.writeRegister(LSM6DS3_ACC_GYRO_MD1_CFG, 0x20);
    
    // Clear interrupt
    // 清除中断
    uint8_t reg;
    myIMU.readRegister(&reg, LSM6DS3_ACC_GYRO_WAKE_UP_SRC);
}

// =============================================================================
// Deep Sleep Function | 深度睡眠函数
// =============================================================================

/**
 * Enter System OFF deep sleep mode
 * Uses SoftDevice API for proper shutdown
 * 进入 System OFF 深度睡眠模式
 * 使用 SoftDevice API 进行正确关闭
 */
void goToSleep() {
    DEBUG_PRINTLN(">>> Sleep");
    Serial.flush();
    
    // Stop BLE advertising
    // 停止 BLE 广播
    Bluefruit.Advertising.stop();
    delay(10);
    
    ledsOff();
    
    // Single short LED pulse to indicate sleep (non-blocking)
    // 单次短 LED 脉冲表示睡眠（非阻塞）
    setBlueLed(true);
    delay(50);
    setBlueLed(false);
    
    // Configure IMU wake-up interrupt
    // 配置 IMU 唤醒中断
    setupWakeUpInterrupt();
    delay(10);
    
    // Detach Arduino interrupt before clearing
    // 清除前先断开 Arduino 中断
    detachInterrupt(digitalPinToInterrupt(IMU_INT1_PIN));
    
    // Clear any pending/latched interrupt right before sleep
    // 睡眠前清除任何待处理/锁存的中断
    uint8_t dummy;
    myIMU.readRegister(&dummy, LSM6DS3_ACC_GYRO_WAKE_UP_SRC);
    
    // Shutdown I2C
    // 关闭 I2C
    Wire.end();
    
    // Shutdown Serial
    // 关闭串口
    Serial.end();
    
    // Configure wake-up pin using SoftDevice API
    // 使用 SoftDevice API 配置唤醒引脚
    nrf_gpio_cfg_sense_input(IMU_INT1_PIN, NRF_GPIO_PIN_PULLDOWN, NRF_GPIO_PIN_SENSE_HIGH);
    
    // Set LED pins HIGH (off)
    // 设置 LED 引脚为高电平（关闭）
    nrf_gpio_cfg_output(LED_GREEN_PIN);
    nrf_gpio_cfg_output(LED_BLUE_PIN);
    nrf_gpio_pin_set(LED_GREEN_PIN);
    nrf_gpio_pin_set(LED_BLUE_PIN);
    
    // Enter System OFF immediately
    // 立即进入 System OFF
    sd_power_system_off();
    
    // Code never reaches here
    // 代码永远不会执行到这里
    while(1) { __WFE(); }
}

// =============================================================================
// Arduino Main Program | Arduino 主程序
// =============================================================================

void setup() {
#if DEBUG_ENABLED
    Serial.begin(115200);
    delay(100);
#endif

    DEBUG_PRINTLN("");
    DEBUG_PRINTLN("========================================");
    DEBUG_PRINTLN("  XIAO nRF52840 BTHome Motion Detect");
    DEBUG_PRINTLN("========================================");
    DEBUG_PRINTLN("");

    // =========================================================================
    // Check wake-up reason | 检查唤醒原因
    // =========================================================================
    
    // Read reset reason register
    // 读取复位原因寄存器
    uint32_t resetReason = NRF_POWER->RESETREAS;
    bool wokeFromSleep = (resetReason & 0x10000);  // Bit 16: GPIO wake from System OFF
                                                    // Bit 16: 从 System OFF GPIO 唤醒
    
    // Clear reset reason (write 1 to clear)
    // 清除复位原因（写 1 清除）
    NRF_POWER->RESETREAS = resetReason;
    
    DEBUG_PRINT("Reset reason: 0x");
    DEBUG_PRINTLN(resetReason);
    DEBUG_PRINTLN(wokeFromSleep ? ">>> Woke from sleep (motion triggered) <<<" : ">>> Normal power-on <<<");
    DEBUG_PRINTLN("");

    // Enable DC-DC converter for efficiency
    // 启用 DC-DC 转换器以提高效率
    NRF_POWER->DCDCEN = 1;

    // =========================================================================
    // Initialize LEDs | 初始化 LED
    // =========================================================================
    
    pinMode(LED_GREEN_PIN, OUTPUT);
    pinMode(LED_BLUE_PIN, OUTPUT);
    ledsOff();

    // Quick LED flash to indicate startup
    // 快速 LED 闪烁表示启动
    setGreenLed(true);
    delay(wokeFromSleep ? 30 : 100);
    setGreenLed(false);

    // =========================================================================
    // Initialize BLE and get MAC address | 初始化 BLE 并获取 MAC 地址
    // =========================================================================
    
    Bluefruit.begin();
    uint8_t mac[6];
    Bluefruit.getAddr(mac);
    
    // Format MAC address string (AA:BB:CC:DD:EE:FF)
    // 格式化 MAC 地址字符串
    sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X", 
            mac[5], mac[4], mac[3], mac[2], mac[1], mac[0]);
    
    // Device name uses last 4 digits of MAC
    // 设备名称使用 MAC 后 4 位
    sprintf(deviceName, "SeeedUA-%02X%02X", mac[1], mac[0]);
    
    DEBUG_PRINT("MAC Address: ");
    DEBUG_PRINTLN(macStr);
    DEBUG_PRINT("Device Name: ");
    DEBUG_PRINTLN(deviceName);
    DEBUG_PRINTLN("");

    // =========================================================================
    // Configure IMU interrupt | 配置 IMU 中断
    // =========================================================================
    
    pinMode(IMU_INT1_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(IMU_INT1_PIN), int1ISR, RISING);

    // =========================================================================
    // Initialize IMU | 初始化 IMU
    // =========================================================================
    
    if (myIMU.begin() != 0) {
        DEBUG_PRINTLN("IMU initialization failed!");
        // Blue LED continuous blink indicates error
        // 蓝色 LED 持续闪烁表示错误
        while (1) {
            setBlueLed(true);
            delay(500);
            setBlueLed(false);
            delay(500);
        }
    }
    DEBUG_PRINTLN("IMU initialization successful!");

    // =========================================================================
    // Configure BLE advertising | 配置 BLE 广播
    // =========================================================================
    
    Bluefruit.setTxPower(BLE_TX_POWER);
    Bluefruit.setName(deviceName);
    
    // Build initial BTHome Service Data (motion=1)
    // 构建初始 BTHome 服务数据（motion=1）
    uint8_t serviceData[8];
    uint8_t len = 0;
    serviceData[len++] = 0xD2;  // UUID 0xFCD2 (little-endian)
    serviceData[len++] = 0xFC;
    serviceData[len++] = BTHOME_DEVICE_INFO;
    serviceData[len++] = BTHOME_BINARY_MOTION;
    serviceData[len++] = 0x01;  // Motion detected
                                // 检测到运动
    
    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addName();
    Bluefruit.Advertising.addData(BLE_GAP_AD_TYPE_SERVICE_DATA, serviceData, len);
    Bluefruit.Advertising.setInterval(160, 160);

    // =========================================================================
    // Start based on wake-up reason | 根据唤醒原因启动
    // =========================================================================
    
    if (wokeFromSleep) {
        // Woke from sleep = motion detected, start advertising immediately
        // 从睡眠唤醒 = 检测到运动，立即开始广播
        DEBUG_PRINTLN("Motion wake!");
        
        // Fast advertising (20ms interval) for quick detection
        // 快速广播（20ms 间隔）以便快速检测
        Bluefruit.Advertising.setInterval(32, 32);
        Bluefruit.Advertising.start(0);
        
        lastAdvertiseTime = millis();
    } else {
        // Normal power-on, also start advertising
        // 正常上电，也开始广播
        DEBUG_PRINTLN("Normal power-on, starting advertising...");
        Bluefruit.Advertising.start(0);
        lastAdvertiseTime = millis();
    }

    DEBUG_PRINTLN("Ready. Will sleep after broadcast.");
}

void loop() {
    static bool inTailWindow = false;
    static unsigned long tailWindowStart = 0;
    static bool usbMode = false;
    static bool usbModeChecked = false;
    
    // Check power mode once at startup (USB detection)
    // 启动时检测一次供电模式
    if (!usbModeChecked) {
        usbMode = isUsbPowered();
        usbModeChecked = true;
        if (usbMode) {
            DEBUG_PRINTLN(">>> USB Power Mode: Sleep disabled");
        }
    }
    
    // Always check motion first (critical for responsiveness)
    // 始终优先检查运动（响应性关键）
    if (motionDetected) {
        noInterrupts();
        motionDetected = false;
        interrupts();
        
        if (inTailWindow) {
            // Motion during tail window: restart advertising
            // 尾随窗口期间检测到运动：重新开始广播
            updateAdvertising(true);
            inTailWindow = false;
        }
        // Extend/reset the broadcast timer
        // 延长/重置广播计时器
        lastAdvertiseTime = millis();
        
        // Visual feedback in USB mode (since we don't sleep)
        // USB 模式下的视觉反馈（因为不会睡眠）
        if (usbMode) {
            setGreenLed(true);
            delay(30);
            setGreenLed(false);
        }
    }
    
    // State machine
    // 状态机
    if (!inTailWindow) {
        // Broadcasting state: check if broadcast duration elapsed
        // 广播状态：检查广播时长是否已过
        if (millis() - lastAdvertiseTime > BROADCAST_DURATION) {
            stopBLE();
            inTailWindow = true;
            tailWindowStart = millis();
        }
    } else {
        // Tail window state: check if tail window elapsed
        // 尾随窗口状态：检查尾随窗口是否已过
        if (millis() - tailWindowStart > TAIL_WINDOW_DURATION) {
            if (usbMode) {
                // USB mode: don't sleep, just wait for next motion
                // USB 模式：不睡眠，等待下一次运动
                inTailWindow = false;
                // Keep BLE stopped, will restart on next motion
                // 保持 BLE 停止，下次运动时重启
            } else {
                // Battery mode: enter deep sleep
                // 电池模式：进入深度睡眠
                goToSleep();
            }
        }
    }
    
    delay(10);
}
