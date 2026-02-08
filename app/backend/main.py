"""
SeeedUA 智慧零售后端服务
FastAPI + MQTT + 简单 Web 界面
"""

import json
import csv
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import paho.mqtt.client as mqtt

from config import settings
from i18n import load_translations, get_translations, get_language_list


# ============================================
# 数据模型
# ============================================
class ProductMapping(BaseModel):
    mac: str
    sku: str
    name: str
    video: str
    screen: str
    timeout_s: Optional[float] = Field(default=None, ge=0.5, le=300)


class MQTTConfig(BaseModel):
    broker: str
    port: int


class GatewayInfo(BaseModel):
    gateway_id: str
    mac: str
    ip: str
    board: str
    label: str = ""  # 用户自定义标签，如"货架A"
    last_seen: str = ""


class AppConfigUpdate(BaseModel):
    dedup_window: Optional[float] = Field(default=None, ge=0.1, le=60)
    sensor_timeout: Optional[float] = Field(default=None, ge=0.5, le=300)
    sku_poll_ms: Optional[int] = Field(default=None, ge=100, le=10000)
    status_poll_ms: Optional[int] = Field(default=None, ge=500, le=60000)


# ============================================
# 全局状态
# ============================================
product_map: dict[str, ProductMapping] = {}
gateways: dict[str, GatewayInfo] = {}
recent_triggers: dict[str, float] = {}
sensor_states: dict[str, bool] = {}
sensor_last_seen: dict[str, float] = {}
sensor_meta: dict[str, dict] = {}
event_log: list[dict] = []
mqtt_client: Optional[mqtt.Client] = None
mqtt_connected = False
ui_runtime_config = {
    "sku_poll_ms": 500,
    "status_poll_ms": 5000,
}
DEFAULT_VIDEO_FILE = "demo_default.mp4"
DEFAULT_SCREEN_ID = "screen-01"


