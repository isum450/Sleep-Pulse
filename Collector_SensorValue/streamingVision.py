import cv2
import requests
import numpy as np
from datetime import datetime

# 1. 전역 변수 설정 (DataToDataBase.py에서 접근 가능)
MotionSumFor10sec = 0 
now = datetime.now()

def get_motion_count():
    """현재까지 누적된 움직임 값을 반환"""
    global MotionSumFor10sec
    return MotionSumFor10sec

def reset_motion_count():
    """DB 전송 후 값을 0으로 리셋"""
    global MotionSumFor10sec, now
    MotionSumFor10sec = 0
    now = datetime.now()

def run_vision():
    """실제 카메라 스트리밍 및 움직임 감지 루프"""
    global MotionSumFor10sec, now
    
    IP_ADDRESS = "192.168.0.36"
    URL = f"http://{IP_ADDRESS}:81/stream"
    
    thresh = 25 
    max_diff = 5 
    a, b = None, None

    print(f"[{datetime.now().strftime('%H:%M:%S')}] ESP32-CAM 연결 시도 중...")

    try:
        # 스트리밍 연결 (timeout을 줘서 무한 대기 방지)
        res = requests.get(URL, stream=True, timeout=15)
        bytes_data = b''

        print("✅ 영상 처리 루프 진입: 움직임 감지 시작")

        for chunk in res.iter_content(chunk_size=1024):
            bytes_data += chunk
            a_idx = bytes_data.find(b'\xff\xd8') # JPEG 시작
            b_idx = bytes_data.find(b'\xff\xd9') # JPEG 끝

            if a_idx != -1 and b_idx != -1:
                jpg = bytes_data[a_idx:b_idx+2]
                bytes_data = bytes_data[b_idx+2:]

                # 바이트 데이터를 이미지로 변환
                c = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if c is None: continue

                c = cv2.resize(c, (480, 320))
                draw = c.copy()

                if a is None:
                    a = c.copy()
                    continue
                if b is None:
                    b = c.copy()
                    continue

                # --- 영상 처리 로직 (Frame Differencing) ---
                a_gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY)
                b_gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY)
                c_gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)

                diff1 = cv2.absdiff(a_gray, b_gray)
                diff2 = cv2.absdiff(b_gray, c_gray)
                _, diff1_t = cv2.threshold(diff1, thresh, 255, cv2.THRESH_BINARY)
                _, diff2_t = cv2.threshold(diff2, thresh, 255, cv2.THRESH_BINARY)
                diff = cv2.bitwise_and(diff1_t, diff2_t)
                
                k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
                diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, k)

                diff_cnt = cv2.countNonZero(diff)

                # 움직임이 감지되면 전역 변수에 누적
                if diff_cnt > max_diff:
                    MotionSumFor10sec += diff_cnt
                    
                    # 화면에 사각형 표시
                    nzero = np.nonzero(diff)
                    cv2.rectangle(draw, (min(nzero[1]), min(nzero[0])), \
                                        (max(nzero[1]), max(nzero[0])), (0, 255, 0), 2)

                # 모니터링용 창 띄우기
                cv2.imshow('Sleep Motion Monitor', draw)

                # 프레임 교체
                a = b
                b = c

                # ESC 키 누르면 루프 탈출
                if cv2.waitKey(1) & 0xFF == 27:
                    break

    except Exception as e:
        print(f"❌ 시각 지능 에러: {e}")
    finally:
        cv2.destroyAllWindows()
        print("카메라 연결 종료")

# 단독 실행 테스트용
if __name__ == "__main__":
    run_vision()