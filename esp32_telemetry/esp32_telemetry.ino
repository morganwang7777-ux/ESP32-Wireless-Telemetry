#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// fill these in before uploading
const char* WIFI_NAME = "YOUR_WIFI_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";
const char* LAPTOP_IP = "192.168.x.x";   // laptop's IPv4 from ipconfig
const int   LAPTOP_PORT = 5005;          // has to match logger.py

#define OLED_ADDRESS 0x3C   // found with an I2C scanner
#define POT_PIN 34          // ADC1 pin, ADC2 pins stop working once Wi-Fi is on
Adafruit_SSD1306 display(128, 64, &Wire, -1);
WiFiUDP udp;

unsigned long seq = 0;   // packet number, used on the laptop to count lost packets

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);   // SDA, SCL
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    Serial.println("OLED not found - check wiring");
  }
  display.setTextColor(SSD1306_WHITE);
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("Connecting to Wi-Fi...");
  display.display();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_NAME, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connected! ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  int raw = analogRead(POT_PIN);
  int throttle = map(raw, 0, 4095, 0, 100);
  int rssi = WiFi.RSSI();

  // e.g. {"seq":42,"t_ms":12345,"throttle":25,"rssi":-55}
  char msg[100];
  snprintf(msg, sizeof(msg),
           "{\"seq\":%lu,\"t_ms\":%lu,\"throttle\":%d,\"rssi\":%d}",
           seq, millis(), throttle, rssi);

  udp.beginPacket(LAPTOP_IP, LAPTOP_PORT);
  udp.print(msg);
  udp.endPacket();

  Serial.println(msg);   // same data over USB as a backup
  seq++;

  // only redraw the OLED every 4th packet so drawing doesn't eat into the send rate
  if (seq % 4 == 0) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.print("TX -> ");
    display.println(LAPTOP_IP);
    display.setTextSize(2);
    display.setCursor(0, 16);
    display.print("THR ");
    display.print(throttle);
    display.println("%");
    display.setTextSize(1);
    display.setCursor(0, 40);
    display.print("Signal: "); display.print(rssi); display.println(" dBm");
    display.print("Sent: ");   display.println(seq);
    display.display();
  }

  delay(50);   // aiming for 20/s, actually measured ~17.5/s because of the loop overhead
}
