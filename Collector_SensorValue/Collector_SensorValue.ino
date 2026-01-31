#include<WiFi.h>
#include<Wire.h>
#include "DHT.h"
#include<PubSubClient.h>
#include <ArduinoJson.h>
#include <math.h>

#define DHTPIN 33
#define DHTTPE DHT11

DHT dht(DHTPIN, DHTTPE);

const int MPU=0x68;//MPU6050 I2C주소
const char* ssid = "U+Net7428";//Wifi ssid
const char* password = "1J3A4AF87#";//Wifi password
const char* mqtt_server = "broker.hivemq.com"; //wifi IP 주소

WiFiClient espClient;
PubSubClient client(espClient);

int AcX,AcY,AcZ,Tmp,GyX,GyY,GyZ;

void get6050();

void setup_wifi()
{
  delay(10);
  Serial.begin(115200);
  Serial.println();
  Serial.print("Connection to ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while(WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length)
{
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  for(int i = 0; i < length; i++)
  {
    Serial.print((char)payload[i]);
  }
  Serial.println();
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ArduinoClient")) {
      Serial.println("connected");
      client.subscribe("leesu/sensor/data");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setSocketTimeout(60); 
  client.setKeepAlive(60);
  client.setCallback(callback);
  Wire.begin(27, 26);
  Wire.beginTransmission(MPU);
  Wire.write(0x6B);
  Wire.write(0);//MPU6050 을 동작 대기 모드로 변경
  Wire.endTransmission(true);
  dht.begin();
  pinMode(32, INPUT);
}

void loop() {
  if(!client.connected()) {
    reconnect();
  }
  client.loop();

  get6050();//센서값 갱신
  //받아온 센서값을 출력
  float VectorMove = sqrt(pow(AcX,2) + pow(AcY, 2) + pow(AcZ, 2));
  float h = dht.readHumidity();    // 습도
  float t = dht.readTemperature(); // 온도(섭씨)
  int illuminanceValue = analogRead(32); //조도센서 값 측정

  JsonDocument doc;//JSON형식으로 데이터를 전송하기 위해서
  doc["motion"] = VectorMove;
  doc["humidity"] = h;
  doc["temperature"] = t;
  doc["illuminance"] = illuminanceValue;
  char buffer[256];
  serializeJson(doc, buffer);
  client.publish("leesu/sensor/data", buffer);

  Serial.println(buffer);

 /*
  Serial.print(VectorMove);
  Serial.print(",");
  Serial.print(h);
  Serial.print(",");
  Serial.print(t);
  Serial.print(",");
  Serial.println(illuminanceValue);      //조도센서 값 출력
*/
  delay(2000);
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
  } 
}
