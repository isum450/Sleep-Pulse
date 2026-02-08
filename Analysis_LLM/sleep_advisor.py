# Analysis_LLM/sleep_advisor.py
#influx DB에서 데이터를 꺼내와서 LLM에게 질문하고 답변을 받아오는 역할을 한다.

import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

def analyze_sleep_data(sensor_summary):
    """
    sensor_summary: { 'avg_temp': 24.5, 'avg_humid': 50, 'avg_move': 100 ... }
    LLM에게 통계 데이터를 주고 점수(0~100)와 피드백을 받아옵니다.
    """
    if not api_key: 
        return 0, "API 키가 설정되지 않아 분석할 수 없습니다."

    # 프롬프트: 명확하게 JSON 출력을 요구합니다.
    prompt = f"""
    당신은 수면 환경 분석 전문가입니다. 아래 측정된 센서 데이터를 기반으로 수면 점수(0~100점)를 매기고 조언을 해주세요.

    [측정 데이터]
    - 평균 움직임: {sensor_summary.get('avg_movement', 0):.1f}
    - 평균 온도: {sensor_summary.get('avg_temperature', 0):.1f}도
    - 평균 습도: {sensor_summary.get('avg_humidity', 0):.1f}%
    - 평균 조도: {sensor_summary.get('avg_illuminance', 0):.1f} lux
    - 실제 수면 시간: {sensor_summary.get('duration', '알수없음')}

    [채점 기준 및 지시사항]
    1. **중요: 수면 시간도 고려하여 점수를 매기세요.** ("짧게 잤지만 꿀잠을 잤다"면 어느정도 점수를 보충할 순 있습니다.)
    2. 오직 **'수면의 질(Quality)'** 에 집중하세요. (온도, 습도, 움직임 안정성 등)
    3. 적정 환경(온도 20~26도, 습도 40~60%, 낮은 조도, 적은 움직임)일수록 100점에 가깝습니다.
    4. 결과는 반드시 JSON 형식으로만 출력하세요.

    [출력 예시]
    {{
        "score": 53,
        "feedback": "수면 시간은 2시간으로 짧아서 수면 점수가 낮지만, 온습도가 완벽하고 뒤척임이 거의 없어 매우 깊은 잠을 주무셨네요!"
    }}
    """

    try:
        response = model.generate_content(prompt)
        text_res = response.text.replace("```json", "").replace("```", "").strip() # 마크다운 제거
        
        # JSON 파싱
        result_json = json.loads(text_res)
        
        return result_json['score'], result_json['feedback']
        
    except Exception as e:
        return 50, f"분석 중 오류 발생: {str(e)}"
    
def get_chat_response(user_question, context_data=None):
    """
    user_question: 사용자의 질문
    context_data: (선택) 최근 수면 데이터 요약본 (문자열)
    """
    
    # 1. AI에게 줄 페르소나(역할) 설정
    system_instruction = "당신은 친절하고 전문적인 '수면 코치'입니다. 사용자의 질문에 대해 수면 건강 관점에서 도움이 되는 조언을 해주세요."
    
    # 2. 만약 최근 수면 데이터가 있다면 프롬프트에 포함 (문맥 주입)
    if context_data:
        prompt = f"""
        [시스템 지시]
        {system_instruction}
        
        [사용자의 최근 수면 데이터]
        {context_data}
        
        [사용자 질문]
        "{user_question}"
        
        위 데이터를 참고하여 사용자의 질문에 답변해주세요. 데이터를 기반으로 구체적이고 맞춤형 조언을 제공하세요.
        """
    else:
        # 데이터가 없으면 일반적인 질문으로 처리
        prompt = f"""
        [시스템 지시]
        {system_instruction}
        
        [사용자 질문]
        "{user_question}"
        """

    try:
        # 3. 제미나이에게 질문
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"죄송합니다. AI 연결 중 오류가 발생했습니다: {str(e)}"