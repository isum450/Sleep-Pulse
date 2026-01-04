import pandas as pd
from dask import dataframe as dd
import time

file = '파일이름.csv'#불러올 파일 경로

#파일을 불러내는 데 걸리는 시간 측정
start = time.time()
chunk = pd.read_csv('파일경로', chunksize = 청크크기) #청크 단위로 파일 불러오기
end = time.time()


total_df = pd.concat(chunk)#청크를 병합하여 데이터 프레임 만들기
total_df.to_csv(저장경로, ...)#병합된 데이터 프레임을 새로운 파일로 저장
print("파일 불러오는 데 걸리는 시간:", end - start)

