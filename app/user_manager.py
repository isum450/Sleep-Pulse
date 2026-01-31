import sqlite3
import hashlib

# DB 파일 이름 설정
DB_FILENAME = r'C:/Users/leeso/source/repos/Sleep-Pulse/app/users.db'

# 데이터베이스 초기화 (테이블 생성)
def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    # DB파일 연결 없으면 새로 만들기(연결객체)

    cursor = conn.cursor()
    # 데이터 베이스 소통 명령어(소통객체)

    # 1. users 테이블 생성 (id, username, password, email)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT
        )
    ''')#유저네임에 unique (중복처리에 필요함)
    
    # 2. 유저 별 상태를 저장할 테이블 새로 생성!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recording_status (
            id INTEGER PRIMARY KEY,
            active_user TEXT,
            is_recording INTEGER DEFAULT 0
        )
    ''')

    # 3. 초기 상태값 삽입 (한 번만 실행됨)
    cursor.execute("INSERT OR IGNORE INTO recording_status (id, active_user, is_recording) VALUES (1, NULL, 0)")
    conn.commit()
    # 작업 확정

    conn.close()
    # 연결끊고 파일 닫기 열었으면 무조건 닫아야함

# 비밀번호 암호화 (SHA-256 알고리즘)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 회원가입 함수
def signup(username, password, email):
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        
        # 비밀번호 암호화 후 저장
        hashed_pw = hash_password(password)
        
        cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                       (username, hashed_pw, email))
        # 정보비교 

        conn.commit()
        print(f"회원가입 완료: {username}")
        return True
        
    except sqlite3.IntegrityError:
        print(f"이미 존재하는 아이디입니다: {username}")
        return False
    except Exception as e:
        print(f"[에러] {e}")
        return False
    finally:
        conn.close()

# 로그인 함수
def login(username, password):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # 입력 비밀번호 암호화하여 DB와 비교
    hashed_pw = hash_password(password)
    
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        print(f"로그인 되었습니다: {username}")
        return True
    else:
        print("아이디 또는 비밀번호가 일치하지 않습니다.")
        return False

def update_recording_status(username, status):
    """
    유저의 녹화 상태를 DB에 업데이트하는 함수
    status: True(시작) / False(중지)
    """
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        
        # True면 1, False면 0
        is_rec = 1 if status else 0
        
        # 녹화 중지일 때는 active_user를 NULL로 변경
        user_to_save = username if status else None

        cursor.execute("UPDATE recording_status SET active_user = ?, is_recording = ? WHERE id = 1", 
                       (user_to_save, is_rec))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"상태 업데이트 에러: {e}")
        return False
"""테스트 코드
if __name__ == "__main__":
    # DB 초기화 실행
    init_db()

    print("\n--- 회원가입 테스트 ---")
    signup("admin", "1234", "admin@sleep.com")
    signup("admin", "1234", "admin@sleep.com") # 중복 시도

    print("\n--- 로그인 테스트 ---")
    login("admin", "1234")      # 성공 케이스
    login("admin", "0000")      # 실패 케이스
"""