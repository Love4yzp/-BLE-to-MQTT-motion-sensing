# BLE-MQTT 网关示例

将 BTHome BLE 广播转发到 MQTT 服务器的网关固件，配合 XIAO nRF52840 运动检测设备使用。

## 功能特性

- 持续扫描 BTHome 设备广播
- 将运动状态转发到 MQTT 服务器
- WiFi 强制门户配网（WiFiManager）
- WiFi 和 MQTT 自动重连
- LED 状态指示
- **多开发板支持**，自动检测引脚配置
- **网关识别功能**：按按钮或远程命令触发 LED 闪烁，方便现场定位
- **自动上报网关信息**：上线时自动发布 gateway_id、MAC、IP 等信息

## 支持的开发板

| 开发板 | LED 引脚 | BOOT 按钮 | WiFi |
|--------|----------|-----------|------|
| XIAO ESP32-C3 | GPIO10 (D10) | GPIO9 | 2.4GHz |
| XIAO ESP32-S3 | GPIO21 (D21) | GPIO0 | 2.4GHz |
| XIAO ESP32-C6 | GPIO15 (D15) | GPIO9 | 2.4GHz |
| XIAO ESP32-C5 | GPIO27 | GPIO9 | 2.4GHz + 5GHz (WiFi 6) |

## 硬件要求

- 支持的 XIAO ESP32 开发板之一（C3、S3、C6 或 C5）
- USB-C 数据线

## 软件依赖

### Arduino IDE 设置

