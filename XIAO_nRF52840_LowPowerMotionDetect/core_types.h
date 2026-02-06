#pragma once

/**
 * Application Types | 应用类型定义
 *
 * Shared vocabulary types used across all firmware modules.
 * 所有固件模块共享的类型定义。
 *
 * Include hierarchy: Layer 1 (depends only on config.h, bsp_pins.h)
 * 包含层级：第 1 层（仅依赖 config.h、bsp_pins.h）
 */

#include <stdint.h>
#include "config.h"
#include "bsp_pins.h"

// =============================================================================
// BTHome Protocol Constants | BTHome 协议常量
// =============================================================================

// BTHome v2 device info byte: trigger-based device, no encryption
// BTHome v2 设备信息字节：触发型设备，无加密
#define BTHOME_DEVICE_INFO    0x44

// BTHome binary motion sensor object ID
// BTHome 二进制运动传感器对象 ID
#define BTHOME_BINARY_MOTION  0x21

// BLE GAP AD type for service data (16-bit UUID)
// BLE GAP AD 类型：服务数据（16 位 UUID）
#define BLE_GAP_AD_TYPE_SERVICE_DATA 0x16

// =============================================================================
// Timing Constants | 时间常量
// =============================================================================

// Broadcast duration derived from config.h
// 广播时长，派生自 config.h
static const unsigned long BROADCAST_DURATION = BROADCAST_DURATION_MS;

// =============================================================================
// Flash Storage Constants | Flash 存储常量
// =============================================================================

#define CONFIG_MAGIC 0x53454544  // "SEED" in hex
#define CONFIG_ADDR  0x7F000     // Last 4KB page of internal flash
                                 // 内部 Flash 最后 4KB 页

// =============================================================================
// Runtime Configuration | 运行时配置
// =============================================================================

/**
 * Config structure for flash storage
 * Flash 存储的配置结构
 *
 * WARNING: Do NOT reorder or change field types.
 *          Existing flash data depends on this exact layout.
 * 警告：不要重新排列字段或更改类型。
 *       现有 Flash 数据依赖于此确切布局。
 */
struct RuntimeConfig {
    uint32_t magic;           // Magic number to validate stored config
                              // 用于验证存储配置的魔数
    uint8_t threshold;        // IMU wake-up threshold (0x02-0x3F)
                              // IMU 唤醒阈值
    uint16_t tailWindow;      // Tail window duration (ms)
                              // 尾随窗口时长（毫秒）
    int8_t txPower;           // BLE TX power (dBm)
                              // BLE 发射功率
};

// =============================================================================
// State Machine Types | 状态机类型
// =============================================================================

/**
 * Run state for the main loop state machine
 * 主循环状态机的运行状态
 */
enum class RunState : uint8_t {
    Broadcasting,   // BLE advertising active | BLE 广播中
    TailWindow,     // Post-broadcast wait for continuous motion | 广播后等待连续运动
    UsbIdle         // USB mode: BLE stopped, waiting for motion | USB 模式：BLE 已停止，等待运动
};

/**
 * Loop bookkeeping state
 * 循环记录状态
 */
struct LoopState {
    RunState runState;                // Current state machine state | 当前状态机状态
    bool usbMode;                     // USB powered (no sleep) | USB 供电（不睡眠）
    bool usbModeChecked;              // USB mode detection done | USB 模式检测完成
    bool lastInt1State;               // Previous INT1 pin state (USB polling) | 上一次 INT1 引脚状态
    unsigned long lastAdvertiseTime;  // Last broadcast start timestamp | 上次广播开始时间戳
    unsigned long tailWindowStart;    // Tail window start timestamp | 尾随窗口开始时间戳
};

/**
 * Runtime telemetry for diagnostics
 * 运行时遥测数据，用于诊断
 */
struct Telemetry {
    RunState runState;                // Tracked state for timing | 用于计时的跟踪状态
    unsigned long lastStateChangeMs;  // Last state transition timestamp | 上次状态转换时间戳
    unsigned long lastStatusMs;       // Last status print timestamp | 上次状态打印时间戳
    uint32_t motionCount;             // Total motion events since boot | 启动以来的运动事件总数
    uint32_t advertiseMs;             // Cumulative advertising time (ms) | 累计广播时间
    uint32_t tailWindowMs;            // Cumulative tail window time (ms) | 累计尾随窗口时间
    uint32_t idleMs;                  // Cumulative idle time (ms) | 累计空闲时间
    bool lastInt1Level;               // Snapshot of INT1 pin for telemetry display
    uint8_t isrCount;                 // Snapshot of ISR count for telemetry display
};

// =============================================================================
// Application Context | 应用上下文
// =============================================================================

/**
 * Central state bundle passed to all modules by reference.
 * Owns all mutable application state. No scattered globals.
 * 传递给所有模块的中心状态包（通过引用传递）。
 * 拥有所有可变应用状态，无分散的全局变量。
 */
struct AppContext {
    RuntimeConfig config;         // Active configuration | 当前配置
    LoopState loop;               // State machine bookkeeping | 状态机记录
    Telemetry telem;              // Runtime statistics | 运行时统计
    bool usbPowered;              // Latched USB detection result | 锁存的 USB 检测结果
    char deviceName[20];          // BLE device name "SeeedUA-XXYY" | BLE 设备名称
    char macStr[18];              // MAC string "AA:BB:CC:DD:EE:FF" | MAC 地址字符串
};