# ============================================
# 数据持久化
# ============================================
def load_product_map():
    """从 CSV 加载产品映射表"""
    global product_map
    product_map = {}

    if not settings.product_map_file.exists():
        return

    with open(settings.product_map_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mac = row["mac"].lower().replace(":", "")
            timeout_raw = (row.get("timeout_s") or "").strip()
            timeout_s = float(timeout_raw) if timeout_raw else None
            video = (row.get("video") or "").strip() or DEFAULT_VIDEO_FILE
            screen = (row.get("screen") or "").strip() or DEFAULT_SCREEN_ID
            product_map[mac] = ProductMapping(
                mac=mac,
                sku=row["sku"],
                name=row["name"],
                video=video,
                screen=screen,
                timeout_s=timeout_s,
            )
    print(f"[映射表] 已加载 {len(product_map)} 个产品")


def save_product_map():
    """保存产品映射表到 CSV"""
    settings.data_dir.mkdir(exist_ok=True)

    with open(settings.product_map_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["mac", "sku", "name", "video", "screen", "timeout_s"],
        )
        writer.writeheader()
        for p in product_map.values():
            writer.writerow(
                {
                    "mac": p.mac,
                    "sku": p.sku,
                    "name": p.name,
                    "video": p.video,
                    "screen": p.screen,
                    "timeout_s": "" if p.timeout_s is None else p.timeout_s,
                }
            )
    print(f"[映射表] 已保存 {len(product_map)} 个产品")


def load_gateways():
    """加载网关信息"""
    global gateways
    gateways = {}

    if not settings.gateways_file.exists():
        return

    with open(settings.gateways_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        for gw_id, info in data.items():
            gateways[gw_id] = GatewayInfo(**info)
    print(f"[网关] 已加载 {len(gateways)} 个网关")


def save_gateways():
    """保存网关信息"""
    settings.data_dir.mkdir(exist_ok=True)

    with open(settings.gateways_file, "w", encoding="utf-8") as f:
        data = {gw_id: gw.model_dump() for gw_id, gw in gateways.items()}
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_app_config() -> dict:
    return {
        "dedup_window": settings.dedup_window,
        "sensor_timeout": settings.sensor_timeout,
        "sku_poll_ms": ui_runtime_config["sku_poll_ms"],
        "status_poll_ms": ui_runtime_config["status_poll_ms"],
    }


def load_app_config():
    """加载运行时配置（覆盖默认设置）"""
    config_file = settings.data_dir / "app_config.json"
    if not config_file.exists():
        return

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        dedup_window = data.get("dedup_window")
        sensor_timeout = data.get("sensor_timeout")
        sku_poll_ms = data.get("sku_poll_ms")
        status_poll_ms = data.get("status_poll_ms")

        if isinstance(dedup_window, (int, float)) and dedup_window >= 0.1:
            settings.dedup_window = float(dedup_window)
        if isinstance(sensor_timeout, (int, float)) and sensor_timeout >= 0.5:
            settings.sensor_timeout = float(sensor_timeout)
        if isinstance(sku_poll_ms, int) and sku_poll_ms >= 100:
            ui_runtime_config["sku_poll_ms"] = sku_poll_ms
        if isinstance(status_poll_ms, int) and status_poll_ms >= 500:
            ui_runtime_config["status_poll_ms"] = status_poll_ms

        print("[配置] 已加载运行时配置")
    except Exception as e:
        print(f"[配置] 加载失败: {e}")


def save_app_config():
    """保存运行时配置"""
    settings.data_dir.mkdir(exist_ok=True)
    config_file = settings.data_dir / "app_config.json"

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(get_app_config(), f, indent=2, ensure_ascii=False)


def add_event(event_type: str, mac: str, details: dict):
    """添加事件日志"""
    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "type": event_type,
        "mac": mac,
        **details,
    }
    event_log.insert(0, event)
    # 只保留最近 100 条
    if len(event_log) > 100:
        event_log.pop()


def apply_demo_defaults(product: ProductMapping):
    product.video = (product.video or "").strip() or DEFAULT_VIDEO_FILE
    product.screen = (product.screen or "").strip() or DEFAULT_SCREEN_ID


# ============================================
# MQTT 处理
# ============================================
def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    global mqtt_connected
    if reason_code == 0:
        mqtt_connected = True
        print(f"[MQTT] 已连接到 {settings.mqtt_broker}:{settings.mqtt_port}")
        client.subscribe("bthome/+/state")
        client.subscribe("gateway/+/info")
    else:
        mqtt_connected = False
        print(f"[MQTT] 连接失败, rc={reason_code}")


def on_mqtt_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    global mqtt_connected
    mqtt_connected = False
    print(f"[MQTT] 已断开")


def on_mqtt_message(client, userdata, msg):
    topic = msg.topic

    try:
        payload = json.loads(msg.payload)
    except:
        return

    if topic.startswith("bthome/"):
        handle_sensor_event(topic, payload)
    elif topic.startswith("gateway/"):
        handle_gateway_event(topic, payload)


def handle_sensor_event(topic: str, payload: dict):
    """处理传感器事件"""
    parts = topic.split("/")
    if len(parts) != 3:
        return

    mac = parts[1].lower()
    motion = payload.get("motion", False)
    rssi = payload.get("rssi", 0)
    gateway_id = payload.get("gateway_id", "unknown")

    sensor_meta[mac] = {
        "gateway_id": gateway_id,
        "rssi": rssi,
        "motion": motion,
        "updated_at": time.time(),
    }

    if motion:
        sensor_last_seen[mac] = time.time()

    prev_state = sensor_states.get(mac)
    sensor_states[mac] = motion

    if prev_state == motion:
        return

    product = product_map.get(mac)
    sku = product.sku if product else ""
    name = product.name if product else ""

    if motion:
        add_event(
            "picked_up",
            mac,
            {"sku": sku, "name": name, "rssi": rssi, "gateway_id": gateway_id},
        )
        print(f"[提起] {sku or mac}")
    else:
        add_event(
            "put_down",
            mac,
            {"sku": sku, "name": name, "rssi": rssi, "gateway_id": gateway_id},
        )
        print(f"[放下] {sku or mac}")
        return

    now = time.time()
    if now - recent_triggers.get(mac, 0) < settings.dedup_window:
        return
    recent_triggers[mac] = now

    if not product:
        add_event("unknown", mac, {"gateway_id": gateway_id})
        print(f"[传感器] 未知 MAC: {mac}")
        return

    add_event(
        "play",
        mac,
        {
            "sku": product.sku,
            "name": product.name,
            "video": product.video,
            "screen": product.screen,
        },
    )
    print(f"[播放] {product.sku} → {product.screen}")

    if mqtt_client and mqtt_connected:
        play_msg = json.dumps(
            {"video": product.video, "sku": product.sku, "name": product.name}
        )
        mqtt_client.publish(f"screen/{product.screen}/play", play_msg)


def handle_gateway_event(topic: str, payload: dict):
    """处理网关事件"""
    gateway_id = payload.get("gateway_id", "")
    action = payload.get("action", "")

    if not gateway_id:
        return

    # 更新或创建网关记录
    if gateway_id in gateways:
        gw = gateways[gateway_id]
        gw.ip = payload.get("ip", gw.ip)
        gw.mac = payload.get("mac", gw.mac)
        gw.board = payload.get("board", gw.board)
        gw.last_seen = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        gateways[gateway_id] = GatewayInfo(
            gateway_id=gateway_id,
            mac=payload.get("mac", ""),
            ip=payload.get("ip", ""),
            board=payload.get("board", ""),
            last_seen=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    save_gateways()

    add_event("gateway", gateway_id, {"action": action, "ip": payload.get("ip", "")})
    print(f"[网关] {gateway_id} - {action}")


def start_mqtt():
    """启动 MQTT 客户端线程"""
    global mqtt_client

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.on_message = on_mqtt_message

    def mqtt_loop():
        while True:
            try:
                mqtt_client.connect(settings.mqtt_broker, settings.mqtt_port, 60)
                mqtt_client.loop_forever()
            except Exception as e:
                print(f"[MQTT] 连接错误: {e}, 5秒后重试...")
                time.sleep(5)

    thread = threading.Thread(target=mqtt_loop, daemon=True)
    thread.start()


def start_sensor_timeout_checker():
    def check_timeout():
        while True:
            time.sleep(1)
            now = time.time()
            for mac, last_seen in list(sensor_last_seen.items()):
                product = product_map.get(mac)
                timeout_s = (
                    product.timeout_s
                    if product and product.timeout_s is not None
                    else settings.sensor_timeout
                )
                if now - last_seen > timeout_s:
                    if sensor_states.get(mac):
                        sensor_states[mac] = False
                        sku = product.sku if product else ""
                        name = product.name if product else ""
                        add_event("timeout", mac, {"sku": sku, "name": name})
                        print(f"[超时] {sku or mac}")

    thread = threading.Thread(target=check_timeout, daemon=True)
    thread.start()


# ============================================
# FastAPI 应用
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_product_map()
    load_gateways()
    load_translations()
    load_app_config()
    start_mqtt()
    start_sensor_timeout_checker()
    yield
    # 关闭时
    if mqtt_client:
        mqtt_client.disconnect()


app = FastAPI(title="SeeedUA 智慧零售后端", lifespan=lifespan)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


# ============================================
# Web 界面
# ============================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "products": list(product_map.values()),
            "gateways": list(gateways.values()),
            "events": event_log[:20],
            "mqtt_connected": mqtt_connected,
            "mqtt_broker": settings.mqtt_broker,
            "mqtt_port": settings.mqtt_port,
        },
    )


