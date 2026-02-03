import sqlite3
import hashlib

# DB 파일 이름 설정
DB_FILENAME = 'users.db'

# 데이터베이스 초기화 (테이블 생성)
def init_db():
    conn = sqlite3.connect(DB_FILENAME)
    # DB파일 연결 없으면 새로 만들기(연결객체)

    cursor = conn.cursor()
    # 데이터 베이스 소통 명령어(소통객체)

    # 1. users 테이블 생성 (user_id, username, password, email)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            idx INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL, 
            password TEXT NOT NULL,
            email TEXT,
            username TEXT NOT NULL 
        )
    ''')#유저네임에 unique (중복처리에 필요함)
    
    # 2. 유저 별 상태를 저장할 테이블 새로 생성!
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recording_status (
            idx INTEGER PRIMARY KEY,
            active_username TEXT,
            is_recording INTEGER DEFAULT 0
        )
    ''')

    # 3. 초기 상태값 삽입 (한 번만 실행됨)
    cursor.execute("INSERT OR IGNORE INTO recording_status (idx, active_username, is_recording) VALUES (1, NULL, 0)")
    conn.commit()
    # 작업 확정

    conn.close()
    # 연결끊고 파일 닫기 열었으면 무조건 닫아야함

# 비밀번호 암호화 (SHA-256 알고리즘)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 회원가입 함수
def signup(user_id, password, email, username):
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        
        # 비밀번호 암호화 후 저장
        hashed_pw = hash_password(password)
        
        cursor.execute("INSERT INTO users (user_id, password, email, username) VALUES (?, ?, ?, ?)", 
                       (user_id, hashed_pw, email, username))
        # 정보비교 

        conn.commit()
        print(f"회원가입 완료: ID={user_id}, Name={username}")
        return True
        
    except sqlite3.IntegrityError:
        print(f"이미 존재하는 아이디입니다: {user_id}")
        return False
    except Exception as e:
        print(f"[에러] {e}")
        return False
    finally:
        conn.close()

# 로그인 함수
def login(user_id, password):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    
    # 입력 비밀번호 암호화하여 DB와 비교
    hashed_pw = hash_password(password)
    
    cursor.execute("SELECT * FROM users WHERE user_id = ? AND password = ?", (user_id, hashed_pw))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        print(f"로그인 되었습니다.")
        return True
    else:
        print("아이디 또는 비밀번호가 일치하지 않습니다.")
        return False

def get_username(user_id):
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0] # 이름 반환
        return None
    except:
        return None

def update_recording_status(target_username, status):
    try:
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        
        is_rec = 1 if status else 0
        name_to_save = target_username if status else None

        cursor.execute("UPDATE recording_status SET active_username = ?, is_recording = ? WHERE idx = 1", 
                       (name_to_save, is_rec))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"상태 업데이트 에러: {e}")
        return False

if __name__ == "__main__":
    init_db()