import json
from datetime import datetime
import statistics
import sqlite3
import paho.mqtt.client as mqtt
import certifi
import streamingVision
import threading
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

MQTT_BROKER = "broker.emqx.io"
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

# [중요] 영상 처리를 백그라운드에서 실행할 함수
def start_vision_thread():
    try:
        # streamingVision.py 안에 있는 실행 로직을 호출합니다.
        # 만약 streamingVision.py 파일이 실행 코드를 함수 안에 넣지 않았다면 
        # 그 파일의 루프가 여기서 돌아가게 됩니다.
        streamingVision.run_vision() # 추천: streamingVision 내부 루프를 함수화하세요.
    except Exception as e:
        print(f"Vision Thread Error: {e}")

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
            
            m = int(streamingVision.MotionSumFor10sec)
            streamingVision.MotionSumFor10sec = 0
            h = float(data.get("humidity", 0))
            t = float(data.get("temperature", 0))
            l = int(data.get("illuminance", 0))

            buffer_hum.append(h)
            buffer_temp.append(t)
            buffer_lux.append(l)

            #현재 버퍼 상태 출력
            print(f"   데이터 수집 중 ({len(buffer_hum)}/30) - {current_active_user}")


            if len(buffer_hum) >= 30:
                buffer_motion.append(m)
                
                try:
                    if buffer_motion >= 100000:
                        final_motion = 4
                    elif 100000 > buffer_motion >= 75000:
                        final_motion = 3
                    elif 75000 > buffer_motion >= 50000:
                        final_motion = 2
                    elif 50000 > buffer_motion >= 25000:
                        final_motion = 1
                    else:
                        final_motion = 0
                except ValueError:
                    # 혹시라도 리스트가 비어있을 경우 에러 방지
                    final_motion = 0

                avg_hum = round(statistics.mean(buffer_hum), 1)
                avg_temp = round(statistics.mean(buffer_temp), 1)
                avg_lux = int(statistics.mean(buffer_lux) / 4)

                # 데이터 포인트 생성
                p = Point("sleep_sensor_data") \
                    .tag("user", current_active_user) \
                    .field("avg_temperature", avg_temp) \
                    .field("avg_humidity", avg_hum) \
                    .field("avg_movement", final_motion) \
                    .field("avg_illuminance", avg_lux)
                
                # DB 저장
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=p)
                print("데이터 저장 완료 (InfluxDB)")
                
                # 버퍼 비우기
                buffer_motion.clear()
                buffer_hum.clear()
                buffer_temp.clear()
                buffer_lux.clear()

        except json.JSONDecodeError:
            print(f"에러: 들어온 데이터가 JSON이 아닙니다 -> {payload}")
        except Exception as e:
            print(f"에러 발생: {e}")

# 메인 실행부
if __name__ == "__main__":
    # 2. 영상 처리 쓰레드 시작
    # daemon=True는 메인 프로그램 종료 시 같이 종료되게 합니다.
    vision_thread = threading.Thread(target=start_vision_thread, daemon=True)
    vision_thread.start()
    print("🚀 영상 처리 쓰레드가 시작되었습니다.")

    # 3. MQTT 클라이언트 설정 및 연결
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print(f"브로커({MQTT_BROKER}) 연결 시도 중...")
        client.connect(MQTT_BROKER, 1883, 60)
        
        # InfluxDB와 MQTT 루프 시작
        print("📥 데이터 수집 대기 중... (웹에서 시작 버튼을 누르세요)")
        client.loop_forever() 
    except KeyboardInterrupt:
        print("\n프로그램 종료")