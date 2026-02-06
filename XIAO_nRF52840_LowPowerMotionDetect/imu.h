#pragma once

#include <stdint.h>
#include <stdbool.h>

// Initialize IMU hardware. Returns true on success.
// 初始化 IMU 硬件，成功返回 true。
bool imuInit();

// Configure IMU wake-up interrupt registers
// 配置 IMU 唤醒中断寄存器
void imuConfigureWake(uint8_t threshold);

// Attach/detach INT1 interrupt to ISR
// 挂接/断开 INT1 中断到 ISR
void imuAttachInterrupt();
void imuDetachInterrupt();

// Read WAKE_UP_SRC to clear latched interrupt, returns register value
// 读取 WAKE_UP_SRC 以清除锁存中断，返回寄存器值
uint8_t imuClearLatchedInterrupt();

// Shutdown I2C bus (call before System OFF)
// 关闭 I2C 总线（System OFF 前调用）
void imuShutdown();
