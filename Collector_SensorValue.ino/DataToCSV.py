import serial
import csv
from datetime import datetime
ser = serial.Serial('COM5', 115200)#포트

with open('sensor_datalog.csv', 'a', newline ='') as f:
    writer = csv.writer(f)
    while True:
        data = ser.readline().decode().strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H: %M: %S")
        writer.writerow([timestamp, data])
        print(f"{timestamp}, {data}")
        