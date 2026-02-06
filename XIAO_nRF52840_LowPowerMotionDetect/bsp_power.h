#pragma once

#include <stdint.h>

// Check if USB power is connected (VBUS present)
// 检测是否连接 USB 供电（VBUS 存在）
bool bspPowerIsUsb();

// Enable DC-DC converter for efficiency
// 启用 DC-DC 转换器以提高效率
void bspPowerEnableDCDC();

// Enter System OFF deep sleep mode (does not return)
// 进入 System OFF 深度睡眠模式（不会返回）
void bspPowerSystemOff(uint8_t wakePin);
