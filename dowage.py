import pandas as pd
import matplotlib.pyplot as plt

filename = 'C:/Users/ju/Sleep-Pulse/Sleep-Pulse/sensor_datalog.csv'
df = pd.read_csv(filename, header=None, names=['Time', 'DataVlaue'])

split_data = df['DataVlaue'].str.split(',', expand=True)
split_data = split_data.astype(float)

df['Time'] = pd.to_datetime(df['Time'], format='%Y-%m-%d %H: %M: %S')

plt.figure(figsize=(12, 10))

plt.subplot(4, 1, 1)
plt.plot(df['Time'], split_data[0], color='red')
plt.title('move')
plt.grid(True)

plt.subplot(4, 1, 2)
plt.plot(df['Time'], split_data[1], color='orange')
plt.title('hum')
plt.grid(True)

plt.subplot(4, 1, 3)
plt.plot(df['Time'], split_data[2], color='blue')
plt.title('temp')
plt.grid(True)

plt.subplot(4, 1, 4)
plt.plot(df['Time'], split_data[3], color='green')
plt.title('hum')
plt.grid(True)
plt.tight_layout()
plt.show()