import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import user_manager as db
import pandas as pd
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt
import time
from datetime import datetime, timedelta
import Analysis_LLM.sleep_advisor as advisor

# 페이지 설정 (브라우저 탭 이름 등)
st.set_page_config(page_title="SLEEP PULSE", layout="wide") 

# influx DB 설정
INFLUX_URL = "https://us-east-1-1.aws.cloud2.influxdata.com/"
INFLUX_TOKEN = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="
INFLUX_ORG = "personal project"
INFLUX_BUCKET = "sleep_pulse"
INFLUX_MEASUREMENT = "sleep_sensor_data"

MQTT_BROKER = "broker.emqx.io"
MQTT_CONTROL_TOPIC = "sleep_pulse/control"

# 세션 상태 초기화
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
    st.session_state['user_id'] = None   # 로그인용 아이디
    st.session_state['username'] = None  # 태그/표시용 이름
#로그인한 후 화면을 새로고침했을떄 로그인이 풀리는걸 방지하기 위한 로그인 여부 저장장치 
#웹사이트를 처음들어왔을때 실행되고 이제 로그인하면 TURE로 바꾸는 형식
#username은 고유 사용자 특정을 위함

# 현재 보고 있는 화면을 기억하는 변수 ('menu', 'score', 'graph', 'chat', 'my_info', 'history')
if 'current_view' not in st.session_state:
    st.session_state['current_view'] = 'menu'

# 채팅 기록 초기화 (AI 상담용)
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 수면 데이터 분석 AI입니다. 무엇을 도와드릴까요?"}
]

#시간 저장용 변수
if 'recording_start_dt' not in st.session_state:
    st.session_state['recording_start_dt'] = None

def send_mqtt_command(command):
    try:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            client = mqtt.Client()
        client.connect(MQTT_BROKER, 1883, 60)
        client.publish(MQTT_CONTROL_TOPIC, command)
        client.disconnect()
    except Exception as e:
        st.error(f"명령 전송 실패: {e}")

