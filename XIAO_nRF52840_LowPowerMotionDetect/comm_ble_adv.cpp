#include <Arduino.h>
#include <bluefruit.h>
#include "comm_ble_adv.h"
#include "comm_bthome.h"
#include "core_types.h"

void commBleInit(AppContext& ctx) {
    Bluefruit.begin();

    uint8_t mac[6];
    Bluefruit.getAddr(mac);

    // Format MAC: "AA:BB:CC:DD:EE:FF"
    sprintf(ctx.macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
            mac[5], mac[4], mac[3], mac[2], mac[1], mac[0]);

    // Device name: "SeeedUA-XXYY" (last 4 hex digits of MAC)
    sprintf(ctx.deviceName, "SeeedUA-%02X%02X", mac[1], mac[0]);

    Bluefruit.setTxPower(ctx.config.txPower);
    Bluefruit.setName(ctx.deviceName);
}

void commBleStartAdvertising(bool motionDetected) {
    Bluefruit.Advertising.stop();
    Bluefruit.Advertising.clearData();

    uint8_t serviceData[8];
    uint8_t len = commBthomeBuildMotionPacket(serviceData, sizeof(serviceData), motionDetected);

    Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
    Bluefruit.Advertising.addName();
    Bluefruit.Advertising.addData(BLE_GAP_AD_TYPE_SERVICE_DATA, serviceData, len);
    // Fast advertising: 20ms interval | 快速广播：20ms 间隔
    Bluefruit.Advertising.setInterval(32, 32);
    Bluefruit.Advertising.start(0);
}

void commBleStop() {
    Bluefruit.Advertising.stop();
    delay(10);
}
