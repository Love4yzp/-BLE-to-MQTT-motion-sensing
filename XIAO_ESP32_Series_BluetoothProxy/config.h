/**
 * ============================================================================
 * Configuration File - Pre-fill WiFi and MQTT Settings
 * 配置文件 - 预填 WiFi 和 MQTT 设置
 * ============================================================================
 * 
 * For testing or batch flashing, fill in your settings below.
 * 用于测试或批量烧录，请在下方填写您的配置。
 * 
 * These values will be used as defaults in the WiFiManager portal.
 * 这些值将作为 WiFiManager 配置门户的默认值。
 * 
 * IMPORTANT: Do not commit this file with real credentials to git!
 * 重要：不要将包含真实凭据的此文件提交到 git！
 */

#ifndef CONFIG_H
#define CONFIG_H

// =============================================================================
// WiFi Configuration | WiFi 配置
// =============================================================================

// Uncomment and fill in to enable WiFi pre-configuration
// 取消注释并填写以启用 WiFi 预配置
// #define WIFI_SSID     "your-wifi-ssid"
// #define WIFI_PASSWORD "your-wifi-password"

// =============================================================================
// MQTT Configuration | MQTT 配置
// =============================================================================

// Uncomment and fill in to enable MQTT pre-configuration
// 取消注释并填写以启用 MQTT 预配置
// #define MQTT_SERVER   "192.168.100.10"
// #define MQTT_PORT     "1883"
// #define MQTT_USER     "adc"
// #define MQTT_PASSWORD "123"

// =============================================================================
// Example Configuration (for local testing)
// 示例配置（用于本地测试）
// =============================================================================
// 
#define WIFI_SSID     "MPR114993468245000005-2.4G"
#define WIFI_PASSWORD "missionconnected"
#define MQTT_SERVER   "192.168.100.10"
#define MQTT_PORT     "1883"
#define MQTT_USER     "adc"
#define MQTT_PASSWORD "123"

#endif // CONFIG_H
