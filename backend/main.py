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
from pydantic import BaseModel
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


# ============================================
# 全局状态
# ============================================
product_map: dict[str, ProductMapping] = {}
gateways: dict[str, GatewayInfo] = {}
recent_triggers: dict[str, float] = {}
sensor_states: dict[str, bool] = {}
sensor_last_seen: dict[str, float] = {}
event_log: list[dict] = []
mqtt_client: Optional[mqtt.Client] = None
mqtt_connected = False


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
            product_map[mac] = ProductMapping(
                mac=mac,
                sku=row["sku"],
                name=row["name"],
                video=row["video"],
                screen=row["screen"],
            )
    print(f"[映射表] 已加载 {len(product_map)} 个产品")


def save_product_map():
    """保存产品映射表到 CSV"""
    settings.data_dir.mkdir(exist_ok=True)

    with open(settings.product_map_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["mac", "sku", "name", "video", "screen"])
        writer.writeheader()
        for p in product_map.values():
            writer.writerow(p.model_dump())
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
                if now - last_seen > settings.sensor_timeout:
                    if sensor_states.get(mac):
                        sensor_states[mac] = False
                        product = product_map.get(mac)
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
    product_map[mac] = product
    save_product_map()
    return {"status": "ok", "product": product}


@app.put("/api/products/{mac}")
async def update_product(mac: str, product: ProductMapping):
    mac = mac.lower().replace(":", "")
    if mac not in product_map:
        raise HTTPException(status_code=404, detail="Product not found")
    product.mac = mac
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
        states.append(
            {
                "mac": mac,
                "sku": product.sku if product else "",
                "name": product.name if product else "",
                "active": motion,
            }
        )
    return states


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
