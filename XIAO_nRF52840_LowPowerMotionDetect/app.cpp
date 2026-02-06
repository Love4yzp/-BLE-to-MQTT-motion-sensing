#include <Arduino.h>
#include "app.h"
#include "app_types.h"
#include "debug.h"
#include "pins.h"
#include "leds.h"
#include "flash_store.h"
#include "imu.h"
#include "isr_events.h"
#include "ble_adv.h"
#include "power.h"
#include "cli_at.h"
#include "telemetry.h"

// Helper: transition run state and update telemetry
// 辅助：转换运行状态并更新遥测
static void transitionState(AppContext& ctx, RunState next, unsigned long nowMs) {
    telemetryOnTransition(ctx.telem, next, nowMs);
    ctx.loop.runState = next;
}

void appSetup(AppContext& ctx) {
    // Detect USB power first (determines Serial init)
    // 先检测 USB 供电（决定是否初始化串口）
    ctx.usbPowered = powerIsUsbPowered();

#if DEBUG_ENABLED
    Serial.begin(115200);
    delay(100);
#else
    if (ctx.usbPowered) {
        Serial.begin(115200);
        delay(100);
    }
#endif

    // Load config from flash (or use compile-time defaults)
    // 从 flash 加载配置（或使用编译时默认值）
    ctx.config = {
        CONFIG_MAGIC,
        IMU_WAKEUP_THRESHOLD,
        TAIL_WINDOW_MS,
        BLE_TX_POWER
    };
    if (flashLoadConfig(ctx.config)) {
        DEBUG_PRINTLN("Config loaded from flash");
    } else {
        DEBUG_PRINTLN("Using default config");
    }

    if (ctx.usbPowered || DEBUG_ENABLED) {
        Serial.println();
        Serial.println(F("========================================"));
        Serial.println(F("  XIAO nRF52840 BTHome Motion Detect"));
        Serial.println(F("========================================"));
        Serial.println();
    }

    // Check wake-up reason | 检查唤醒原因
    uint32_t resetReason = NRF_POWER->RESETREAS;
    // Bit 16: GPIO wake from System OFF
    bool wokeFromSleep = (resetReason & 0x10000);
    NRF_POWER->RESETREAS = resetReason;

    DEBUG_PRINT("Reset reason: 0x");
    DEBUG_PRINTLN(resetReason);
    DEBUG_PRINTLN(wokeFromSleep ? ">>> Woke from sleep (motion triggered) <<<" : ">>> Normal power-on <<<");
    DEBUG_PRINTLN("");

    powerEnableDCDC();

    // Initialize LEDs | 初始化 LED
    ledsInit();
    ledsSetGreen(true);
    delay(wokeFromSleep ? 30 : 100);
    ledsSetGreen(false);

    // Initialize BLE (gets MAC, sets name + TX power)
    // 初始化 BLE（获取 MAC，设置名称和发射功率）
    bleInit(ctx);

    DEBUG_PRINT("MAC Address: ");
    DEBUG_PRINTLN(ctx.macStr);
    DEBUG_PRINT("Device Name: ");
    DEBUG_PRINTLN(ctx.deviceName);
    DEBUG_PRINTLN("");

    // Initialize IMU | 初始化 IMU
    if (!imuInit()) {
        DEBUG_PRINTLN("IMU initialization failed!");
        while (1) {
            ledsSetBlue(true);
            delay(500);
            ledsSetBlue(false);
            delay(500);
        }
    }
    DEBUG_PRINTLN("IMU initialization successful!");

    imuAttachInterrupt();
    imuConfigureWake(ctx.config.threshold);

    // Start advertising based on wake-up reason
    // 根据唤醒原因开始广播
    if (wokeFromSleep) {
        DEBUG_PRINTLN("Motion wake!");
        bleStartAdvertising(true);
    } else {
        DEBUG_PRINTLN("Normal power-on, starting advertising...");
        bleStartAdvertising(true);
    }

    // Initialize loop state | 初始化循环状态
    ctx.loop = { RunState::Broadcasting, false, false, false, millis(), 0 };
    telemetryReset(ctx.telem, ctx.loop.lastAdvertiseTime, RunState::Broadcasting);

    DEBUG_PRINTLN("Ready. Will sleep after broadcast.");

    if (ctx.usbPowered) {
        cliInit(ctx);
    }
}

