/*
 * IoT Water Quality Sensor Node (ESP32) with I2C 16x2 LCD
 * Major Project: Water Quality Prediction for Aquaculture using AI
 *
 * Connections:
 * 1. DS18B20 Temp Sensor: Data connected to GPIO 4 (with a 4.7k pull-up resistor to 3.3V)
 * 2. Analog pH Sensor: Output connected to GPIO 34 (ADC1_CH6)
 * 3. Analog Turbidity Sensor: Output connected to GPIO 35 (ADC1_CH7)
 * 4. Analog TDS/EC Sensor: Output connected to GPIO 32 (ADC1_CH4)
 * 5. Analog Dissolved Oxygen (DO) Sensor: Output connected to GPIO 33 (ADC1_CH5)
 * 6. I2C 16x2 LCD Screen: 
 *    - GND -> GND
 *    - VCC -> VIN (5V)
 *    - SDA -> GPIO 21 (SDA on ESP32)
 *    - SCL -> GPIO 22 (SCL on ESP32)
 */

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Pin configurations
#define ONE_WIRE_BUS 4
#define PH_PIN 34
#define TURBIDITY_PIN 35
#define TDS_PIN 32
#define DO_PIN 33

// Setup I2C LCD (0x27 is standard address, 16 columns, 2 rows)
// Note: If display does not show text, try changing address to 0x3F
LiquidCrystal_I2C lcd(0x27, 16, 2);

// Setup DS18B20 temperature sensor
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// ADC calibration constants (Assume 3.3V reference and 12-bit ADC - 4096 levels)
const float ADC_REF = 3.3;
const float ADC_RESOLUTION = 4095.0;

// LCD cycling display state
bool displayPageOne = true;

void setup() {
  Serial.begin(115200);
  
  // Initialize LCD
  lcd.init();
  lcd.backlight();
  
  // LCD Splash Screen
  lcd.setCursor(0, 0);
  lcd.print("Aquaculture IoT");
  lcd.setCursor(0, 1);
  lcd.print("AI Monitor Init");
  delay(2000);
  lcd.clear();
  
  sensors.begin();
  
  // Configure ADC pins
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
  pinMode(TDS_PIN, INPUT);
  pinMode(DO_PIN, INPUT);
}

// Helper to convert ADC value to voltage
float readVoltage(int pin) {
  int raw = analogRead(pin);
  return (raw / ADC_RESOLUTION) * ADC_REF;
}

// Convert pH sensor voltage to pH value (standard slope calibration)
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
  float doValue = voltage * 5.0; // simple calibration multiplier
  return doValue;
}

void loop() {
  // Read DS18B20 Temperature
  sensors.requestTemperatures();
  float temp = sensors.getTempCByIndex(0);
  if (temp == DEVICE_DISCONNECTED_C) {
    temp = 25.0; 
  }
  
  // Read remaining sensors
  float ph = getpHValue();
  float turbidity = getTurbidityValue();
  float conductivity = getConductivityValue(temp);
  float dissolvedOxygen = getDOValue(temp);
  float ammonia = 0.012; // Static baseline ammonia
  
  // 1. Send data over Serial (JSON for python dashboard bridge)
  Serial.print("{\"temperature\":");
  Serial.print(temp, 2);
  Serial.print(",\"ph\":");
  Serial.print(ph, 2);
  Serial.print(",\"dissolved_oxygen\":");
  Serial.print(dissolvedOxygen, 2);
  Serial.print(",\"turbidity\":");
  Serial.print(turbidity, 2);
  Serial.print(",\"conductivity\":");
  Serial.print(conductivity, 2);
  Serial.print(",\"ammonia\":");
  Serial.print(ammonia, 3);
  Serial.println("}");
  
  // 2. Update LCD screen (cycle information)
  lcd.clear();
  if (displayPageOne) {
    // Page 1: Temp and pH
    lcd.setCursor(0, 0);
    lcd.print("Temp: ");
    lcd.print(temp, 1);
    lcd.print(" C");
    
    lcd.setCursor(0, 1);
    lcd.print("pH:   ");
    lcd.print(ph, 1);
  } else {
    // Page 2: DO and Turbidity
    lcd.setCursor(0, 0);
    lcd.print("DO:   ");
    lcd.print(dissolvedOxygen, 1);
    lcd.print(" mg/L");
    
    lcd.setCursor(0, 1);
    lcd.print("Turb: ");
    lcd.print(turbidity, 0);
    lcd.print(" NTU");
  }
  
  // Toggle the display page state for the next run
  displayPageOne = !displayPageOne;
  
  delay(2000); // 2-second update interval
}