# 로그아웃 함수 (리셋)
def logout():
    st.session_state['is_logged_in'] = False
    st.session_state['user_id'] = None
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

        target_name = st.session_state['username']

        # Flux 쿼리: 최근 8시간 데이터 조회
        # person1 데이터 중 avg_... 로 시작하는 필드값들을 가져옵니다.
        query = f"""
        from(bucket: "{INFLUX_BUCKET}")
          |> range(start: -7d)
          |> filter(fn: (r) => r["_measurement"] == "{INFLUX_MEASUREMENT}")
          |> filter(fn: (r) => r["user"] == "{target_name}") 
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

        # 시간 차이 계산
        time_diff = df.index.to_series().diff()

        #데이터가 10분이상 끊겼다면 저장
        GAP_THRESHOLD = pd.Timedelta(minutes=10)

        new_session_starts = time_diff[time_diff > GAP_THRESHOLD].index
        
        if not new_session_starts.empty:
            # 가장 마지막 시간 찾기
            last_start_time = new_session_starts[-1]
            
            # 그 시간이후의 데이터만 남기기
            df = df[df.index >= last_start_time]
                        
        else:
            # 끊긴 적이 없다면 (데이터가 1개뿐이거나 아주 짧은 경우) 그대로 씁니다.
            pass


        # 그래프에 필요한 컬럼만 남기기 (태그 정보 등 제외)
        cols_to_keep = [c for c in df.columns if c in ['avg_movement', 'avg_temperature', 'avg_humidity', 'avg_illuminance']]
        return df[cols_to_keep]

    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return None

def save_sleep_session(duration_str, start_dt, end_dt):
    # 1. 일단 넉넉하게 최근 데이터를 가져옵니다.
    df = load_data() 
    
    if df is not None and not df.empty:
        # [핵심 수정] 가져온 데이터 중에서 '녹화 시작 시간(start_dt)' 이후의 데이터만 남깁니다.
        # (이전 8시간 데이터가 섞이는 것을 방지)
        
        # start_dt가 타임존 정보가 없을 수 있어 맞춰주는 작업 (에러 방지용)
        try:
            # df 인덱스가 UTC일 수 있으므로 비교를 위해 시간대 제거 혹은 맞춤
            # 가장 단순한 방법: 문자열로 변환해서 비교하거나, 그냥 필터링
            df = df[df.index >= pd.to_datetime(start_dt).tz_localize(None).tz_localize('UTC')]
        except:
            # 타임존 처리가 복잡하면, 그냥 개수로 대략 자르거나 전체 사용
            pass

        # 데이터가 필터링 후에도 남아있는지 확인
        if df.empty:
             st.warning("수집된 데이터가 너무 적어 분석할 수 없습니다.")
             return

        # 평균값 계산 (이제 녹화된 구간만의 평균입니다!)
        summary = {
            "avg_movement": float(df['avg_movement'].mean()),
            "avg_temperature": float(df['avg_temperature'].mean()),
            "avg_humidity": float(df['avg_humidity'].mean()),
            "avg_illuminance": float(df['avg_illuminance'].mean()),
            "duration": duration_str # "01:30:00" 같은 문자열
        }
    else:
        st.warning("저장된 데이터가 없습니다.")
        return

    # 2. LLM에게 분석 요청
    with st.spinner("AI가 수면 데이터를 분석 중입니다..."):
        score, feedback = advisor.analyze_sleep_data(summary)

    # 3. 결과 저장
    summary_str = str(summary)
    db.save_sleep_result(st.session_state['user_id'], score, feedback, summary_str)
    
    st.toast(f"분석 완료! 점수: {score}점", icon="🎉")

# 메인 함수
def main():
    if st.session_state['is_logged_in']:
        if st.session_state['username'] == 'admin':
            st.divider() # 구분선
            st.subheader("관리자 메뉴 (유저 목록)")
            
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
            st.divider()

        # 사이드바(메뉴)
        with st.sidebar:
            st.title(f"{st.session_state['username']}님") # 이름 표시
            st.caption(f"ID: {st.session_state['user_id']}") # 아이디 작게 표시
            st.write("반갑습니다!")
            st.divider()
            if st.button("홈", use_container_width=True):
                go_to_main()

            if st.button("내 정보", use_container_width=True):
                st.session_state['current_view'] = 'my_info'
                st.rerun()
                
            if st.button("이전 데이터 보기", use_container_width=True):
                st.session_state['current_view'] = 'history'
                st.rerun()
                
            st.divider()
            if st.button("로그아웃", type="primary"):
                logout()
       
        
        st.subheader("데이터 수집 제어")

        if 'is_recording' not in st.session_state:
            st.session_state['is_recording'] = False

        
        # 녹화 중인지 아닌지에 따라 UI 다르게 보여주기
        if st.session_state['is_recording']:
            # 경과 시간 계산 및 표시
            if st.session_state['recording_start_dt']:
                elapsed = datetime.now() - st.session_state['recording_start_dt']
                elapsed_str = str(elapsed).split('.')[0] 
                st.success(f"현재 '{st.session_state['username']}'님의 데이터를 수집 중입니다... (경과 시간: {elapsed_str})")
            else:
                st.success(f"현재 '{st.session_state['username']}'님의 데이터를 수집 중입니다...")

            if st.button("⏹️ 수집 중지"):
                # 1. 종료 시간 및 기간 계산
                end_dt = datetime.now()
                start_dt = st.session_state['recording_start_dt']
                
                duration_str = "알 수 없음"
                if start_dt:
                    total_duration = end_dt - start_dt
                    duration_str = str(total_duration).split('.')[0]

                # 2. MQTT로 센서 끄기 명령 전송
                send_mqtt_command("STOP")
                
                # ---------------------------------------------------------
                # [핵심 추가] 여기서 데이터를 분석하고 저장해야 합니다!
                # ---------------------------------------------------------
                if start_dt:
                    save_sleep_session(duration_str, start_dt, end_dt)
                # ---------------------------------------------------------

                # 3. DB 상태 업데이트 (수집 종료 상태로)
                # (db.update_recording_status 함수가 user_manager.py에 정의되어 있어야 에러 안 남)
                # 만약 정의 안 했다면 이 줄은 지우거나 pass 처리
                try:
                    db.update_recording_status(st.session_state['username'], False)
                except:
                    pass

                # 4. 화면 상태 초기화 (순서 중요: 저장 다 끝난 뒤에 초기화)
                st.session_state['is_recording'] = False
                st.session_state['recording_start_dt'] = None
                
                # 5. 결과 확인할 시간(2초) 주고 새로고침
                time.sleep(2) 
                st.rerun()
        else:
            st.info("데이터 수집을 시작하려면 버튼을 누르세요.")
            
            if st.button("▶️ 수집 시작"):
                # 1. 시작 시간 기록 (datetime 객체 사용)
                now = datetime.now()
                st.session_state['recording_start_dt'] = now
                
                my_name = st.session_state['username']
                send_mqtt_command(f"START:{my_name}")
                
                db.update_recording_status(my_name, True)
                st.session_state['is_recording'] = True
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
                    if st.button("2. 시간별 그래프 (최근 8시간)", use_container_width=True):
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
            
            st.subheader("지난 수면 분석 결과")
            
            # DB에서 가장 최근 기록 가져오기
            last_result = db.get_last_sleep_result(st.session_state['user_id'])

            if last_result:
                #가장 최근에 저장된 점수를 불러와야 함.

                db_score = last_result[0]
                db_feedback = last_result[1]
                db_time = last_result[2]

                col1, col2 = st.columns([2, 1])
                with col1:
                    with st.container(border=True):
                        st.markdown(f"### 💡 AI 분석 리포트 ({db_time} 기준)")
                        st.info(db_feedback) # LLM이 해준 조언 출력
                        
                with col2:
                    with st.container(border=True):
                        st.markdown("### 종합 점수")
                        
                        # 점수에 따라 색상 변경
                        color = "#4CAF50" # 초록(좋음)
                        if db_score < 70: color = "#FFA500" # 주황(보통)
                        if db_score < 50: color = "#FF4B4B" # 빨강(나쁨)
                            
                        st.markdown(f"<h1 style='text-align: center; color: {color}; font-size: 70px;'>{db_score}점</h1>", unsafe_allow_html=True)
            else:
                st.warning("아직 저장된 수면 데이터가 없습니다. 먼저 데이터 수집을 진행해주세요!")
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
            st.caption("궁금한 점을 물어보세요! (예: 오늘 내 수면 점수가 왜 낮아? / 잠 잘 오는 법 알려줘)")

            # 대화 기록 표시
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

            # 입력창
            if prompt := st.chat_input("질문을 입력하세요..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)
                
                # 3. 답변 생성 (DB에서 최근 데이터 가져와서 같이 보내기)
                with st.chat_message("assistant"):
                    with st.spinner("AI가 수면 기록을 분석하고 생각 중입니다..."):
                        
                        # (1) 최근 수면 데이터 조회 (문맥 파악용)
                        last_sleep_info = db.get_last_sleep_result(st.session_state['user_id'])
                        context_str = None
                        
                        if last_sleep_info:
                            # DB에서 가져온 summary_data (문자열) 활용
                            # last_sleep_info 구조: (score, feedback, timestamp, summary_data)
                            context_str = f"최근 측정 일시: {last_sleep_info[2]}, 요약 데이터: {last_sleep_info[3]}"
                        
                        # (2) 질문 + 데이터 보내서 답변 받기
                        response_text = advisor.get_chat_response(prompt, context_data=context_str)
                        
                        # (3) 화면에 출력
                        st.write(response_text)
                
                # 4. 대화 기록에 저장
                st.session_state.messages.append({"role": "assistant", "content": response_text})

        elif st.session_state['current_view'] == 'my_info':
            if st.button("메인으로"):
                go_to_main()
            
            st.title("내 정보")
            
            # user_manager.py에서 추가한 get_user_info 사용
            user_info = db.get_user_info(st.session_state['user_id'])
            
            if user_info:
                with st.container(border=True):
                        st.text_input("아이디", value=user_info[0], disabled=True)
                        st.text_input("이름 (닉네임)", value=user_info[1], disabled=True)
                        email_val = user_info[2] if user_info[2] else "등록되지 않음"
                        st.text_input("이메일", value=email_val, disabled=True)
            else:
                    st.error("정보를 불러올 수 없습니다.")

        elif st.session_state['current_view'] == 'history':
            if st.button("메인으로"):
                go_to_main()

            st.title("지난 수면 기록")
            st.caption("지금까지 측정된 모든 수면 기록을 확인합니다.")

            # user_manager.py에서 추가한 get_all_sleep_records 사용
            records = db.get_all_sleep_records(st.session_state['user_id'])
            
            if records:
                df_history = pd.DataFrame(records, columns=['측정 시간', '수면 점수', 'AI 피드백'])
                
                st.dataframe(
                    df_history, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "측정 시간": st.column_config.TextColumn("측정 시간", width="medium"),
                        "수면 점수": st.column_config.NumberColumn("점수", format="%d점"),
                        "AI 피드백": st.column_config.TextColumn("피드백", width="large"),
                    }
                )
            else:
                st.info("아직 저장된 수면 기록이 없습니다.")
    
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
                    st.session_state['user_id'] = login_id
                    real_name = db.get_username(login_id)
                    st.session_state['username'] = real_name if real_name else login_id
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 일치하지 않습니다.")

        # 회원가입 탭
        with tab2:
            st.subheader("회원가입")
            new_id = st.text_input("새 아이디", key="new_id")
            new_username = st.text_input("사용할 이름/닉네임", key="new_username")
            new_pw = st.text_input("새 비밀번호", type="password", key="new_pw")
            new_pw_check = st.text_input("비밀번호 확인", type="password", key="new_pw_check")
            new_email = st.text_input("이메일", key="new_email")
            
            if st.button("가입하기"):
                # 1. 모든 칸이 채워져 있는지 확인
                if new_id and new_username and new_pw:
                    # 2. 비밀번호와 확인 비밀번호가 같은지 확인
                    if new_pw == new_pw_check:
                        if db.signup(new_id, new_pw, new_email, new_username):
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