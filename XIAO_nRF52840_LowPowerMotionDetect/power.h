#pragma once

#include "app_types.h"

// Check if USB power is connected (VBUS present)
// 检测是否连接 USB 供电（VBUS 存在）
bool powerIsUsbPowered();

// Enable DC-DC converter for efficiency
// 启用 DC-DC 转换器以提高效率
void powerEnableDCDC();

// Enter System OFF deep sleep mode (does not return)
// 进入 System OFF 深度睡眠模式（不会返回）
void powerEnterSystemOff(const RuntimeConfig& cfg);
