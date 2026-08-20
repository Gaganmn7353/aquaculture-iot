import serial
import sqlite3
import json
import time
import sys
import argparse
from datetime import datetime

def setup_database(db_path="water_quality.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            temperature REAL,
            ph REAL,
            dissolved_oxygen REAL,
            turbidity REAL,
            conductivity REAL,
            ammonia REAL
        )
    """)
    conn.commit()
    conn.close()

def log_to_db(data, db_path="water_quality.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO sensor_readings (timestamp, temperature, ph, dissolved_oxygen, turbidity, conductivity, ammonia)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        timestamp,
        data.get("temperature", 25.0),
        data.get("ph", 7.0),
        data.get("dissolved_oxygen", 6.0),
        data.get("turbidity", 20.0),
        data.get("conductivity", 1000.0),
        data.get("ammonia", 0.01)
    ))
    conn.commit()
    conn.close()
    print(f"[{timestamp}] Saved: Temp: {data.get('temperature')} | pH: {data.get('ph')} | DO: {data.get('dissolved_oxygen')} | EC: {data.get('conductivity')}")

def run_bridge(port, baudrate=115200, db_path="water_quality.db"):
    print(f"Connecting to ESP32 on port {port} at {baudrate} baud...")
    
    try:
        ser = serial.Serial(port, baudrate, timeout=3.0)
        # Flush input buffer
        ser.reset_input_buffer()
        print("Connected! Listening for sensor data packets...")
    except serial.SerialException as e:
        print(f"Error opening serial port {port}: {e}")
        print("\nAvailable ports:")
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            print(f" - {p.device}: {p.description}")
        sys.exit(1)
        
    setup_database(db_path)
    
    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Check if it looks like JSON
                if line.startswith("{") and line.endswith("}"):
                    try:
                        sensor_data = json.loads(line)
                        log_to_db(sensor_data, db_path)
                    except json.JSONDecodeError:
                        print(f"Malformed JSON data received: {line}")
                else:
                    # Log non-JSON print statements from ESP32 for debugging
                    print(f"[ESP32 Debug]: {line}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nClosing serial bridge...")
    finally:
        ser.close()
        print("Serial port closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ESP32 to SQLite Serial Bridge")
    parser.add_argument("--port", type=str, default="COM3", help="Serial port of your ESP32 (e.g., COM3 on Windows or /dev/ttyUSB0 on Linux)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    
    args = parser.parse_args()
    run_bridge(args.port, args.baud)
