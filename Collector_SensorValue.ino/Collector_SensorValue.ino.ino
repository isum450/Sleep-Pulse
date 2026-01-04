#include<Wire.h>

const int MPU=0x68;//MPU6050 I2C주소

int AcX,AcY,AcZ,Tmp,GyX,GyY,GyZ;

void get6050();

void setup() {
  Wire.begin(27, 26);
  Wire.beginTransmission(MPU);
  Wire.write(0x6B);
  Wire.write(0);//MPU6050 을 동작 대기 모드로 변경
  Wire.endTransmission(true);
  Serial.begin(115200);
  //pinMode(32, INPUT);
}

void loop() {
  //int illuminanceValue = analogRead(32); //조도센서 값 측정
  //Serial.println(illuminanceValue);      //조도센서 값 출력
  //delay(100);

  get6050();//센서값 갱신
  //받아온 센서값을 출력
  Serial.print(AcX);
  Serial.print("");
  Serial.print(AcY);
  Serial.print("");
  Serial.print(AcZ);
  Serial.println();
  delay(15);  
}

void get6050(){
  Wire.beginTransmission(MPU);//MPU6050 호출
  Wire.write(0x3B);//AcX 레지스터 위치 요청
  Wire.endTransmission(false);
  // 데이터 요청 시 실제 읽어온 개수를 확인하는 것이 좋다고 함.
  if(Wire.requestFrom(MPU, 14, true) == 14) {
    AcX = Wire.read() << 8 | Wire.read();
    AcY = Wire.read() << 8 | Wire.read();
    AcZ = Wire.read() << 8 | Wire.read();
    Tmp = Wire.read() << 8 | Wire.read();
    GyX = Wire.read() << 8 | Wire.read();
    GyY = Wire.read() << 8 | Wire.read();
    GyZ = Wire.read() << 8 | Wire.read();
  } else {
    // 읽어오지 못했을 때의 처리 (디버깅용)
    // Serial.println("No data from sensor");
  }
}
