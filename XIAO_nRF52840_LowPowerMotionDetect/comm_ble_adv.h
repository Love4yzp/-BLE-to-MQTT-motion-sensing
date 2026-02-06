#pragma once

#include "core_types.h"

// Initialize BLE: Bluefruit.begin(), get MAC, format device name
// 初始化 BLE：Bluefruit.begin()，获取 MAC，格式化设备名称
void commBleInit(AppContext& ctx);

// Start or update BLE advertising with motion state
// 开始或更新 BLE 广播（带运动状态）
void commBleStartAdvertising(bool motionDetected);

// Stop BLE advertising | 停止 BLE 广播
void commBleStop();
