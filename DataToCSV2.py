import serial
import csv
import time
import statistics
from datetime import datetime

ser = serial.Serial('COM4', 115200)
FILENAME = 'sensor_datalog.csv'

buffer_hum = []
buffer_temp = []
buffer_lux = []
buffer_move = []

try:
    with open(FILENAME, 'x', newline='') as f:
        pass 
except FileExistsError:
    pass

try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if not line: continue

            try:
                parts = line,split(',')
                if len(parts) >= 4:
                    m = int(parts[0])
                    h = float(parts[1])
                    t = float(parts[2])
                    l = int(parts[3])

                    buffer_hum.append(h)
                    buffer_temp.append(t)
                    buffer_lux.append(l)

                    print("움직임{m}, 습도{h}%, 온도{t}, 조도{3}")

            except ValueError:
                continue

        if len(buffer_hum) >= 30:
            timestamp = datetime.now().strftime("%y-%m-%d %H:%M")

            avg_hum = round(statistics.mean(buffer_hum), 1)
            avg_temp = round(statistics.mean(buffer_temp), 1)
            avg_lux = int(statistics.mean(buffer_lux) / 4)

            data_value_str = f"0,{avg_hum},{avg_temp},{avg_lux},0"

            with open(FILENAME, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, data_value_str])

            buffer_hum.clear()
            buffer_temp.clear()
            buffer_lux.clear()

            time.sleep(0.01)

except KeyboardInterrupt:
    ser.close()