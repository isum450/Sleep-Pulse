import pandas as pd

filename = 'C:/Users/ju/Sleep-Pulse/Sleep-Pulse/sleep_data.csv'

df_raw = pd.read_csv(filename, header=None, 
                        names=['Time', 'Movement', 'Humidity', 'Temperature', 'Illuminance', 'Trash'])

if 'Trash' in df_raw.columns:
        df = df_raw.drop(columns=['Trash'])

cols_to_numeric = ['Movement', 'Humidity', 'Temperature', 'Illuminance']
for col in cols_to_numeric:
    df[col] = pd.to_numeric(df[col], errors='coerce') # 에러나면 NaN 처리

# 2. 점수 계산 함수
def calculate_score(row):
    temp = row['Temperature']
    humid = row['Humidity']
    lux = row['Illuminance']
    #sound = row['Sound']

    #온도 35점 만점
    if 20 <= temp < 22:
        score_temp = 35
    elif (18 <= temp < 20) or (22 <= temp < 24):
        score_temp = 30
    elif (16 <= temp < 18) or (24 <= temp < 26):
        score_temp = 25
    else:
        score_temp = 20

    #조도 27.5점 만점
    if lux < 30:
        score_lux = 27.5
    elif 30 <= lux < 60:
        score_lux = 25
    elif 60 <= lux < 150:
        score_lux = 22.5
    elif 150 <= lux < 300:
        score_lux = 20
    elif 300 <= lux < 600:
        score_lux = 17.5
    else:
        score_lux = 15
    
    #습도 10점 만점
    if temp < 16: target_humid = 70
    elif 16 <= temp < 18: target_humid = 65
    elif 18 <= temp < 20: target_humid = 60
    elif 20 <= temp < 22: target_humid = 50
    elif 22 <= temp < 24: target_humid = 40
    elif 24 <= temp < 26: target_humid = 30
    else: target_humid = 25

    #습도 오차 범위로 점수 깍는 로직
    humid_diff = abs(humid - target_humid)
    deduction = (humid_diff / 10.0) * 1
    score_humid = 10 - deduction

    #소리 27.5점 만점
    score_sound = 0
    #if sound < 30: score_sound = 27.5
    #elif 30 <= sound < 35: score_sound = 23
    #elif 35 <= sound < 40: score_sound = 19.5
    #elif 40 <= sound < 45: score_sound = 17.5
    #elif 45 <= sound < 50: score_sound = 16
    #elif 50 <= sound < 55: score_sound = 14
    #else: score_sound = 12.5
    

    total_score = score_temp + score_lux + score_humid + score_sound
    return total_score



target = 2

selected_row = df.iloc[target]
final_score = calculate_score(selected_row)

print(f"시간: {selected_row['Time']}")
print(f"움직임: {selected_row['Movement']}")
print(f"습도: {selected_row['Humidity']}")
print(f"온도: {selected_row['Temperature']}")
print(f"조도: {selected_row['Illuminance']}")
#print(f"소리: {selected_row['sound']}")
print(f"점수: {final_score:.2f}")