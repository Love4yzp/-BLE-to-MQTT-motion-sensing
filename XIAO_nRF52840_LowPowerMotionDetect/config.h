/**
 * ============================================================================
 * DEPLOYMENT CONFIGURATION | 部署配置
 * ============================================================================
 * 
 * >>> FOR DEPLOYMENT PERSONNEL - 供部署人员调整 <<<
 * 
 * Adjust these parameters based on product requirements.
 * 根据产品需求调整以下参数。
 * 
 * After modification, recompile and flash the firmware.
 * 修改后需重新编译并烧录固件。
 * 
 * ============================================================================
 */

#ifndef CONFIG_H
#define CONFIG_H

// =============================================================================
// 1. DEBUG MODE | 调试模式
// =============================================================================
//
// Set to 1 for Serial debug output (requires USB connection)
// 设为 1 启用串口调试输出（需要 USB 连接）
// Set to 0 for production (saves power, faster response)
// 设为 0 用于生产（省电，响应更快）
//
// WARNING: Debug mode adds ~50ms latency per message
// 警告：调试模式每条消息增加约 50ms 延迟
//
#define DEBUG_ENABLED  0  // 0=Production, 1=Debug

// =============================================================================
// 2. MOTION SENSITIVITY | 运动灵敏度
// =============================================================================
// 
// IMU wake-up threshold (0x01 - 0x3F, 6-bit value)
// IMU 唤醒阈值 (0x01 - 0x3F, 6位数值)
// 
// Formula: threshold_mg = IMU_WAKEUP_THRESHOLD * 31.25 mg (at ±2g scale)
// 公式: 阈值(毫g) = IMU_WAKEUP_THRESHOLD * 31.25 mg (±2g量程下)
//
// Examples | 示例:
//   0x02 =  62.5 mg  - Ultra sensitive (detects slight touch)
//                      超灵敏（轻触即触发）
//   0x05 = 156.3 mg  - High sensitive (light pickup)
//                      高灵敏（轻拿触发）
//   0x0A = 312.5 mg  - Medium (normal pickup) [DEFAULT]
//                      中等灵敏（正常拿起）[默认]
//   0x14 = 625.0 mg  - Low sensitive (firm pickup required)
//                      低灵敏（需用力拿起）
//   0x20 = 1000  mg  - Very low (strong motion only)
//                      非常低（仅强烈运动）
//
#define IMU_WAKEUP_THRESHOLD  0x0A  // Default: 0x0A (~312mg)

// =============================================================================
// 3. BROADCAST TIMING | 广播时序
// =============================================================================
//
// How long to broadcast BLE after motion detected (milliseconds)
// 检测到运动后广播 BLE 的时长（毫秒）
//
// Shorter = faster response but may miss slow gateways
// 越短 = 响应越快，但可能被慢网关错过
// Longer = more reliable but uses more power
// 越长 = 更可靠，但更耗电
//
// Recommended: 200-500ms
// 建议值: 200-500毫秒
//
#define BROADCAST_DURATION_MS  300  // Default: 300ms

// =============================================================================
// 4. TAIL WINDOW | 尾随窗口
// =============================================================================
//
// After broadcasting, wait this long for additional motion before sleeping.
// 广播后，等待此时长检测额外运动，然后再睡眠。
//
// Purpose: Merge rapid consecutive pickups into one wake cycle.
// 目的：将快速连续的拿起动作合并为一次唤醒周期。
//
// Shorter = saves power, but each motion triggers full wake cycle
// 越短 = 省电，但每次运动都触发完整唤醒周期
// Longer = smoother UX for "shake" gestures, uses more power
// 越长 = "晃动"手势体验更顺滑，但更耗电
//
// Recommended: 2000-5000ms
// 建议值: 2000-5000毫秒
//
#define TAIL_WINDOW_MS  3000  // Default: 3000ms (3 seconds)

// =============================================================================
// 5. BLE TX POWER | BLE 发射功率
// =============================================================================
//
// BLE transmission power level (dBm)
// BLE 发射功率等级 (dBm)
//
// Higher = longer range but more power consumption
// 越高 = 传输距离越远，但更耗电
//
// Valid values: -40, -20, -16, -12, -8, -4, 0, 4
// 有效值: -40, -20, -16, -12, -8, -4, 0, 4
//
// Recommended: 0 for indoor retail, 4 for larger spaces
// 建议值: 室内零售用 0，较大空间用 4
//
#define BLE_TX_POWER  4  // Default: 4 dBm

#endif // CONFIG_H
