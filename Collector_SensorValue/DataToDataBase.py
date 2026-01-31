import json
import time #사용안해도댐 influx db 에서 시간 저장해주니까
import statistics
import sqlite3
import paho.mqtt.client as mqtt
import certifi
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = "test.mosquitto.org"
MQTT_SENSOR_TOPIC = "leesu/sensor/data"   # 센서 데이터 오는 곳
MQTT_CONTROL_TOPIC = "sleep_pulse/control" # 시작/중지 명령 오는 곳

#db 주소, 키비번, 이름 등등
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/"
INFLUX_TOKEN = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="
INFLUX_ORG = "f721a092afbb84b0"
INFLUX_BUCKET = "sleep_pulse"
INFLUX_MEASUREMENT = "sleep_sensor_data"#measurement를 유저마다 생성하는 건 비효율적이라서 하나의 measuerement에 관리하는 것이 좋다고 함.
                    #측정 이름 여기서 바꿀수 있도록

DB_PATH = 'https://wmytbsxolrrjkfneunvkp9.streamlit.app/'

#버퍼
buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_motion = []

current_active_user = None # 처음엔 아무도 없음
is_recording = False

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
    print("Connected with result code "+str(rc))
    # 센서 데이터 채널 구독
    client.subscribe(MQTT_SENSOR_TOPIC)   # 센서 데이터 구독
    client.subscribe(MQTT_CONTROL_TOPIC)  # 제어 명령 구독

def on_message(client, userdata, msg):
    global current_active_user, is_recording
    
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # [Case A] 웹에서 명령이 왔을 때
    if topic == MQTT_CONTROL_TOPIC:
        if payload.startswith("START"):
            # "START:leeso" 에서 이름만 잘라내기
            user_name = payload.split(":")[1]
            current_active_user = user_name
            is_recording = True
            # 버퍼 초기화 (새로운 녹화 시작이니까 비워줌)
            buffer_motion.clear()
            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()
            print(f"🔔 명령 수신: {user_name}님 녹화 시작!")
            
        elif payload == "STOP":
            current_active_user = None
            is_recording = False
            # 남은 데이터 버퍼도 비워줌
            buffer_motion.clear()
            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()

            print("🔕 명령 수신: 녹화 중지.")

    # [Case B] 센서 데이터가 왔을 때 (원래 로직)
    elif topic == MQTT_SENSOR_TOPIC: # 본인 센서 토픽
        if not is_recording:
            # print("대기 중... (데이터 수신됨)") # 너무 시끄러우면 주석 처리
            return

        try:
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
            print(f"   데이터 수집 중 ({len(buffer_hum)}/30) - {current_active_user}")


            if len(buffer_hum) >= 30:
                #30개가 모였을 때 저장
                if len(buffer_hum) >= 30:
                    avg_motion = round(statistics.mean(buffer_motion), 1)
                    avg_hum = round(statistics.mean(buffer_hum), 1)
                    avg_temp = round(statistics.mean(buffer_temp), 1)
                    avg_lux = int(statistics.mean(buffer_lux) / 4)

                    p = Point("sleep_sensor_data") \
                        .tag("user", current_active_user) \
                        .field("avg_temperature", avg_temp) \
                        .field("avg_humidity", avg_hum) \
                        .field("avg_movement", avg_motion) \
                        .field("avg_illuminance", avg_lux)
                    
                    #DB에 작성(저장)    ,record=p > p를 전송
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                    
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
