import paho.mqtt.client as mqtt
import csv
import json
import os
from datetime import datetime

# 1. 설정
broker_address = "broker.hivemq.com"
topic = "leesu/sensor/data"
csv_filename = "sleep_data.csv"  # 이 파일명으로 통일됨

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Success Connection topic : {topic}")
    client.subscribe(topic)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print(f"Received message: {payload}")

        # JSON 파싱
        data = json.loads(payload)

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 데이터 추출 (없으면 None 처리)
        row = [
            current_time, 
            data.get('motion'), 
            data.get('humidity'), 
            data.get('temperature'), 
            data.get('illuminance')
        ]

        # 2. 변수명(csv_filename) 사용 + 엑셀 깨짐 방지(utf-8-sig)
        with open(csv_filename, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(row)
            print(f"저장 완료: {row}")

    except json.JSONDecodeError:
        print(f"에러: 들어온 데이터가 JSON이 아닙니다 -> {payload}")
    except Exception as e:
        print(f"에러 발생: {e}")

# 파일 헤더 생성 (변수명 통일)
if not os.path.exists(csv_filename):
    with open(csv_filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'motion', 'humidity', 'temperature', 'illuminance'])

# 3. Paho MQTT 최신 버전(2.x) 호환성 대응
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