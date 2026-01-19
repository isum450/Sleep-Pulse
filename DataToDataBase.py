import json
import time #사용안해도댐 influx db 에서 시간 저장해주니까
import statistics
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "leesu/sensor/data"

#db 주소, 키비번, 이름 등등
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/"
INFLUX_TOKEN = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="
INFLUX_ORG = "personal project"
INFLUX_BUCKET = "sleep_pulse"
INFLUX_MEASUREMENT = "person1"
                    #측정 이름 여기서 바꿀수 있도록

#버퍼
buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_motion = []

try:
    #db접속
    db_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = db_client.write_api(write_options=SYNCHRONOUS)
                            #동기방식: 하나보내고 다음거 확인하는
    print("접속 성공")
except Exception as e:
    print("접속 실패")
    exit()

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Success Connection topic : {MQTT_TOPIC}")
    client.subscribe(MQTT_TOPIC)

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
            avg_motion = round(statistics.mean(buffer_motion), 1)
            avg_hum = round(statistics.mean(buffer_hum), 1)
            avg_temp = round(statistics.mean(buffer_temp), 1)
            avg_lux = int(statistics.mean(buffer_lux) / 4)

            p = Point(INFLUX_MEASUREMENT) \
                .tag("user", "leechunsik") \
                .field("avg_temperature", avg_temp) \
                .field("avg_humidity", avg_hum) \
                .field("avg_movement", avg_motion) \
                .field("avg_illuminance", avg_lux)
            
            #DB에 작성(저장)    ,record=p > p를 전송
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)

            buffer_motion.clear()
            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()

    except json.JSONDecodeError:
        print(f"에러: 들어온 데이터가 JSON이 아닙니다 -> {payload}")
    except Exception as e:
        print(f"에러 발생: {e}")


try:
    # Paho MQTT v2.x 대응
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
except AttributeError:
    # Paho MQTT v1.x 대응
    client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"브로커({MQTT_BROKER}) 연결 시도 중...")
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n프로그램 종료")
