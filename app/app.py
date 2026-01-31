import streamlit as st
import user_manager as db
import pandas as pd
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt


# 페이지 설정 (브라우저 탭 이름 등)
st.set_page_config(page_title="SLEEP PULSE", layout="wide") 

# influx DB 설정
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/"
INFLUX_TOKEN = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="
INFLUX_ORG = "personal project"
INFLUX_BUCKET = "sleep_pulse"
INFLUX_MEASUREMENT = "sleep_sensor_data"

BROKER = "broker.hivemq.com" # 예시 (본인이 쓰는 브로커 주소)
PORT = 1883
TOPIC_CONTROL = "sleep_pulse/control" # 명령을 주고받을 전용 채널

# 세션 상태 초기화
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
    st.session_state['username'] = None
#로그인한 후 화면을 새로고침했을떄 로그인이 풀리는걸 방지하기 위한 로그인 여부 저장장치 
#웹사이트를 처음들어왔을때 실행되고 이제 로그인하면 TURE로 바꾸는 형식
#username은 고유 사용자 특정을 위함

# 현재 보고 있는 화면을 기억하는 변수 ('menu', 'score', 'graph', 'chat')
if 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'menu'

# 채팅 기록 초기화 (AI 상담용)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 수면 데이터 분석 AI입니다. 무엇을 도와드릴까요?"}
]

# 로그아웃 함수 (리셋)
def logout():
    st.session_state['is_logged_in'] = False
    st.session_state['username'] = None
    st.session_state.messages = [] # 로그아웃 시 채팅 기록 초기화
    st.rerun()  #새로고침

# 메뉴 함수
def go_to_main():
    st.session_state['current_view'] = 'menu'
    st.rerun()

# influx DB 데이터 가져오는 함수 (수정됨)
def load_data():
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        query_api = client.query_api()

        # Flux 쿼리: 최근 6시간 데이터 조회
        # person1 데이터 중 avg_... 로 시작하는 필드값들을 가져옵니다.
        query = f"""
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -7h)
          |> filter(fn: (r) => r["_measurement"] == "{INFLUX_MEASUREMENT}")
          |> filter(fn: (r) => r["_field"] == "avg_movement" or r["_field"] == "avg_temperature" or r["_field"] == "avg_humidity" or r["_field"] == "avg_illuminance")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: false)
        """
        #pivot(가로로 재정렬), sort(시간순 재정렬)

        df = query_api.query_data_frame(query)
        
        if df.empty:
            return None
            
        # '_time' 컬럼을 인덱스로 설정하고, 불필요한 컬럼 제거
        df = df.set_index("_time")
        # 그래프에 필요한 컬럼만 남기기 (태그 정보 등 제외)
        cols_to_keep = [c for c in df.columns if c in ['avg_movement', 'avg_temperature', 'avg_humidity', 'avg_illuminance']]
        return df[cols_to_keep]

    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return None
# MQTT로 명령 전송 함수
def send_command(user, status):
    try:
        # 1. 클라이언트 생성 (Paho v2 대응)
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()
            
        # 2. 브로커 연결 (DataToDataBase.py랑 똑같은 주소여야 함!)
        # "broker.hivemq.com" 인지 꼭 확인하세요.
        client.connect(BROKER, PORT)
        
        # 3. 메시지 만들기
        if status:
            msg = f"START:{user}"
        else:
            msg = "STOP"
            
        # 4. 전송 (Publish)
        info = client.publish(TOPIC_CONTROL, msg)
        
        # [중요] 메시지가 갈 때까지 잠깐 기다려줌 (안전장치)
        info.wait_for_publish() 
        
        client.disconnect()
        print(f"전송 성공: {msg}") # Streamlit 로그에 찍힘
        
    except Exception as e:
        print(f"MQTT 전송 에러: {e}")

