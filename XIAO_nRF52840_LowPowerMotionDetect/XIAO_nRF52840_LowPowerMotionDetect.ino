/**
 * XIAO nRF52840 BTHome Motion Detect
 *
 * Low-power BLE motion sensor for smart retail.
 * Detects product pickup via IMU, broadcasts BTHome v2 over BLE.
 * 低功耗 BLE 运动传感器，用于智慧零售。
 * 通过 IMU 检测商品拿取，通过 BLE 广播 BTHome v2。
 *
 * Hardware: Seeed XIAO nRF52840 (built-in LSM6DS3 IMU)
 * Board:    Tools -> Board -> Seeed nRF52 Boards -> Seeed XIAO nRF52840
 * Baud:     115200
 *
 * @author limengdu
 */

#include "app.h"

static AppContext ctx;

void setup() {
    appSetup(ctx);
}

void loop() {
    appLoop(ctx);
}