1. **开发板管理器**：添加 ESP32 开发板
   - URL：`https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
   - 安装：**esp32** by Espressif Systems

2. **开发板选择**：
   ```
   工具 → 开发板 → ESP32 Arduino → 选择你的 XIAO 开发板：
   - XIAO_ESP32C3
   - XIAO_ESP32S3
   - XIAO_ESP32C6
   - XIAO_ESP32C5
   ```

3. **分区方案**：
   ```
   工具 → Partition Scheme → Minimal SPIFFS (1.9MB APP with OTA/190KB SPIFFS)
   ```

### 依赖库

通过 Arduino 库管理器安装：

| 库名称 | 作者 | 用途 |
|--------|------|------|
| WiFiManager | tzapu | WiFi 强制门户配网 |
| PubSubClient | Nick O'Leary | MQTT 客户端 |
| ArduinoJson | Benoit Blanchon | JSON 序列化 |

注：BLE 功能使用 ESP32 内置库，无需额外安装。

## 使用方法

### 1. 首次配网

1. 烧录固件后，设备会创建 WiFi 热点 `SeeedUA-Gateway`
2. 用手机或电脑连接该热点
3. 自动弹出配网页面（或访问 http://192.168.4.1）
4. 填写配置：
   - **WiFi 名称和密码**
   - **MQTT Server**：MQTT 服务器地址
   - **MQTT Port**：端口，默认 1883
   - **MQTT User**：用户名（可选）
   - **MQTT Password**：密码（可选）
5. 点击保存，设备自动重启并连接

### 2. 重新配网

如需修改配置：
1. 设备上电后 **5 秒内按住 BOOT 按钮**
2. 设备进入配网模式，LED 快闪
3. 连接热点重新配置

### 3. 正常运行

- 设备自动扫描 `SeeedUA-` 开头的 BTHome 设备
- 收到数据后转发到 MQTT

## MQTT 消息格式

### Topic

```
bthome/{mac_address}/state
```

示例：`bthome/c1f93e1d937c/state`

### Payload (JSON)

```json
{
  "motion": true,
  "rssi": -65,
  "gateway_id": "gw-1A2B"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| motion | boolean | true=检测到运动, false=静止 |
| rssi | integer | 信号强度 (dBm) |
| gateway_id | string | 网关标识，用于后端去重与路由 |

## 后端去重与映射建议

- 去重：以 `mac + 时间窗口(0.5s~2s)` 去重，避免多网关重复触发
- 路由：优先选择 RSSI 最强的网关上报（可用于就近屏幕触发）
- 映射：后端使用 `mac -> SKU -> 视频` 的映射表进行播放

## 网关识别与管理

### 网关信息上报

网关上线或被识别时，会发布自身信息：

**Topic**: `gateway/{gateway_id}/info`

**Payload**:
```json
{
  "gateway_id": "gw-1A2B",
  "action": "online",
  "board": "XIAO ESP32-C6",
  "ip": "192.168.1.50",
  "mac": "aa:bb:cc:dd:ee:ff"
}
```

| action 值 | 触发时机 |
|-----------|----------|
| online | 网关连接 MQTT 时 |
| identify | 识别模式触发时 |
| info | 后端请求信息时 |

### 识别网关（现场定位）

**方式 1：按按钮（现场操作）**

正常运行时**短按 BOOT 按钮**（< 1 秒），LED 会极快闪烁 5 秒，同时发布 identify 消息。

部署流程：
1. 把网关放到目标位置（如"货架A"）
2. 短按 BOOT 按钮
3. 后端收到 `{"gateway_id": "gw-1A2B", "action": "identify", ...}`
4. 在后台把 `gw-1A2B` 标记为"货架A"

**方式 2：远程命令（后台操作）**

向指定网关发送 identify 命令，让它的 LED 闪烁：

**Topic**: `gateway/{gateway_id}/cmd`

**Payload**:
```json
{"cmd": "identify"}
```

也可请求网关重新上报信息：
```json
{"cmd": "info"}
```

### 收集所有网关

后端订阅 `gateway/+/info`，即可收集所有网关的信息，用于：
- 生成设备清单
- 打印标签
- 建立映射表

## LED 指示

| 状态 | LED 行为 |
|------|---------|
| 配网模式 | 快闪 (200ms) |
| 连接中 | 慢闪 (1s) |
| 正常运行 | 常亮 |
| 收到数据 | 短暂熄灭 |
| **识别模式** | **极快闪 (100ms)，持续 5 秒** |

## 串口输出示例

```
========================================
  XIAO ESP32 BLE-MQTT Gateway
========================================

Board: XIAO ESP32-C5
LED Pin: GPIO27
BOOT Button: GPIO9

Loaded MQTT config: 192.168.1.100:1883
[WiFi] Hold BOOT button within 5s to reconfigure
[WiFi] Connected!
[WiFi] IP: 192.168.1.50
[MQTT] Connecting to 192.168.1.100:1883
[MQTT] Connected!
[BLE] Initializing NimBLE...
[BLE] NimBLE initialization complete
[BLE] Starting scan...

========================================
  Initialization Complete!
========================================

Gateway ready, scanning for BTHome devices...

MQTT Topic Format: bthome/{mac}/state
Payload: {"motion":true/false,"rssi":-XX,"gateway_id":"gw-XXXX"}

[BLE] SeeedUA-937C (c1:f9:3e:1d:93:7c) RSSI:-45 Motion:Detected
[MQTT] -> bthome/c1f93e1d937c/state: {"motion":true,"rssi":-45,"gateway_id":"gw-1A2B"}
[BLE] SeeedUA-937C (c1:f9:3e:1d:93:7c) RSSI:-47 Motion:Clear
[MQTT] -> bthome/c1f93e1d937c/state: {"motion":false,"rssi":-47,"gateway_id":"gw-1A2B"}
```

## Home Assistant 集成

### 方式 1：MQTT 传感器

在 `configuration.yaml` 中添加：

```yaml
mqtt:
  binary_sensor:
    - name: "SeeedUA-937C Motion"
      state_topic: "bthome/c1f93e1d937c/state"
      device_class: motion
      value_template: "{{ 'ON' if value_json.motion else 'OFF' }}"
      json_attributes_topic: "bthome/c1f93e1d937c/state"
      json_attributes_template: "{{ {'rssi': value_json.rssi, 'gateway_id': value_json.gateway_id} | tojson }}"
```

### 方式 2：MQTT Discovery（自动发现）

可以在 ESP32 代码中添加 HA MQTT Discovery 消息，设备会自动出现在 Home Assistant 中。

## 架构图

```
┌─────────────────┐     BLE      ┌─────────────────┐    WiFi/MQTT    ┌─────────────────┐
│                 │  ─────────>  │                 │  ───────────>   │                 │
│  XIAO nRF52840  │   BTHome     │  XIAO ESP32     │                 │  MQTT Broker    │
│  (运动检测)      │   广播       │  (BLE 网关)     │                 │  (服务器)        │
│                 │              │                 │                 │                 │
└─────────────────┘              └─────────────────┘                 └─────────────────┘
                                                                            │
                                                                            │ MQTT
                                                                            ▼
                                                                     ┌─────────────────┐
                                                                     │                 │
                                                                     │ Home Assistant  │
                                                                     │                 │
                                                                     └─────────────────┘
```

## 配置选项

| 参数 | 位置 | 说明 |
|------|------|------|
| GATEWAY_NAME | 代码 | WiFi AP 名称 |
| LED_PIN | 代码 | 内置 LED GPIO |
| scan_params | 代码 | BLE 扫描间隔/窗口 |

## 故障排除

### WiFi 连接失败
- 确保 WiFi 名称和密码正确
- ESP32-C5 支持 2.4GHz 和 5GHz（WiFi 6）

### MQTT 连接失败
- 检查 MQTT 服务器地址和端口
- 确认服务器是否需要用户名密码
- 查看串口输出的错误码

### 收不到 BLE 数据
- 确保 nRF52840 设备在附近且正在广播
- 检查设备名称是否以 `SeeedUA-` 开头
- 尝试重启两个设备

### 进入配网模式
- 上电后 5 秒内按住 BOOT 按钮
- LED 会开始快速闪烁

### MQTT 错误码

| 错误码 | 含义 |
|--------|------|
| -4 | 连接超时 |
| -3 | 连接丢失 |
| -2 | 连接失败 |
| -1 | 已断开 |
| 1 | 协议错误 |
| 2 | 客户端 ID 错误 |
| 3 | 服务不可用 |
| 4 | 凭据错误 |
| 5 | 未授权 |

## 许可证

SeeedHADiscoveryBLE 库的一部分。MIT 许可证。
