# SeeedUA 智慧零售后端服务

FastAPI + MQTT 后端服务，提供产品映射管理、网关管理和实时事件监控。

## 快速启动

```bash
cd backend

# 安装依赖（使用 uv）
uv sync

# 编辑 .env 配置 MQTT 地址等（参考 .env.example）
cp .env.example .env

# 启动服务（默认端口 8080）
uv run python main.py

# 或使用 uvicorn（开发模式）
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

打开浏览器访问: http://localhost:8080

## 配置

通过 `.env` 文件或环境变量配置（参见 `config.py` — Pydantic BaseSettings）：

```bash
MQTT_BROKER=localhost      # MQTT 服务器地址
MQTT_PORT=1883             # MQTT 端口
DEDUP_WINDOW=2.0           # 去重时间窗口（秒）
SENSOR_TIMEOUT=5.0         # 传感器超时（秒），超时后视为放下
SERVER_HOST=0.0.0.0        # 监听地址
SERVER_PORT=8080           # 服务端口
```

## 功能

### Web 界面

- **产品映射表**: 添加/编辑/删除 MAC → 产品 → 视频 映射
- **网关管理**: 查看在线网关、设置位置标签、远程识别（LED 闪烁）
- **实时事件**: 查看传感器事件、播放触发、网关上线等

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/products` | 获取所有产品映射 |
| POST | `/api/products` | 添加产品映射 |
| PUT | `/api/products/{mac}` | 更新产品映射 |
| DELETE | `/api/products/{mac}` | 删除产品映射 |
| GET | `/api/gateways` | 获取所有网关 |
| PUT | `/api/gateways/{id}/label` | 更新网关标签 |
| POST | `/api/gateways/{id}/identify` | 触发网关 LED 闪烁 |
| GET | `/api/events` | 获取事件日志 |
| GET | `/api/mqtt/status` | 获取 MQTT 连接状态 |

### MQTT Topics

| Topic | 方向 | 说明 |
|-------|------|------|
| `bthome/+/state` | 订阅 | 传感器状态 |
| `gateway/+/info` | 订阅 | 网关信息上报 |
| `gateway/{id}/cmd` | 发布 | 网关命令（identify） |
| `screen/{id}/play` | 发布 | 播放指令 |

## 数据文件

```
backend/
├── data/
│   ├── product_map.csv   # 产品映射表
│   └── gateways.json     # 网关信息
```

### product_map.csv 格式

```csv
mac,sku,name,video,screen
c1f93e1d937c,UA-HOVR-001,UA HOVR 跑鞋,hovr_promo.mp4,screen-01
```

## 部署流程

1. 启动 MQTT Broker（如 Mosquitto）
2. 启动本服务
3. 烧录网关固件，配置 WiFi 和 MQTT
4. 网关上线后，在 Web 界面设置位置标签
5. 烧录传感器固件，贴到商品上
6. 在 Web 界面添加产品映射（MAC → 视频）
7. 拿起商品测试播放触发

## 播放器集成

当检测到拿起事件，服务会发布 MQTT 消息：

```
Topic: screen/{screen_id}/play
Payload: {"video": "xxx.mp4", "sku": "UA-HOVR-001", "name": "UA HOVR 跑鞋"}
```

播放器订阅对应 topic 即可接收播放指令。
