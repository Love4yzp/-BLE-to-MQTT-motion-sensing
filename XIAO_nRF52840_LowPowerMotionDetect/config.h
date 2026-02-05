/**
 * ============================================================================
 * DEPLOYMENT CONFIGURATION | 部署配置
 * ============================================================================
 * 
 * >>> FOR DEPLOYMENT PERSONNEL - 供部署人员调整 <<<
 * 
 * Only TWO settings to configure:
 * 只需配置以下两项：
 * 
 * 1. SENSITIVITY_PRESET  - Motion detection sensitivity
 *                          运动检测灵敏度
 * 2. DEBUG_ENABLED       - Debug mode (for troubleshooting)
 *                          调试模式（用于排查问题）
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
// Choose a preset (1, 2, or 3):
// 选择预设模式（1、2 或 3）：
//
//   1 = HIGH SENSITIVITY | 高灵敏
//       - Triggers on light touch/pickup
//       - 轻触或轻拿即触发
//       - Best for: small/light products
//       - 适用于：小件/轻便商品
//       - Battery: ~6 months (200 triggers/day)
//       - 续航：约6个月（每天触发200次）
//
//   2 = STANDARD | 标准 [DEFAULT]
//       - Triggers on normal pickup
//       - 正常拿起时触发
//       - Best for: most retail products
//       - 适用于：大多数零售商品
//       - Battery: ~10 months (200 triggers/day)
//       - 续航：约10个月（每天触发200次）
//
//   3 = LOW SENSITIVITY | 低灵敏
//       - Requires firm pickup to trigger
//       - 需要明显拿起动作才触发
//       - Best for: vibrating environments, heavy products
//       - 适用于：有震动的环境、重型商品
//       - Battery: ~12+ months (200 triggers/day)
//       - 续航：约12个月以上（每天触发200次）
//
#define SENSITIVITY_PRESET  2

// =============================================================================
// 2. DEBUG MODE | 调试模式
// =============================================================================
//
//   0 = PRODUCTION | 生产模式 [DEFAULT]
//       - No serial output, fastest response
//       - 无串口输出，响应最快
//
//   1 = DEBUG | 调试模式
//       - Serial output enabled (115200 baud)
//       - 启用串口输出（波特率 115200）
//       - Use for troubleshooting only
//       - 仅用于排查问题
//
#define DEBUG_ENABLED  0

// =============================================================================
// ^^^ DEPLOYMENT SETTINGS END HERE ^^^
// ^^^ 部署设置到此结束 ^^^
// =============================================================================
//
// >>> DO NOT MODIFY BELOW THIS LINE <<<
// >>> 请勿修改以下内容 <<<
//
// =============================================================================

// Preset configurations (do not modify)
#if SENSITIVITY_PRESET == 1
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

// Fixed timing (optimized, do not change)
#define BROADCAST_DURATION_MS  300

#endif // CONFIG_H
