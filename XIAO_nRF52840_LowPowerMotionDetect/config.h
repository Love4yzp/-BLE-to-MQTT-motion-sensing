/**
 * ============================================================================
 * DEPLOYMENT CONFIGURATION | 部署配置
 * ============================================================================
 * 
 * >>> FOR DEPLOYMENT PERSONNEL - 供部署人员调整 <<<
 * 
 * After modification, recompile and flash the firmware.
 * 修改后需重新编译并烧录固件。
 * 
 * ============================================================================
 */

#ifndef CONFIG_H
#define CONFIG_H

// =============================================================================
// 1. SENSITIVITY PRESET | 灵敏度预设
// =============================================================================
//
// Choose a preset (0, 1, 2, or 3):
// 选择预设模式（0、1、2 或 3）：
//
//   0 = ADVANCED | 高级模式
//       - Use custom values below
//       - 使用下方自定义参数
//
//   1 = HIGH SENSITIVITY | 高灵敏
//       - Triggers on light touch/pickup
//       - 轻触或轻拿即触发
//       - Battery: ~6 months (200 triggers/day)
//       - 续航：约6个月（每天触发200次）
//
//   2 = STANDARD | 标准 [DEFAULT]
//       - Triggers on normal pickup
//       - 正常拿起时触发
//       - Battery: ~10 months (200 triggers/day)
//       - 续航：约10个月（每天触发200次）
//
//   3 = LOW SENSITIVITY | 低灵敏
//       - Requires firm pickup to trigger
//       - 需要明显拿起动作才触发
//       - Battery: ~12+ months (200 triggers/day)
//       - 续航：约12个月以上（每天触发200次）
//
#define SENSITIVITY_PRESET  2

// =============================================================================
// 2. ADVANCED MODE SETTINGS | 高级模式设置
// =============================================================================
//
// >>> Only used when SENSITIVITY_PRESET = 0 <<<
// >>> 仅当 SENSITIVITY_PRESET = 0 时生效 <<<
//
// --- Motion Threshold | 运动阈值 ---
// Range: 0x02 ~ 0x3F (higher = less sensitive)
// 范围: 0x02 ~ 0x3F (越大越不灵敏)
// Formula: threshold = value * 31.25 mg
// 公式: 阈值 = 数值 * 31.25 毫g
//   0x02 =  ~62mg  (ultra sensitive | 超灵敏)
//   0x05 = ~156mg  (high | 高)
//   0x0A = ~312mg  (standard | 标准)
//   0x14 = ~625mg  (low | 低)
//   0x20 = ~1000mg (very low | 非常低)
//
#define CUSTOM_THRESHOLD     0x0A

// --- Tail Window | 尾随窗口 ---
// Range: 1000 ~ 10000 ms
// 范围: 1000 ~ 10000 毫秒
// Longer = better for continuous motion, but uses more power
// 越长 = 连续动作体验更好，但更耗电
//
#define CUSTOM_TAIL_WINDOW   3000

// --- TX Power | 发射功率 ---
// Valid: -40, -20, -16, -12, -8, -4, 0, 4 (dBm)
// 有效值: -40, -20, -16, -12, -8, -4, 0, 4 (dBm)
// Higher = longer range, more power consumption
// 越高 = 覆盖越远，但更耗电
//
#define CUSTOM_TX_POWER      4

// =============================================================================
// 3. FORCE BATTERY MODE | 强制电池模式
// =============================================================================
//
//   0 = AUTO DETECT | 自动检测 [DEFAULT]
//       - USB → USB mode (no sleep, CLI active)
//       - Battery → Battery mode (sleep enabled)
//       - USB → USB 模式（不睡眠，CLI 可用）
//       - 电池 → 电池模式（启用睡眠）
//
//   1 = FORCE BATTERY MODE | 强制电池模式
//       - USB powered but behaves as battery mode
//       - Use for power measurement with USB ammeter
//       - USB 供电但表现为电池模式（会进入 System OFF）
//       - 用于 USB 电流表测量低功耗
//
#define FORCE_BATTERY_MODE  0

// =============================================================================
// 4. DEBUG MODE | 调试模式
// =============================================================================
//
//   0 = PRODUCTION | 生产模式 [DEFAULT]
//   1 = DEBUG | 调试模式 (Serial 115200)
//
#define DEBUG_ENABLED  0

// =============================================================================
// ^^^ DEPLOYMENT SETTINGS END HERE ^^^
// ^^^ 部署设置到此结束 ^^^
// =============================================================================

// Preset configurations
#if SENSITIVITY_PRESET == 0
  // Advanced: use custom values
  #define IMU_WAKEUP_THRESHOLD  CUSTOM_THRESHOLD
  #define TAIL_WINDOW_MS        CUSTOM_TAIL_WINDOW
  #define BLE_TX_POWER          CUSTOM_TX_POWER
#elif SENSITIVITY_PRESET == 1
  // High sensitivity
  #define IMU_WAKEUP_THRESHOLD  0x05
  #define TAIL_WINDOW_MS        2000
  #define BLE_TX_POWER          4
#elif SENSITIVITY_PRESET == 3
  // Low sensitivity
  #define IMU_WAKEUP_THRESHOLD  0x14
  #define TAIL_WINDOW_MS        4000
  #define BLE_TX_POWER          0
#else
  // Standard (default, preset 2)
  #define IMU_WAKEUP_THRESHOLD  0x0A
  #define TAIL_WINDOW_MS        3000
  #define BLE_TX_POWER          4
#endif

// Fixed timing
#define BROADCAST_DURATION_MS  300

#endif // CONFIG_H