# ============================================
# 产品映射 API
# ============================================
@app.get("/api/products")
async def get_products():
    return list(product_map.values())


@app.post("/api/products")
async def add_product(product: ProductMapping):
    mac = product.mac.lower().replace(":", "")
    product.mac = mac
    apply_demo_defaults(product)
    product_map[mac] = product
    save_product_map()
    return {"status": "ok", "product": product}


@app.put("/api/products/{mac}")
async def update_product(mac: str, product: ProductMapping):
    mac = mac.lower().replace(":", "")
    if mac not in product_map:
        raise HTTPException(status_code=404, detail="Product not found")
    product.mac = mac
    apply_demo_defaults(product)
    product_map[mac] = product
    save_product_map()
    return {"status": "ok", "product": product}


@app.delete("/api/products/{mac}")
async def delete_product(mac: str):
    mac = mac.lower().replace(":", "")
    if mac not in product_map:
        raise HTTPException(status_code=404, detail="Product not found")
    del product_map[mac]
    save_product_map()
    return {"status": "ok"}


# ============================================
# 网关管理 API
# ============================================
@app.get("/api/gateways")
async def get_gateways():
    return list(gateways.values())


@app.put("/api/gateways/{gateway_id}/label")
async def update_gateway_label(gateway_id: str, data: dict):
    if gateway_id not in gateways:
        raise HTTPException(status_code=404, detail="Gateway not found")
    gateways[gateway_id].label = data.get("label", "")
    save_gateways()
    return {"status": "ok"}


