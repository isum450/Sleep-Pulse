import csv
import pandas as pd
import matplotlib.pyplot as plt

f = pd.read_csv('./sensor_datalog.csv', 
                names=['timestamp', 'motion', 'humidity', 'temperature', 'illuminance'],
                quotechar='|',
                header=0
                )
f['motion'] = f['motion'].astype(str).str.replace('"', '').astype(float)
f['illuminance'] = f['illuminance'].astype(str).str.replace('"', '').astype(float)
f['humidity'] = f['humidity'].astype(float)
f['temperature'] = f['temperature'].astype(float)


fig, ax = plt.subplots(4, 1, figsize=(12, 10))


# 첫 번째 칸: Motion
ax[0].plot(f['motion'], color='red', label='Motion')
ax[0].set_ylabel('Motion')
ax[0].legend(loc='upper right')
ax[0].grid(True) # 격자 무늬 추가 (보기 편하게)

# 두 번째 칸: Humidity
ax[1].plot(f['humidity'], color='green', label='Humidity')
ax[1].set_ylabel('Humidity (%)')
ax[1].legend(loc='upper right')
ax[1].grid(True)

# 세 번째 칸: Temperature
ax[2].plot(f['temperature'], color='blue', label='Temperature')
ax[2].set_ylabel('Temp (C)')
ax[2].legend(loc='upper right')
ax[2].grid(True)

# 네 번째 칸: Illuminance
ax[3].plot(f['illuminance'], color='orange', label='Illuminance')
ax[3].set_ylabel('Lux')
ax[3].set_xlabel('Time (Index)') # 맨 마지막 그래프에만 X축 라벨 표시
ax[3].legend(loc='upper right')
ax[3].grid(True)

plt.xlabel('time', labelpad=15)
plt.ylabel('value', labelpad=15)

plt.tight_layout()
plt.suptitle('Sensor Data Log', fontsize=20, y=1.02) 

plt.show()