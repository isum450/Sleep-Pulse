import json
import time #사용안해도댐 influx db 에서 시간 저장해주니까
import statistics
import sqlite3
import paho.mqtt.client as mqtt
import certifi
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "leesu/sensor/data"

#db 주소, 키비번, 이름 등등
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/"
INFLUX_TOKEN = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="
INFLUX_ORG = "f721a092afbb84b0"
INFLUX_BUCKET = "sleep_pulse"
INFLUX_MEASUREMENT = "sleep_sensor_data"#measurement를 유저마다 생성하는 건 비효율적이라서 하나의 measuerement에 관리하는 것이 좋다고 함.
                    #측정 이름 여기서 바꿀수 있도록

DB_PATH = r'C:/Users/leeso/source/repos/Sleep-Pulse/app/users.db'

#버퍼
buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_motion = []

def get_active_user():
    try:
        #users.db 파일 경로 확인하기
        #다른 파일이면 경로 수정 필요함
        conn = sqlite3.connect(DB_PATH)
        # 확인을 위해 로그 출력 (디버깅용)
        print(f"📂 DB 읽는 중: {DB_PATH}")
        c = conn.cursor()
        c.execute("SELECT active_user, is_recording FROM recording_status WHERE id = 1")
        row = c.fetchone()
        conn.close()

        # DB에 뭐라고 적혀있는지 확인해보세요!
        if row:
            print(f"👀 DB 상태 확인: 유저={row[0]}, 녹화중={row[1]}")
        else:
            print("👀 DB 상태 확인: 데이터 없음 (row가 None)")

        if row and row[1] == 1:
            return row[0]
        return None
    except Exception as e:
        print(f"Error accessing sqlite: {e}")
        return None
    
#influxDB 클라이언트 설정
try:
    db_client = InfluxDBClient(
        url = INFLUX_URL,
        token = INFLUX_TOKEN,
        org = INFLUX_ORG,
        ssl_ca_cert = certifi.where(),
        timeout=10000
    )
    write_api = db_client.write_api(write_options=SYNCHRONOUS)
    print("InfluxDB Client set finished")
except Exception as e:
    print("InfluxDB initialization failed")
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

        #현재 버퍼 상태 출력
        print(f"움직임{m}, 습도{h}%, 온도{t}, 조도{l}")


        if len(buffer_hum) >= 30:
            #30개가 모였을 때 유저가 누군지 확인한다.
            current_user = get_active_user()
            if current_user:
                print(f"현재 기록 중인 유저: {current_user}")
                avg_motion = round(statistics.mean(buffer_motion), 1)
                avg_hum = round(statistics.mean(buffer_hum), 1)
                avg_temp = round(statistics.mean(buffer_temp), 1)
                avg_lux = int(statistics.mean(buffer_lux) / 4)

                p = Point("sleep_sensor_data") \
                    .tag("user", current_user) \
                    .field("avg_temperature", avg_temp) \
                    .field("avg_humidity", avg_hum) \
                    .field("avg_movement", avg_motion) \
                    .field("avg_illuminance", avg_lux)
                
                #DB에 작성(저장)    ,record=p > p를 전송
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                print(f"InfluxDB에 기록됨 -> 사용자: {current_user}, 온도: {avg_temp}, 습도: {avg_hum}, 움직임: {avg_motion}, 조도: {avg_lux}")

            else:
                print("기록 중인 유저가 없습니다. 데이터가 저장되지 않았습니다.")
            
            #버퍼 비우기
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