# 메인 함수
def main():
    if st.session_state['is_logged_in']:
        if st.session_state['username'] == 'admin':
            st.divider() # 구분선
            st.subheader("👑 관리자 메뉴 (유저 목록)")
            
            # DB 내용을 가져와서 화면에 보여주기
            import sqlite3
            import pandas as pd
            
            # user_manager.py에 있는 경로가 아니라, 현재 실행 위치의 db를 읽어야 함
            # (주의: user_manager를 통해서 가져오는 게 제일 좋지만, 임시로 직접 읽음)
            try:
                # DB 연결 (경로는 상황에 맞게 수정 필요, 보통 같은 폴더면 그냥 파일명)
                con = sqlite3.connect('users.db') 
                df = pd.read_sql_query("SELECT * FROM users", con)
                st.dataframe(df) # 데이터프레임(표)으로 보여주기
                con.close()
            except Exception as e:
                st.error(f"DB 읽기 실패: {e}")
        # 사이드바(메뉴)
        with st.sidebar:
            st.title(f"{st.session_state['username']}님")
            st.write("반갑습니다!")
            st.divider()
            if st.button("홈", use_container_width=True):
                go_to_main()
            st.button("내 정보", use_container_width=True)
            st.button("데이터 보기", use_container_width=True)
            st.divider()
            if st.button("로그아웃", type="primary"):
                logout()
        if st.sidebar.button("로그아웃"):
            logout()
            
        st.title("수면 데이터 분석")

        # --- 수집 제어 버튼 ---
        st.subheader("📡 데이터 수집 제어")

        if 'is_recording' not in st.session_state:
            st.session_state['is_recording'] = False

        if st.button("▶️ 수집 시작"):
            # 1. 버튼 눌림 확인 (화면에 무조건 떠야 함)
            st.warning("⚠️ 버튼 눌림! 코드 실행 시작...")
            print("LOG: 버튼 클릭됨 - 로직 진입")

            try:
                # 2. MQTT 연결 및 전송 시도
                st.info("📡 MQTT 브로커 연결 시도 중...")
                
                # 브로커 정보 다시 확인
                BROKER_ADDRESS = "test.mosquitto.org" # 혹은 "broker.hivemq.com"
                PORT_NUMBER = 1883
                
                # 클라이언트 생성
                try:
                    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                except AttributeError:
                    client = mqtt.Client()
                    
                # 연결 (타임아웃 5초 설정 - 무한 대기 방지)
                client.connect(BROKER_ADDRESS, PORT_NUMBER, keepalive=60)
                
                # 메시지 전송
                msg = f"START:{st.session_state['username']}"
                client.publish(TOPIC_CONTROL, msg)
                client.disconnect()
                
                # 3. 성공 메시지
                st.success(f"✅ 전송 완료: {msg}")
                print(f"LOG: 전송 성공 - {msg}")
                
                # 상태 변경
                st.session_state['is_recording'] = True
                
            except Exception as e:
                # 에러가 나면 화면에 빨갛게 표시!
                st.error(f"❌ 에러 발생: {e}")
                print(f"LOG: 에러 발생 - {e}")

            # [중요] 디버깅을 위해 st.rerun()을 잠시 끕니다!
            # 메시지를 눈으로 확인해야 하니까요.
            # st.rerun()
        # 녹화 중인지 아닌지에 따라 UI 다르게 보여주기
        #if st.button("▶️ 수집 시작"):
            # 1. 화면 상태 변경
            #st.session_state['is_recording'] = True
            # 2. [변경] MQTT로 "시작해!" 명령 보내기
            #send_command(st.session_state['username'], True)
            #st.rerun()

        if st.button("⏹️ 수집 중지"):
            st.session_state['is_recording'] = False
            # [변경] MQTT로 "멈춰!" 명령 보내기
            send_command(None, False)
            st.rerun()


       # 화면 1: 메인 옵션 메뉴 (로그인 직후 화면)
        if st.session_state['current_view'] == 'menu':
            st.title("SLEEP PULSE")
            for _ in range(5):
                st.write("")

            # 화면 중앙 정렬을 위해 컬럼 사용 (좌우 여백 둠)
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col2: # 가운데 컬럼에 버튼 배치
                with st.container(border=True):
                    st.markdown("<div style='text-align: center; font-size: 26px; font-weight: bold;'>MENU</div>", unsafe_allow_html=True)
                    st.write("") # 여백
                    
                    # 1. 수면 점수 버튼
                    if st.button("1. 수면 점수 확인", use_container_width=True):
                        st.session_state['current_view'] = 'score'
                        st.rerun()
                    
                    st.write("") # 버튼 사이 간격
                    
                    # 2. 시간별 그래프 버튼
                    if st.button("2. 시간별 그래프", use_container_width=True):
                        st.session_state['current_view'] = 'graph'
                        st.rerun()
                        
                    st.write("") # 버튼 사이 간격

                    # 3. AI 상담 버튼
                    if st.button("3. 실시간 AI 상담", use_container_width=True):
                        st.session_state['current_view'] = 'chat'
                        st.rerun()

        # 화면 2: 수면 점수
        elif st.session_state['current_view'] == 'score':
            if st.button("메인으로"):
                go_to_main()
            
            st.subheader("오늘의 수면 분석")
            col1, col2 = st.columns([2, 1])
            with col1:
                with st.container(border=True):
                    st.markdown(" AI 분석 리포트")
                    st.info("전날 대비 깊은 수면이 **30분 증가**했습니다! 아주 좋은 신호입니다.")
                    st.write("- **수면 효율:** 92% (매우 좋음)")
                    st.write("- **뒤척임 횟수:** 12회 (정상)")
            with col2:
                with st.container(border=True):
                    st.markdown("종합 점수")
                    st.markdown("<h1 style='text-align: center; color: #4CAF50; font-size: 60px;'>88점</h1>", unsafe_allow_html=True)

        # 화면 3: 시간별 그래프 
        elif st.session_state['current_view'] == 'graph':
            if st.button("메인으로"):
                go_to_main()

            with st.spinner('클라우드 서버에서 데이터를 가져오는 중...'):
                df = load_data()

            if df is not None and not df.empty:
                tab1, tab2, tab3, tab4 = st.tabs(["움직임", "온도", "습도", "조도"])
                
                # 움직임 탭
                with tab1:
                    st.markdown("움직임 수치 (Movement)")
                    if 'avg_movement' in df.columns:
                        st.line_chart(df['avg_movement'], use_container_width=True, color="#FF4B4B") # 빨간색
                    else:
                        st.warning("움직임 데이터가 없습니다.")

                # 온도 탭
                with tab2:
                    st.markdown("실내 온도 (Temperature)")
                    if 'avg_temperature' in df.columns:
                        st.line_chart(df['avg_temperature'], use_container_width=True, color="#FFA500") # 주황색
                    else:
                        st.warning("온도 데이터가 없습니다.")

                # 습도 탭
                with tab3:
                    st.markdown("실내 습도 (Humidity)")
                    if 'avg_humidity' in df.columns:
                        st.line_chart(df['avg_humidity'], use_container_width=True, color="#00BFFF") # 파란색
                    else:
                        st.warning("습도 데이터가 없습니다.")
                        
                # 조도 탭
                with tab4:
                    st.markdown("빛 밝기 (Illuminance)")
                    if 'avg_illuminance' in df.columns:
                        st.line_chart(df['avg_illuminance'], use_container_width=True, color="#FFD700") # 노란색
                    else:
                        st.warning("조도 데이터가 없습니다.")
            else:
                with st.container(border=True):
                    st.warning("⚠️ 저장된 데이터가 없습니다.")
                    st.write("1. ESP32 보드가 켜져 있는지 확인해주세요.")
                    st.write("2. 'sensor.py' 코드가 실행 중인지 확인해주세요.")
                    st.write(f"3. InfluxDB Bucket 이름이 '{INFLUX_BUCKET}'인지 확인해주세요.")

        # 화면 4: AI 상담 
        elif st.session_state['current_view'] == 'chat':
            if st.button("메인으로"):
                go_to_main()

            st.subheader("AI 수면 코치")
            
            # 대화 기록 표시
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            # 입력창
            if prompt := st.chat_input("질문을 입력하세요..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                response = f"'{prompt}'에 대한 답변 준비 중..."
                st.session_state.messages.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.write(response)

    # 비로그인 상태일 때 화면
    else:
        st.title("SLEEP PULSE")
        
        tab1, tab2 = st.tabs(["로그인", "회원가입"])

        # 로그인 탭
        with tab1:
            st.subheader("로그인")
            login_id = st.text_input("아이디", key="login_id")
            login_pw = st.text_input("비밀번호", type="password", key="login_pw")
            #type을 통해 패스워드 치는거 가리기
            if st.button("로그인"):
                if db.login(login_id, login_pw):
                    st.session_state['is_logged_in'] = True
                    st.session_state['username'] = login_id
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

        # 회원가입 탭
        with tab2:
            st.subheader("회원가입")
            new_id = st.text_input("새 아이디", key="new_id")
            new_pw = st.text_input("새 비밀번호", type="password", key="new_pw")
            new_pw_check = st.text_input("비밀번호 확인", type="password", key="new_pw_check")
            new_email = st.text_input("이메일", key="new_email")
            
            if st.button("가입하기"):
                # 1. 모든 칸이 채워져 있는지 확인
                if new_id and new_pw and new_pw_check:
                    # 2. 비밀번호와 확인 비밀번호가 같은지 확인
                    if new_pw == new_pw_check:
                        if db.signup(new_id, new_pw, new_email):
                            st.success("회원가입 성공. 로그인 탭에서 로그인해주세요.")
                        else:
                            st.error("이미 존재하는 아이디입니다.")
                    else:
                        st.error("비밀번호가 서로 일치하지 않습니다.") # 다르면 에러
                else:
                    st.warning("모든 정보를 입력해주세요.")



if __name__ == "__main__":
    db.init_db()
    #db실행함수
    main()

    #python -m streamlit run app.py