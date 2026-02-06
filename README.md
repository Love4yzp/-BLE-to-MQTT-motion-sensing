# 智慧零售：分布式"拿起即播"互动展陈方案

IoT 系统：通过 BLE 运动传感器检测商品被拿起，触发屏幕播放对应视频。

## 系统架构

```
nRF52840 传感器 (BLE BTHome v2 广播)
    → ESP32 网关 (BLE 扫描 → MQTT 发布 bthome/{mac}/state)
    → MQTT Broker
    → FastAPI 后端 (去重 → 查询映射表 → 发布 screen/{id}/play)
    → 播放器 (播放视频)
```

## 组件

| 组件 | 目录 | 硬件 | 说明 |
|------|------|------|------|
| 运动传感器 | `XIAO_nRF52840_LowPowerMotionDetect/` | XIAO nRF52840 Sense | LSM6DS3 IMU 运动检测，BTHome v2 BLE 广播，深度睡眠 < 5µA |
| BLE-MQTT 网关 | `XIAO_ESP32_Series_BluetoothProxy/` | XIAO ESP32-C3/S3/C6/C5 | BLE 扫描 → WiFi → MQTT 转发 |
| 后端服务 | `backend/` | 任意服务器 | FastAPI + MQTT，产品映射、去重、播放指令 |

## 快速开始

### 1. 启动 MQTT Broker

```bash
# 使用 Mosquitto
mosquitto -c /usr/local/etc/mosquitto/mosquitto.conf
```

### 2. 启动后端

```bash
cd backend
uv sync                    # 安装依赖
cp .env.example .env       # 编辑 .env 设置 MQTT_BROKER 地址
uv run python main.py      # http://localhost:8080
```

### 3. 烧录网关固件

Arduino IDE 打开 `XIAO_ESP32_Series_BluetoothProxy/XIAO_ESP32_Series_BluetoothProxy.ino`，选择对应 ESP32 开发板，Minimal SPIFFS 分区，编译上传。首次启动连接 `SeeedUA-Gateway` 热点配网。

### 4. 烧录传感器固件

```bash
arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense XIAO_nRF52840_LowPowerMotionDetect/
arduino-cli upload --fqbn Seeeduino:nrf52:xiaonRF52840Sense -p /dev/cu.usbmodem1101 XIAO_nRF52840_LowPowerMotionDetect/
```

USB 连接时支持 AT 命令配置（`AT+HELP` 查看命令列表）。

### 5. 配置产品映射

在后端 Web 界面或直接编辑 `backend/data/product_map.csv`：

```csv
mac,sku,name,video,screen
f7dac49b63d1,UA-HOVR-001,UA HOVR 跑鞋,hovr_promo.mp4,screen-01
```

## MQTT Topic

| Topic | 方向 | Payload |
|-------|------|---------|
| `bthome/{mac}/state` | 网关 → 后端 | `{"motion": true, "rssi": -45, "gateway_id": "gw-B3E4"}` |
| `screen/{id}/play` | 后端 → 播放器 | `{"video": "hovr_promo.mp4", "sku": "UA-HOVR-001", "name": "UA HOVR 跑鞋"}` |
| `gateway/{id}/info` | 网关 → 后端 | `{"gateway_id", "mac", "ip", "board"}` |
| `gateway/{id}/cmd` | 后端 → 网关 | `{"cmd": "identify"}` |

## 硬件验证结果 (2026-02-06)

全链路端到端测试通过：

| 环节 | 结果 |
|------|------|
| 传感器 IMU 运动检测 | motion=98 次事件，WAKE_UP_SRC 寄存器正常 |
| BLE BTHome v2 广播 | `SeeedUA-63D1`，UUID 0xFCD2，motion=1 |
| ESP32 网关接收 | RSSI -38 ~ -54 dBm，37 条 MQTT 消息 |
| 后端去重 | 37 条传感器事件 → 1 条播放指令（2s 去重窗口） |
| 屏幕播放指令 | `screen/screen-01/play` 正确触发 |
| 超时检测 | 5s 无运动 → timeout 事件 |

## 致谢

ESP32 网关固件基于 [limengdu](https://github.com/limengdu) 的 [Seeed-Homeassistant-Discovery](https://github.com/Seeed-Projects/Seeed-Homeassistant-Discovery) 项目改造。

## 项目参考

- [Seeed HA Discovery BLE](https://github.com/Seeed-Projects/Seeed-Homeassistant-Discovery) — by [limengdu](https://github.com/limengdu)
- [BTHome 协议](https://bthome.io/)
