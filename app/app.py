import streamlit as st
import user_manager as db

# 세션 상태 초기화
if 'is_logged_in' not in st.session_state:
    st.session_state['is_logged_in'] = False
    st.session_state['username'] = None
#로그인한 후 화면을 새로고침했을떄 로그인이 풀리는걸 방지하기 위한 로그인 여부 저장장치 
#웹사이트를 처음들어왔을때 실행되고 이제 로그인하면 TURE로 바꾸는 형식
#username은 고유 사용자 특정을 위함

# 로그아웃 함수 (리셋)
def logout():
    st.session_state['is_logged_in'] = False
    st.session_state['username'] = None
    st.rerun()  #새로고침

# 메인 함수
def main():
    st.set_page_config(page_title="SLEEP PULSE")

    # 1. 로그인 상태일 때 화면
    if st.session_state['is_logged_in']:
        st.sidebar.write(f"{st.session_state['username']}님 환영합니다.")
        
        if st.sidebar.button("로그아웃"):
            logout()
            
        st.title("수면 데이터 분석")
        st.write("로그인 성공")

    # 2. 비로그인 상태일 때 화면
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