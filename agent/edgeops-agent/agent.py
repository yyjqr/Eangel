import time
import json
from modules.monitor import collect_status
from modules.diagnose import diagnose_logs
from modules.healer import auto_heal
from modules.optimizer import auto_optimize
from modules.comm_mqtt import MqttClient

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

    # 内部状态（从 MEC 收到的最新状态）
    latest_mec_status = {}

    # 注册收到 MEC 消息的回调：处理并在必要时转发模型性能数据
    def _incoming(topic, payload):
        nonlocal latest_mec_status
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

