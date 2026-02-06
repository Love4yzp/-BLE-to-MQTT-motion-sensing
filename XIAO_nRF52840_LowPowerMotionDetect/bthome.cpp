#include "bthome.h"
#include "app_types.h"

uint8_t bthomeBuildMotionPacket(uint8_t* buf, uint8_t bufSize, bool motionDetected) {
    if (bufSize < 5) return 0;

    uint8_t len = 0;
    buf[len++] = 0xD2;                // UUID 0xFCD2 (little-endian low byte)
    buf[len++] = 0xFC;                // UUID 0xFCD2 (little-endian high byte)
    buf[len++] = BTHOME_DEVICE_INFO;  // 0x44: trigger-based, no encryption
    buf[len++] = BTHOME_BINARY_MOTION;// 0x21: binary motion sensor
    buf[len++] = motionDetected ? 0x01 : 0x00;

    return len;
}
