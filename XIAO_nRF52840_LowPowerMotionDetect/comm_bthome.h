#pragma once

#include <stdint.h>

// Build a BTHome v2 motion advertisement payload into buf.
// Returns number of bytes written (5 for motion packet).
// 构建 BTHome v2 运动广播数据到 buf，返回写入的字节数。
uint8_t commBthomeBuildMotionPacket(uint8_t* buf, uint8_t bufSize, bool motionDetected);
