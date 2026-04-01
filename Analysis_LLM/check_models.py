# check_models.py (프로젝트 폴더에 만들고 실행)
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# (스트림릿 클라우드면 secrets에서 가져오도록 수정 필요하지만, 로컬 테스트용으로 .env 추천)
if not api_key:
    print("API 키가 없습니다.")
else:
    genai.configure(api_key=api_key)
    print("사용 가능한 모델 목록:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")