#include<WiFi.h>
#include "DHT.h"
#include<PubSubClient.h>
#include <ArduinoJson.h>
#include "esp_camera.h"

#define CAMERA_MODEL_WROVER_KIT // 카메라 모델 정의
#define DHTPIN 14
#define DHTTPE DHT11

DHT dht(DHTPIN, DHTTPE);

void startCameraServer();

const char* ssid = "TNet2";//Wifi ssid
const char* password = "@@##tee75682";//Wifi password
const char* mqtt_server = "broker.emqx.io"; //wifi IP 주소

camera_config_t config;

WiFiClient espClient;
PubSubClient client(espClient);

void setup_camera()
{
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 4;
  config.pin_d1 = 5;
  config.pin_d2 = 18;
  config.pin_d3 = 19;
  config.pin_d4 = 36;
  config.pin_d5 = 39;
  config.pin_d6 = 34;
  config.pin_d7 = 35;
  config.pin_xclk = 21;
  config.pin_pclk = 22;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
  config.pin_pwdn = -1;  
  config.pin_reset = -1;
  config.xclk_freq_hz = 16000000;
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG;  // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 18;
  config.fb_count = 1;

  // 해상도 품질 관련 설정
  if (config.pixel_format == PIXFORMAT_JPEG) {
    if (psramFound()) {
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_240X240;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }
  // 카메라 초기화 함수 호출, 초기화 실패시 오류 메시지 출력
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  //카메라 센서 정보 가저오는 함수 포인터
  sensor_t *s = esp_camera_sensor_get(); 
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);        // 수직 뒤집기
    s->set_brightness(s, 1);   // 밝기 1올리기
    s->set_saturation(s, -2);  // 채도 낮추기
  }

  startCameraServer();

}

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
  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
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
  setup_camera();
  client.setServer(mqtt_server, 1883);
  client.setSocketTimeout(60); 
  client.setKeepAlive(60);
  client.setCallback(callback);
  dht.begin();
  pinMode(32, INPUT);
}

void loop() {
  if(!client.connected()) {
    reconnect();
  }
  client.loop();

  float h = dht.readHumidity();    // 습도
  float t = dht.readTemperature(); // 온도(섭씨)
  int illuminanceValue = analogRead(32); //조도센서 값 측정

  JsonDocument doc;//JSON형식으로 데이터를 전송하기 위해서
  doc["humidity"] = h;
  doc["temperature"] = t;
  doc["illuminance"] = illuminanceValue;
  char buffer[256];
  serializeJson(doc, buffer);
  client.publish("leesu/sensor/data", buffer);

  Serial.println(buffer);

  delay(500);
}
