/*
 * Cloud IoT Water Quality Sensor Node (ESP32)
 * Major Project: Water Quality Prediction for Aquaculture using AI
 *
 * Connections:
 * 1. DS18B20 Temp Sensor: Data -> GPIO 4 (with a 4.7k pull-up resistor to 3.3V)
 * 2. Analog pH Sensor: Output -> GPIO 34 (ADC1_CH6)
 * 3. Analog Turbidity Sensor: Output -> GPIO 35 (ADC1_CH7)
 * 4. Analog TDS/EC Sensor: Output -> GPIO 32 (ADC1_CH4)
 * 5. Analog Dissolved Oxygen (DO) Sensor: Output -> GPIO 33 (ADC1_CH5)
 * 6. I2C 16x2 LCD Screen: GND->GND, VCC->VIN(5V), SDA->GPIO 21, SCL->GPIO 22
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <time.h>

// Wi-Fi Credentials
const char* ssid     = "YOUR_WIFI_SSID";     // Replace with your Wi-Fi SSID
const char* password = "YOUR_WIFI_PASSWORD"; // Replace with your Wi-Fi Password

// Firebase Database URL
// MUST end with a '/' (e.g. "https://aquaculture-iot-default-rtdb.firebaseio.com/")
const char* firebase_url = "YOUR_FIREBASE_DATABASE_URL/";

// Pin configurations
#define ONE_WIRE_BUS 4
#define PH_PIN 34
#define TURBIDITY_PIN 35
#define TDS_PIN 32
#define DO_PIN 33

// NTP Time Server config (for IST: UTC + 5:30 -> 5.5 * 3600 = 19800 seconds)
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 19800; 
const int   daylightOffset_sec = 0;

// Setup hardware
LiquidCrystal_I2C lcd(0x27, 16, 2);
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

const float ADC_REF = 3.3;
const float ADC_RESOLUTION = 4095.0;
bool displayPageOne = true;

// Get network time formatted as "YYYY-MM-DD HH:MM:SS"
String getFormattedTime() {
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)){
    return "";
  }
  char timeStringBuff[30];
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S", &timeinfo);
  return String(timeStringBuff);
}

void setup() {
  Serial.begin(115200);
  
  // Init LCD
  lcd.init();
  lcd.backlight();
  
  lcd.setCursor(0, 0);
  lcd.print("Connecting WiFi");
  
  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Connected!");
  delay(1000);
  lcd.clear();
  
  // Initialize NTP time
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  
  sensors.begin();
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
  pinMode(TDS_PIN, INPUT);
  pinMode(DO_PIN, INPUT);
}

// Convert ADC value to voltage
float readVoltage(int pin) {
  int raw = analogRead(pin);
  return (raw / ADC_RESOLUTION) * ADC_REF;
}

// Convert pH sensor voltage to pH value
float getpHValue() {
  float voltage = readVoltage(PH_PIN);
  float pH = 7.0 + ((2.5 - voltage) * 3.5); 
  if (pH < 0.0) pH = 0.0;
  if (pH > 14.0) pH = 14.0;
  return pH;
}

// Convert Turbidity sensor voltage to NTU units
float getTurbidityValue() {
  float voltage = readVoltage(TURBIDITY_PIN);
  float turbidity = 0.0;
  if (voltage < 2.5) {
    turbidity = 3000.0;
  } else {
    turbidity = -1120.4 * (voltage * voltage) + 5742.3 * voltage - 4353.8;
  }
  if (turbidity < 0.0) turbidity = 0.0;
  return turbidity;
}

// Convert TDS voltage to Electrical Conductivity (EC) in uS/cm
float getConductivityValue(float temp) {
  float voltage = readVoltage(TDS_PIN);
  float compensationCoefficient = 1.0 + 0.02 * (temp - 25.0);
  float compensationVoltage = voltage / compensationCoefficient;
  float conductivity = (133.42 * pow(compensationVoltage, 3) - 255.86 * pow(compensationVoltage, 2) + 857.39 * compensationVoltage) * 1.5;
  if (conductivity < 0.0) conductivity = 0.0;
  return conductivity;
}

// Convert DO sensor voltage to mg/L
float getDOValue(float temp) {
  float voltage = readVoltage(DO_PIN);
  float doValue = voltage * 5.0; 
  return doValue;
}

void loop() {
  sensors.requestTemperatures();
  float temp = sensors.getTempCByIndex(0);
  if (temp == DEVICE_DISCONNECTED_C) {
    temp = 25.0; 
  }
  
  float ph = getpHValue();
  float turbidity = getTurbidityValue();
  float conductivity = getConductivityValue(temp);
  float dissolvedOxygen = getDOValue(temp);
  float ammonia = 0.012; // Static baseline ammonia
  String timestamp = getFormattedTime();
  
  if (timestamp == "") {
    // If NTP fails, get system up-time
    timestamp = String(millis() / 1000) + " sec";
  }
  
  // 1. Post to Firebase over WiFi
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String requestUrl = String(firebase_url) + "sensor_readings.json";
    
    http.begin(requestUrl);
    http.addHeader("Content-Type", "application/json");
    
    // Construct JSON Payload
    String jsonPayload = "{\"timestamp\":\"" + timestamp + "\"" +
                         ",\"temperature\":" + String(temp, 2) + 
                         ",\"ph\":" + String(ph, 2) + 
                         ",\"dissolved_oxygen\":" + String(dissolvedOxygen, 2) + 
                         ",\"turbidity\":" + String(turbidity, 2) + 
                         ",\"conductivity\":" + String(conductivity, 2) + 
                         ",\"ammonia\":" + String(ammonia, 3) + "}";
                         
    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      Serial.print("Cloud Synced! Code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error sending POST: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  }
  
  // 2. Display on local LCD (Cycle pages)
  lcd.clear();
  if (displayPageOne) {
    lcd.setCursor(0, 0);
    lcd.print("Temp: "); lcd.print(temp, 1); lcd.print(" C");
    lcd.setCursor(0, 1);
    lcd.print("pH:   "); lcd.print(ph, 1);
  } else {
    lcd.setCursor(0, 0);
    lcd.print("DO:   "); lcd.print(dissolvedOxygen, 1); lcd.print(" mg/L");
    lcd.setCursor(0, 1);
    lcd.print("Turb: "); lcd.print(turbidity, 0); lcd.print(" NTU");
  }
  
  displayPageOne = !displayPageOne;
  
  // Local Water Classification logic for physical buzzer
  int status = 0; // 0: Optimal, 1: Warning, 2: Critical
  if (dissolvedOxygen < 3.0 || ph < 5.5 || ph > 9.5 || temp < 15.0 || temp > 36.0) {
    status = 2; // Critical
  } else if (dissolvedOxygen < 5.0 || ph < 6.5 || ph > 8.5 || temp < 20.0 || temp > 33.0 || turbidity > 50.0 || conductivity > 2500.0 || conductivity < 300.0) {
    status = 1; // Warning
  }

  // Control Buzzer Alarm (Beeps for 5 seconds total)
  if (status == 2) {
    // Critical: Rapid beeps (10 cycles of 250ms ON, 250ms OFF = 5000ms)
    for (int i = 0; i < 10; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(250);
      digitalWrite(BUZZER_PIN, LOW);
      delay(250);
    }
  } else if (status == 1) {
    // Warning: Slow pulse beeps (5 cycles of 500ms ON, 500ms OFF = 5000ms)
    for (int i = 0; i < 5; i++) {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(500);
      digitalWrite(BUZZER_PIN, LOW);
      delay(500);
    }
  } else {
    // Silent for Optimal Zone (5 seconds delay)
    digitalWrite(BUZZER_PIN, LOW);
    delay(5000);
  }
}
