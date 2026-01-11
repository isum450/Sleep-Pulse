import csv
import pandas as pd
import matplotlib.pyplot as plt

data = list()
f = open("./sensor_datalog.csv",
         'r',
         names=['timestamp', 'motion', 'humidity', 'temperature', 'illuminance'],
         encoding='utf-t-sig'
         )
rea = csv.reader(f)
for row in rea:
    data.append(row)
f.close

plt.plot()
plt.plot()
plt.plot()
plt.plot()

plt.xlabel('time', labelpad=15)
plt.ylabel('value', labelpad=15)

plt.title()
plt.legend()
plt.show()