#pragma once

#include <stdint.h>

// Event bit definitions | 事件位定义
#define EVT_MOTION  (1u << 0)

// ISR function — passed to attachInterrupt()
// ISR 函数 — 传给 attachInterrupt()
void imuInt1Isr();

// Atomically read and clear all pending events
// 原子性读取并清除所有待处理事件
uint32_t isrFetchAndClearEvents();

// Get cumulative interrupt count (for telemetry display)
// 获取累计中断计数（用于遥测显示）
uint8_t isrGetInterruptCount();
