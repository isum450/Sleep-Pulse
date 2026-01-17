import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('sensor_datalog.csv', names=['Time', 'Value'])
df['Value'] = pd.to_numeric(df['Value'], errors='coerce')

#이상값 제거
#df = df[df['Value'] > 100]
  

#통계 분석
print("총 데이터 수 ")