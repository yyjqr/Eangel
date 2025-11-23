import json
import time
import paho.mqtt.client as mqtt

class MqttClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = mqtt.Client()
        self._user_callback = None

        # 用户名密码（可为空）
        if cfg.get("user"):
            self.client.username_pw_set(cfg["user"], cfg.get("password", ""))

        # 连接与循环
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_log = self._on_log

        # 尝试连接，若失败则重试几次以便排查网络/凭据问题
        retries = cfg.get("connect_retries", 3)
        retry_delay = cfg.get("retry_delay", 5)
        connected = False
        for attempt in range(1, retries + 1):
            try:
                print(f"[MQTT] Attempting to connect to {cfg.get('host')}:{cfg.get('port')} (attempt {attempt})")
                self.client.connect(cfg["host"], cfg["port"], 60)
                connected = True
                break
            except Exception as e:
                print(f"[MQTT] Connect attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(retry_delay)

        if not connected:
            print("[MQTT] Warning: could not establish connection to broker after retries. Will still start loop to allow later reconnects.")

        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        # 打印连接结果，便于排查 rc（0 表示成功）
        print(f"[MQTT] on_connect rc={rc}")
        if rc != 0:
            rc_meanings = {
                1: "Unacceptable protocol version",
                2: "Identifier rejected",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorised"
            }
            print(f"[MQTT] Connect failed: {rc_meanings.get(rc, 'Unknown error')} (rc={rc})")

        # 连接成功后订阅配置中的主题（或默认 MEC 主题）
        subs = self.cfg.get("subscribe_topics") or [
            "rsu/+/rsm/up",
            "rsu/+/om/status"
        ]
        for t in subs:
            try:
                client.subscribe(t)
            except Exception:
                pass

    def _on_message(self, client, userdata, msg):
        payload = msg.payload
        try:
            payload = payload.decode('utf-8')
            payload = json.loads(payload)
        except Exception:
            # keep raw string if not JSON
            try:
                payload = msg.payload.decode('utf-8')
            except Exception:
                payload = msg.payload

        if self._user_callback:
            try:
                self._user_callback(msg.topic, payload)
            except Exception:
                pass

    def _on_disconnect(self, client, userdata, rc):
        print(f"[MQTT] Disconnected (rc={rc})")

    def _on_log(self, client, userdata, level, buf):
        # 仅打印关键调试信息，避免过多日志
        print(f"[MQTT LOG] {buf}")

    def set_message_callback(self, func):
        """注册收到消息的回调，回调签名为 func(topic, payload)"""
        self._user_callback = func

    def publish(self, topic, msg):
        # 将 dict/列表等序列化为 JSON 字符串
        payload = msg
        if not isinstance(msg, (str, bytes)):
            try:
                payload = json.dumps(msg)
            except Exception:
                payload = str(msg)
        self.client.publish(topic, payload)