@app.post("/api/gateways/{gateway_id}/identify")
async def identify_gateway(gateway_id: str):
    """让指定网关 LED 闪烁"""
    if mqtt_client and mqtt_connected:
        mqtt_client.publish(
            f"gateway/{gateway_id}/cmd", json.dumps({"cmd": "identify"})
        )
        return {"status": "ok", "message": f"已发送识别命令到 {gateway_id}"}
    return {"status": "error", "message": "MQTT 未连接"}


# ============================================
# 事件日志 API
# ============================================
@app.get("/api/events")
async def get_events(limit: int = 50):
    return event_log[:limit]


@app.get("/api/sku-states")
async def get_sku_states():
    states = []
    for mac, motion in sensor_states.items():
        product = product_map.get(mac)
        last_seen = sensor_last_seen.get(mac)
        states.append(
            {
                "mac": mac,
                "sku": product.sku if product else "",
                "name": product.name if product else "",
                "active": motion,
                "last_seen": last_seen,
                "timeout_s": (
                    product.timeout_s
                    if product and product.timeout_s is not None
                    else settings.sensor_timeout
                ),
                "gateway_id": sensor_meta.get(mac, {}).get("gateway_id", "unknown"),
                "rssi": sensor_meta.get(mac, {}).get("rssi", 0),
            }
        )
    return states


@app.get("/api/sensors/unmapped")
async def get_unmapped_sensors(limit: int = 50):
    sensors = []
    all_macs = set(sensor_meta.keys()) | set(sensor_states.keys())

    for mac in all_macs:
        if mac in product_map:
            continue

        meta = sensor_meta.get(mac, {})
        last_seen = sensor_last_seen.get(mac, meta.get("updated_at"))
        sensors.append(
            {
                "mac": mac,
                "active": sensor_states.get(mac, False),
                "last_seen": last_seen,
                "gateway_id": meta.get("gateway_id", "unknown"),
                "rssi": meta.get("rssi", 0),
            }
        )

    sensors.sort(key=lambda x: x.get("last_seen") or 0, reverse=True)
    return sensors[:limit]


# ============================================
# MQTT 配置 API
# ============================================
@app.get("/api/mqtt/status")
async def get_mqtt_status():
    return {
        "connected": mqtt_connected,
        "broker": settings.mqtt_broker,
        "port": settings.mqtt_port,
    }


@app.get("/api/config")
async def get_config():
    return get_app_config()


@app.patch("/api/config")
async def patch_config(update: AppConfigUpdate):
    changed = False

    if update.dedup_window is not None:
        settings.dedup_window = update.dedup_window
        changed = True
    if update.sensor_timeout is not None:
        settings.sensor_timeout = update.sensor_timeout
        changed = True
    if update.sku_poll_ms is not None:
        ui_runtime_config["sku_poll_ms"] = update.sku_poll_ms
        changed = True
    if update.status_poll_ms is not None:
        ui_runtime_config["status_poll_ms"] = update.status_poll_ms
        changed = True

    if changed:
        save_app_config()

    return {"status": "ok", "config": get_app_config()}


# ============================================
# i18n API
# ============================================
@app.get("/api/i18n/{lang}")
async def get_i18n(lang: str):
    return get_translations(lang)


@app.get("/api/i18n/languages")
async def get_languages():
    return get_language_list()


# ============================================
# 入口
# ============================================
if __name__ == "__main__":
    import uvicorn

    print(f"\n{'=' * 50}")
    print(f"  SeeedUA Backend Server")
    print(f"  Open: http://localhost:{settings.server_port}")
    print(f"{'=' * 50}\n")
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