void appLoop(AppContext& ctx) {
    unsigned long nowMs = millis();

    // USB mode detection (once) | USB 模式检测（一次）
    if (!ctx.loop.usbModeChecked) {
        ctx.loop.usbMode = powerIsUsbPowered();
        ctx.loop.usbModeChecked = true;
        if (ctx.loop.usbMode) {
            Serial.println(F(">>> USB Power Mode: Sleep disabled, CLI active"));
            Serial.print(F("INT1 pin state: "));
            Serial.println(digitalRead(IMU_INT1_PIN) ? "HIGH" : "LOW");

            if (digitalRead(IMU_INT1_PIN) == HIGH) {
                imuClearLatchedInterrupt();
                delay(10);
                isrFetchAndClearEvents();  // Discard ISR events from boot latch
                Serial.print(F("Cleared latch, INT1 now: "));
                Serial.println(digitalRead(IMU_INT1_PIN) ? "HIGH (still stuck!)" : "LOW (OK)");
            }

            ctx.loop.lastInt1State = digitalRead(IMU_INT1_PIN);
        }
    }

    // USB mode: CLI + polling telemetry
    // USB 模式：CLI + 轮询遥测
    if (ctx.loop.usbMode) {
        cliPoll(ctx);
        telemetryPrintIfDue(ctx, nowMs);
    }

    // Check ISR events | 检查 ISR 事件
    uint32_t events = isrFetchAndClearEvents();
    bool motionEvent = (events & EVT_MOTION) != 0;

    // USB fallback: if INT1 is HIGH (latched) but ISR missed the edge,
    // read WAKE_UP_SRC to check for real wake-up event and clear latch.
    // USB 回退：如果 INT1 为高（已锁存）但 ISR 未捕获上升沿，
    // 读取 WAKE_UP_SRC 确认真实唤醒事件并清除锁存。
    if (ctx.loop.usbMode && !motionEvent && digitalRead(IMU_INT1_PIN)) {
        uint8_t src = imuClearLatchedInterrupt();
        // Bit 3 (WU_IA) = wake-up event detected
        if (src & 0x08) {
            motionEvent = true;
        }
    }

    if (motionEvent) {
        uint8_t wakeUpSrc = imuClearLatchedInterrupt();

        if (ctx.loop.usbMode) {
            Serial.print(F("[MOTION] cnt="));
            Serial.print(isrGetInterruptCount());
            Serial.print(F(" src=0x"));
            Serial.print(wakeUpSrc, HEX);
            Serial.print(F(" tail="));
            Serial.println(ctx.loop.runState == RunState::TailWindow ? "Y" : "N");
        }

        ctx.telem.motionCount++;

        if (ctx.loop.runState == RunState::TailWindow) {
            bleStartAdvertising(true);
            transitionState(ctx, RunState::Broadcasting, nowMs);
        } else if (ctx.loop.usbMode) {
            bleStartAdvertising(true);
            transitionState(ctx, RunState::Broadcasting, nowMs);
        }

        ctx.loop.lastAdvertiseTime = nowMs;

        if (ctx.loop.usbMode) {
            ledsSetGreen(true);
            delay(30);
            ledsSetGreen(false);
        }
    }

    // State machine | 状态机
    if (ctx.loop.runState == RunState::Broadcasting) {
        if (nowMs - ctx.loop.lastAdvertiseTime > BROADCAST_DURATION) {
            bleStop();
            ctx.loop.tailWindowStart = nowMs;
            transitionState(ctx, RunState::TailWindow, nowMs);
        }
    } else if (ctx.loop.runState == RunState::TailWindow) {
        if (nowMs - ctx.loop.tailWindowStart > ctx.config.tailWindow) {
            if (ctx.loop.usbMode) {
                transitionState(ctx, RunState::UsbIdle, nowMs);
            } else {
                powerEnterSystemOff(ctx.config);
            }
        }
    }

    delay(10);
}
