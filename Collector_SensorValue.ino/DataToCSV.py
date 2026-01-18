import csv
import time
import statistics
from datetime import datetime
import json
import paho.mqtt.client as mqtt
import os

FILENAME = 'sensor_datalog.csv'
broker_address = "broker.hivemq.com"
topic = "leesu/sensor/data"

buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_motion = []

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Success Connection topic : {topic}")
    client.subscribe(topic)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        
        m = float(data.get("motion", 0))
        h = float(data.get("humidity", 0))
        t = float(data.get("temperature", 0))
        l = int(data.get("illuminance", 0))

        buffer_motion.append(m)
        buffer_hum.append(h)
        buffer_temp.append(t)
        buffer_lux.append(l)

        print(f"움직임{m}, 습도{h}%, 온도{t}, 조도{l}")

        if len(buffer_hum) >= 30:
            timestamp = datetime.now().strftime("%y-%m-%d %H:%M")

            avg_motion = round(statistics.mean(buffer_motion), 1)
            avg_hum = round(statistics.mean(buffer_hum), 1)
            avg_temp = round(statistics.mean(buffer_temp), 1)
            avg_lux = int(statistics.mean(buffer_lux) / 4)

            save_data = [timestamp, avg_motion, avg_hum, avg_temp, avg_lux]

            with open(FILENAME, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(save_data)

            buffer_motion.clear()
            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()

    except json.JSONDecodeError:
        print(f"에러: 들어온 데이터가 JSON이 아닙니다 -> {payload}")
    except Exception as e:
        print(f"에러 발생: {e}")       

if not os.path.exists(FILENAME):
    with open(FILENAME, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Movement', 'Humidity', 'Temperature', 'Illuminance'])

try:
    # Paho MQTT v2.x 대응
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    # Paho MQTT v1.x 대응
    client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"브로커({broker_address}) 연결 시도 중...")
    client.connect(broker_address, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n프로그램 종료")