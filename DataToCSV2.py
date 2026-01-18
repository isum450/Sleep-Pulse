import serial
import csv
import time
import statistics
from datetime import datetime
import json
import paho.mqtt.client as mqtt

ser = serial.Serial('COM4', 115200)
FILENAME = 'sensor_datalog.csv'
broker_address = "broker.hivemq.com"
topic = "leesu/sensor/data"

try:
    # Paho MQTT v2.x 대응
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    # Paho MQTT v1.x 대응
    client = mqtt.Client()

try:
    print(f"브로커({broker_address}) 연결 시도 중...")
    client.connect(broker_address, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n프로그램 종료")

buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_motion = []

try:
    with open(FILENAME, 'x', newline='') as f:
        pass 
except FileExistsError:
    pass

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line: continue

            try:
                data = json.loads(line)
                m = float(data.get("motion", 0))  # 아두이노의 "motion"
                h = float(data.get("humidity", 0))
                t = float(data.get("temperature", 0))
                l = int(data.get("illuminance", 0))

                buffer_hum.append(h)
                buffer_temp.append(t)
                buffer_lux.append(l)

                print(f"움직임{m}, 습도{h}%, 온도{t}, 조도{l}")
            except json.JSONDecodeError:
                continue
            except ValueError:
                continue

        if len(buffer_hum) >= 30:
            timestamp = datetime.now().strftime("%y-%m-%d %H:%M")

            avg_hum = round(statistics.mean(buffer_hum), 1)
            avg_temp = round(statistics.mean(buffer_temp), 1)
            avg_lux = int(statistics.mean(buffer_lux) / 4)

            data_value_str = f"0,{avg_hum},{avg_temp},{avg_lux},0"

            with open(FILENAME, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, data_value_str])

            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()

        time.sleep(0.01)

except KeyboardInterrupt:
    ser.close()
    client.disconnect()