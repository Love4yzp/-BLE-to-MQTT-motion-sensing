#include <Arduino.h>
#include <bluefruit.h>
#include "power.h"
#include "app_types.h"
#include "pins.h"
#include "leds.h"
#include "imu.h"
#include "debug.h"

bool powerIsUsbPowered() {
    return (NRF_POWER->USBREGSTATUS & POWER_USBREGSTATUS_VBUSDETECT_Msk);
}

void powerEnableDCDC() {
    NRF_POWER->DCDCEN = 1;
}

void powerEnterSystemOff(const RuntimeConfig& cfg) {
    DEBUG_PRINTLN(">>> Sleep");
    Serial.flush();

    // Stop BLE | 停止 BLE
    Bluefruit.Advertising.stop();
    delay(10);

    ledsOff();

    // Blue LED pulse to indicate sleep | 蓝灯脉冲表示进入睡眠
    ledsSetBlue(true);
    delay(50);
    ledsSetBlue(false);

    // Configure IMU wake-up | 配置 IMU 唤醒
    imuConfigureWake(cfg.threshold);
    delay(10);

    // Detach interrupt, clear latch | 断开中断，清除锁存
    imuDetachInterrupt();
    imuClearLatchedInterrupt();

    // Shutdown peripherals | 关闭外设
    imuShutdown();
    Serial.end();

    // Configure wake-up pin (SoftDevice API)
    // 配置唤醒引脚（SoftDevice API）
    nrf_gpio_cfg_sense_input(IMU_INT1_PIN, NRF_GPIO_PIN_PULLDOWN, NRF_GPIO_PIN_SENSE_HIGH);

    // Set LED pins HIGH (off) via direct register
    // 通过寄存器直接设置 LED 引脚为 HIGH（关闭）
    nrf_gpio_cfg_output(LED_GREEN_PIN);
    nrf_gpio_cfg_output(LED_BLUE_PIN);
    nrf_gpio_pin_set(LED_GREEN_PIN);
    nrf_gpio_pin_set(LED_BLUE_PIN);

    // Enter System OFF | 进入 System OFF
    sd_power_system_off();

    // Never reached | 永远不会执行到此
    while (1) { __WFE(); }
}
