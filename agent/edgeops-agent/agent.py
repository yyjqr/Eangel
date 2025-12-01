import time
import json
import math
import os
from datetime import datetime
from modules.monitor import collect_status
from modules.diagnose import diagnose_logs
from modules.healer import auto_heal
from modules.optimizer import auto_optimize
from modules.comm_mqtt import MqttClient
from modules.perception import analyze_rsm, generate_map_geojson, save_map_html
from modules.websrv import start_server

ANOMALY_LOG_PATH = os.path.join(os.path.dirname(__file__), 'perception-abnormal.log')

def _normalize_heading(value):
    try:
        h = float(value)
    except (TypeError, ValueError):
        return None
    if h > 360.0 and h <= 36000.0:
        h = h / 100.0
    h = h % 360.0
    return h if h >= 0 else h + 360.0


def _angle_diff(a, b):
    if a is None or b is None:
        return None
    d = abs(float(a) - float(b)) % 360.0
    if d > 180.0:
        d = 360.0 - d
    return d


def _haversine_m(lon1, lat1, lon2, lat2):
    try:
        lon1, lat1, lon2, lat2 = map(float, (lon1, lat1, lon2, lat2))
    except (TypeError, ValueError):
        return None
    r = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _bearing_deg(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return None
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(y, x))
    bearing = (bearing + 360.0) % 360.0
    return bearing


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def main():
    cfg = load_config()
    # 先读取 device_id 与 topic_templates
    device_id = cfg.get("device_id", "unknown")
    mqtt_cfg = cfg.get("mqtt", {}).copy()
    topic_templates = mqtt_cfg.get("topic_templates", {})

    def _t(name, default):
        return topic_templates.get(name, default).format(device_id=device_id)

    # 格式化 subscribe_topics（支持在 config 中写入含 {device_id} 的模板）
    subs = []
    for t in mqtt_cfg.get("subscribe_topics", []):
        try:
            subs.append(t.format(device_id=device_id))
        except Exception:
            subs.append(t)

    if not subs:
        subs = [f"rsu/{device_id}/rsm/up", f"rsu/{device_id}/om/status"]

    mqtt_cfg["subscribe_topics"] = subs

    mqtt = MqttClient(mqtt_cfg)
    print("🔥 EdgeOps-Agent Started with JSON config...")

    # 启动本地 web 服务以便实时查看地图（数据文件由 agent 更新）
    geojson_path = f"/tmp/perception_latest_{device_id}.geojson"
    try:
        start_server(geojson_path)
        print(f"[WebSrv] started, open http://<this-device-ip>:5000/perception to view live map")
    except Exception as e:
        print('[WebSrv] failed to start:', e)

    # 内部状态（从 MEC 收到的最新状态）
    latest_mec_status = {}
    track_state = {}
    track_order = []
    track_state_limit = 1024

    # 注册收到 MEC 消息的回调：处理并在必要时转发模型性能数据
    def _incoming(topic, payload):
        nonlocal latest_mec_status, track_state, track_order
        print("⬅ MQTT IN:", topic, payload)

        # 更新最新状态（如果是 om/status）
        if topic.endswith('/om/status'):
            latest_mec_status = payload

        # 如果 payload 看起来包含模型性能指标，则转发到 model_perf 主题
        if isinstance(payload, dict):
            keys = set(payload.keys())
            if {'models', 'perf'} & keys or {'inference', 'latency', 'throughput'} & keys or 'model_id' in keys:
                model_topic = _t('model_perf', f"rsu/{device_id}/om/models/perf")
                mqtt.publish(model_topic, payload)

        # 如果是路侧感知 rsm/up 消息，则做基础感知分析并发布到 perception 主题，同时生成本地地图
        try:
            if topic.endswith('/rsm/up') or '/rsm/up' in topic:
                if isinstance(payload, dict):
                    analysis = analyze_rsm(payload)
                    objects = analysis.get('objects', []) or []
                    ts = analysis.get('timestamp', int(time.time()))
                    anomaly_logs = []

                    for obj in objects:
                        anomalies = obj.get('anomalies') or []
                        if not isinstance(anomalies, list):
                            anomalies = list(anomalies)
                        obj['anomalies'] = anomalies

                        oid = obj.get('ptcId') or obj.get('id')
                        pos = obj.get('pos') or {}
                        lon = pos.get('lon')
                        lat = pos.get('lat')
                        heading = obj.get('heading')
                        ptc_type = obj.get('ptcType')
                        frame_ts = obj.get('frame_ts') or ts

                        prev = track_state.get(oid) if oid else None

                        # Detect type change
                        if prev and prev.get('ptcType') is not None and ptc_type is not None:
                            try:
                                if int(prev['ptcType']) != int(ptc_type) and 'type_changed' not in anomalies:
                                    anomalies.append('type_changed')
                            except Exception:
                                pass

                        # Detect reverse heading based on movement direction
                        if prev and prev.get('lon') is not None and prev.get('lat') is not None and lon is not None and lat is not None:
                            dist = _haversine_m(prev['lon'], prev['lat'], lon, lat)
                            if dist is not None and dist > 0.5:
                                bearing = _bearing_deg(prev['lat'], prev['lon'], lat, lon)
                                heading_norm = _normalize_heading(heading)
                                diff = _angle_diff(bearing, heading_norm)
                                if diff is not None and diff > 130.0 and 'reverse_heading' not in anomalies:
                                    anomalies.append('reverse_heading')

                        if anomalies:
                            anomaly_logs.append({
                                'ts': frame_ts,
                                'id': oid,
                                'ptcType': ptc_type,
                                'heading': heading,
                                'lon': lon,
                                'lat': lat,
                                'anomalies': anomalies,
                                'speed': obj.get('speed')
                            })

                        if oid:
                            if oid in track_state:
                                try:
                                    track_order.remove(oid)
                                except ValueError:
                                    pass
                            track_state[oid] = {
                                'ptcType': ptc_type,
                                'lon': lon,
                                'lat': lat,
                                'ts': frame_ts,
                                'heading': heading
                            }
                            track_order.append(oid)
                            if len(track_order) > track_state_limit:
                                drop_id = track_order.pop(0)
                                track_state.pop(drop_id, None)

                    # Log anomalies after processing all objects
                    for item in anomaly_logs:
                        readable_ts = item['ts']
                        try:
                            if isinstance(readable_ts, (int, float)):
                                # assume seconds if too small
                                ts_val = readable_ts if readable_ts > 1e11 else readable_ts * 1000
                                readable_ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts_val / 1000.0))
                        except Exception:
                            pass
                        print(
                            "[Perception][Anomaly] ts={ts} id={oid} ptcType={ptype} heading={heading} speed={speed} pos=({lat},{lon}) anomalies={anom}".format(
                                ts=readable_ts,
                                oid=item['id'] or 'unknown',
                                ptype=item['ptcType'],
                                heading=item['heading'],
                                speed=item.get('speed'),
                                lat=item['lat'],
                                lon=item['lon'],
                                anom=','.join(item['anomalies'])
                            )
                        )

                    perception_topic = _t('perception', f"rsu/{device_id}/om/perception")
                    mqtt.publish(perception_topic, analysis)
                    # 写入最新 geojson 文件，web 服务会读取并实时展示
                    try:
                        gj = generate_map_geojson(objects)
                        geojson_path = f"/tmp/perception_latest_{device_id}.geojson"
                        with open(geojson_path, 'w', encoding='utf-8') as f:
                            json.dump(gj, f)
                        print(f"[Perception] published to {perception_topic}, geojson updated at {geojson_path}")
                    except Exception as e:
                        print('[Perception] failed to write geojson:', e)
        except Exception as e:
            print("[Perception] analysis error:", e)

    try:
        mqtt.set_message_callback(_incoming)
    except Exception:
        pass

    while True:
        status = collect_status()

        # 不再主动发布 MEC 的 rsm/up 或 om/status（MEC 设备会发布），
        # 但我们仍然发布本地诊断、heal、opt 结果到配置的模板。
        diag = diagnose_logs()
        if diag:
            diag_topic = _t("diagnosis", f"rsu/{device_id}/om/diagnosis")
            mqtt.publish(diag_topic, diag)
            print("⚠ AI Diagnosis:", diag)

        heal_result = auto_heal(status, diag)
        if heal_result:
            print("🔧 Auto-Heal:", heal_result)
            heal_topic = _t("heal", f"rsu/{device_id}/om/heal")
            mqtt.publish(heal_topic, heal_result)

        optimize_result = auto_optimize(status)
        if optimize_result:
            print("🚀 Auto-Optimize:", optimize_result)
            opt_topic = _t("opt", f"rsu/{device_id}/om/opt")
            mqtt.publish(opt_topic, optimize_result)

        time.sleep(cfg["interval"])

if __name__ == "__main__":
    main()

