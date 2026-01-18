import time
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS


# 1. URL: 웹페이지 주소창에 보이는 주소 (예: https://us-east-1-1.aws.cloud2.influxdata.com)
url = "https://us-east-1-1.aws.cloud2.influxdata.com/"

# 2. Token: 아까 복사해둔 긴 암호
token = "2ajd0VIjjQWniBBz5m2SAyMeNW1ilKJgAQK4Mp21LXQuOmdDgfgYG4X6_XoA_bZzjGCxZux58DAQR9FT4Cgkug=="

# 3. Org: 가입할 때 쓴 이메일 주소 혹은 화면 왼쪽 프로필 아이콘 밑에 써있는 조직 이름
org = "personal project"

bucket = "sleep_pulse"

# 연결 시작
client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

print("InfluxDB 데이터 전송 시작")

for i in range(5):
    # 데이터 구조: 
    # Measurement(큰 분류): environment
    # Tag(태그): location=bedroom (침실 데이터)
    # Field(값): temperature, humidity (실제 센서 값)
    
    p = Point("environment") \
        .tag("location", "bedroom") \
        .field("temperature", 24.0 + i) \
        .field("humidity", 50.0 - i) \
        .field("movement", 0.0)

    write_api.write(bucket=bucket, org=org, record=p)
    print(f"데이터 저장 중... (온도: {24.0 + i})")
    time.sleep(1)

print("전송 완료!")
client.close()