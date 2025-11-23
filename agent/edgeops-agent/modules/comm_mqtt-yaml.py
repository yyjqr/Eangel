print('mqtt')
import paho.mqtt.client as mqtt

class MqttClient:
    def __init__(self, cfg):
        self.client = mqtt.Client()
        self.client.username_pw_set(cfg["user"], cfg["password"])
        self.client.connect(cfg["host"], cfg["port"], 60)

    def publish(self, topic, msg):
        self.client.publish(topic, msg)

