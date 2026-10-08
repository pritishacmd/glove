#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <math.h>

#define MPU 0x68

int touchPins[5] = {
  D1,
  D2,
  D5,
  D6,
  D7
};

const char* AP_SSID = "GloveCare-ESP8266";
const char* AP_PASSWORD = "GloveCare123";

const char* WIFI_SSID = "";
const char* WIFI_PASSWORD = "";

ESP8266WebServer server(80);

int16_t ax = 0;
int16_t ay = 0;
int16_t az = 0;

int16_t gx = 0;
int16_t gy = 0;
int16_t gz = 0;

int touchValues[5] = {
  0, 0, 0, 0, 0
};

float pitch = 0.0;
float roll = 0.0;

unsigned long lastSensorRead = 0;

const unsigned long sensorInterval = 40;


void enableCors()
{
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}


void readMPU6050()
{
  Wire.beginTransmission(MPU);
  Wire.write(0x3B);

  if (Wire.endTransmission(false) != 0)
  {
    return;
  }

  Wire.requestFrom(MPU, 14);

  if (Wire.available() < 14)
  {
    return;
  }

  ax = (Wire.read() << 8) | Wire.read();
  ay = (Wire.read() << 8) | Wire.read();
  az = (Wire.read() << 8) | Wire.read();

  Wire.read();
  Wire.read();

  gx = (Wire.read() << 8) | Wire.read();
  gy = (Wire.read() << 8) | Wire.read();
  gz = (Wire.read() << 8) | Wire.read();


  float axG = ax / 16384.0;
  float ayG = ay / 16384.0;
  float azG = az / 16384.0;


  pitch = atan2(
    axG,
    sqrt(
      (ayG * ayG) +
      (azG * azG)
    )
  ) * 180.0 / PI;


  roll = atan2(
    ayG,
    azG
  ) * 180.0 / PI;
}


void readTouchSensors()
{
  for (int i = 0; i < 5; i++)
  {
    touchValues[i] = digitalRead(touchPins[i]);
  }
}


void readAllSensors()
{
  readTouchSensors();
  readMPU6050();
}


void sendSerialData()
{
  Serial.print("DATA,");
  Serial.print(millis());
  Serial.print(",");
  Serial.print(touchValues[0]);
  Serial.print(",");
  Serial.print(touchValues[1]);
  Serial.print(",");
  Serial.print(touchValues[2]);
  Serial.print(",");
  Serial.print(touchValues[3]);
  Serial.print(",");
  Serial.print(touchValues[4]);
  Serial.print(",");
  Serial.print(ax);
  Serial.print(",");
  Serial.print(ay);
  Serial.print(",");
  Serial.print(az);
  Serial.print(",");
  Serial.print(gx);
  Serial.print(",");
  Serial.print(gy);
  Serial.print(",");
  Serial.println(gz);
}


void handleData()
{
  enableCors();

  float axG = ax / 16384.0;
  float ayG = ay / 16384.0;
  float azG = az / 16384.0;

  float gxDps = gx / 131.0;
  float gyDps = gy / 131.0;
  float gzDps = gz / 131.0;


  String json = "{";

  json += "\"touch\":[";

  for (int i = 0; i < 5; i++)
  {
    json += String(touchValues[i]);

    if (i < 4)
    {
      json += ",";
    }
  }

  json += "],";


  json += "\"accel\":{";

  json += "\"x\":" + String(axG, 3) + ",";
  json += "\"y\":" + String(ayG, 3) + ",";
  json += "\"z\":" + String(azG, 3);

  json += "},";


  json += "\"gyro\":{";

  json += "\"x\":" + String(gxDps, 2) + ",";
  json += "\"y\":" + String(gyDps, 2) + ",";
  json += "\"z\":" + String(gzDps, 2);

  json += "},";


  json += "\"rawAccel\":{";

  json += "\"x\":" + String(ax) + ",";
  json += "\"y\":" + String(ay) + ",";
  json += "\"z\":" + String(az);

  json += "},";


  json += "\"rawGyro\":{";

  json += "\"x\":" + String(gx) + ",";
  json += "\"y\":" + String(gy) + ",";
  json += "\"z\":" + String(gz);

  json += "},";


  json += "\"orientation\":{";

  json += "\"pitch\":" + String(pitch, 2) + ",";
  json += "\"roll\":" + String(roll, 2);

  json += "},";


  json += "\"timestamp\":" + String(millis());

  json += "}";


  server.send(200, "application/json", json);
}


void handleOptions()
{
  enableCors();

  server.send(204);
}


void handleRoot()
{
  enableCors();

  String message = "";

  message += "GloveCare AI ESP8266\n";
  message += "Sensor server is running.\n\n";
  message += "Endpoint:\n";
  message += "/data\n";

  server.send(
    200,
    "text/plain",
    message
  );
}


void setup()
{
  Serial.begin(115200);

  delay(500);


  for (int i = 0; i < 5; i++)
  {
    pinMode(
      touchPins[i],
      INPUT
    );
  }


  Wire.begin(D3, D4);

  delay(100);


  Wire.beginTransmission(MPU);

  Wire.write(0x6B);
  Wire.write(0x00);

  Wire.endTransmission();


  Serial.println();
  Serial.println("==============================");
  Serial.println("GLOVECARE AI");
  Serial.println("MULTISENSOR GLOVE");
  Serial.println("==============================");


  WiFi.mode(WIFI_AP_STA);


  WiFi.softAP(
    AP_SSID,
    AP_PASSWORD
  );


  Serial.println();
  Serial.println("ESP8266 ACCESS POINT");
  Serial.print("SSID: ");
  Serial.println(AP_SSID);

  Serial.print("PASSWORD: ");
  Serial.println(AP_PASSWORD);

  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());


  if (
    strlen(WIFI_SSID) > 0 &&
    strlen(WIFI_PASSWORD) > 0
  )
  {
    WiFi.begin(
      WIFI_SSID,
      WIFI_PASSWORD
    );

    Serial.println();
    Serial.println("Connecting to Wi-Fi...");

    unsigned long startTime = millis();

    while (
      WiFi.status() != WL_CONNECTED &&
      millis() - startTime < 15000
    )
    {
      delay(500);
      Serial.print(".");
    }

    Serial.println();

    if (WiFi.status() == WL_CONNECTED)
    {
      Serial.println("Wi-Fi connected.");

      Serial.print("Wi-Fi IP: ");
      Serial.println(WiFi.localIP());
    }
    else
    {
      Serial.println("Wi-Fi connection failed.");
      Serial.println("AP mode is still available.");
    }
  }


  server.on(
    "/",
    HTTP_GET,
    handleRoot
  );


  server.on(
    "/data",
    HTTP_GET,
    handleData
  );


  server.on(
    "/data",
    HTTP_OPTIONS,
    handleOptions
  );


  server.begin();

  Serial.println();
  Serial.println("HTTP SERVER READY");
  Serial.println("Endpoint: /data");
  Serial.println("==============================");
}


void loop()
{
  server.handleClient();


  if (
    millis() - lastSensorRead >=
    sensorInterval
  )
  {
    lastSensorRead = millis();

    readAllSensors();

    sendSerialData();
  }
}
