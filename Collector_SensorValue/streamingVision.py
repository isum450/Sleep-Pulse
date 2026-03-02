import cv2
import requests
import numpy as np
from datetime import datetime

# 1. 설정 및 초기화
IP_ADDRESS = "192.168.0.36"
URL = f"http://{IP_ADDRESS}:81/stream"

thresh = 25 
max_diff = 5 

# 외부 프로그램(DataToDataBase.py)에서 참조하거나 초기화할 변수
# 누적된 움직임 값입니다.
MotionSum = 0 

a, b = None, None

def get_motion_count():
    """외부에서 현재까지 누적된 MotionSum을 가져가기 위한 함수"""
    global MotionSum
    return MotionSum

def reset_motion_count():
    """DB 전송 완료 후 외부에서 이 값을 0으로 리셋하기 위한 함수"""
    global MotionSum
    MotionSum = 0

try:
    # 스트리밍 연결
    res = requests.get(URL, stream=True, timeout=10)
    bytes_data = b''

    print("움직임 감지 시작... (데이터 수집 대기 중)")

    for chunk in res.iter_content(chunk_size=1024):
        bytes_data += chunk
        a_idx = bytes_data.find(b'\xff\xd8')
        b_idx = bytes_data.find(b'\xff\xd9')

        if a_idx != -1 and b_idx != -1:
            jpg = bytes_data[a_idx:b_idx+2]
            bytes_data = bytes_data[b_idx+2:]

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

            # --- 움직임 감지 로직 ---
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

            # 움직임이 기준치 이상일 때만 누적
            if diff_cnt > max_diff:
                MotionSum += diff_cnt  # 무한 누적 (외부에서 리셋할 때까지)
                
                # 시각화 (선택 사항)
                nzero = np.nonzero(diff)
                cv2.rectangle(draw, (min(nzero[1]), min(nzero[0])), \
                                    (max(nzero[1]), max(nzero[0])), (0, 255, 0), 2)

            # 결과 화면 출력
            cv2.imshow('Motion Capture System', draw)

            # 프레임 교체
            a = b
            b = c

            if cv2.waitKey(1) & 0xFF == 27:
                break

except Exception as e:
    print(f"에러 발생: {e}")
finally:
    cv2.destroyAllWindows()