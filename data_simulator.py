import argparse
import time
import random
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Classify water suitability based on standard aquaculture guidelines
def classify_water(temp, ph, do, turbidity, conductivity, ammonia):
    # Critical conditions
    if (do < 3.0 or 
        ph < 5.5 or ph > 9.5 or 
        ammonia > 0.10 or 
        temp < 15.0 or temp > 36.0):
        return 2  # Critical
    
    # Warning conditions
    if (do < 5.0 or 
        ph < 6.5 or ph > 8.5 or 
        ammonia > 0.03 or 
        temp < 20.0 or temp > 33.0 or 
        turbidity > 50.0 or 
        conductivity > 2500.0 or conductivity < 300.0):
        return 1  # Warning
        
    return 0  # Optimal (Safe)

def generate_sample(mode="random"):
    """
    Generates a single water quality sample.
    Modes:
      - 'optimal': forces variables inside optimal range.
      - 'warning': introduces slight stress to some variables.
      - 'critical': introduces severe threat to aquatic life.
      - 'random': randomly selects a mode with bias.
    """
    if mode == "random":
        mode = random.choices(["optimal", "warning", "critical"], weights=[0.60, 0.25, 0.15])[0]

    if mode == "optimal":
        temp = round(random.uniform(24.0, 30.0), 2)
        ph = round(random.uniform(6.8, 8.2), 2)
        do = round(random.uniform(5.5, 9.0), 2)
        turbidity = round(random.uniform(10.0, 28.0), 2)
        conductivity = round(random.uniform(600.0, 1500.0), 2)
        ammonia = round(random.uniform(0.005, 0.02), 4)
    elif mode == "warning":
        # Randomly choose one or two params to trigger warning
        temp = round(random.uniform(18.0, 34.0), 2)
        ph = round(random.uniform(6.0, 9.0), 2)
        do = round(random.uniform(4.0, 5.8), 2)
        turbidity = round(random.uniform(20.0, 65.0), 2)
        conductivity = round(random.uniform(200.0, 3000.0), 2)
        ammonia = round(random.uniform(0.015, 0.05), 4)
    else: # critical
        # Randomly choose at least one fatal param
        trigger = random.choice(["do", "ph", "ammonia", "temp"])
        temp = round(random.uniform(22.0, 28.0), 2)
        ph = round(random.uniform(7.0, 8.0), 2)
        do = round(random.uniform(5.0, 8.0), 2)
        turbidity = round(random.uniform(15.0, 40.0), 2)
        conductivity = round(random.uniform(800.0, 1200.0), 2)
        ammonia = round(random.uniform(0.005, 0.02), 4)
        
        if trigger == "do":
            do = round(random.uniform(1.0, 2.9), 2)
        elif trigger == "ph":
            ph = random.choice([round(random.uniform(4.0, 5.4), 2), round(random.uniform(9.6, 11.0), 2)])
        elif trigger == "ammonia":
            ammonia = round(random.uniform(0.11, 0.50), 4)
        elif trigger == "temp":
            temp = random.choice([round(random.uniform(10.0, 14.9), 2), round(random.uniform(36.1, 42.0), 2)])

    status = classify_water(temp, ph, do, turbidity, conductivity, ammonia)
    return temp, ph, do, turbidity, conductivity, ammonia, status

def generate_historical_dataset(filepath="historical_water_data.csv", num_records=5000):
    print(f"Generating {num_records} historical records...")
    
    start_time = datetime.now() - timedelta(days=30)
    data = []
    
    for i in range(num_records):
        timestamp = (start_time + timedelta(minutes=10 * i)).strftime("%Y-%m-%d %H:%M:%S")
        temp, ph, do, turbidity, conductivity, ammonia, status = generate_sample()
        data.append([timestamp, temp, ph, do, turbidity, conductivity, ammonia, status])
        
    df = pd.DataFrame(data, columns=[
        "Timestamp", "Temperature", "pH", "Dissolved_Oxygen", 
        "Turbidity", "Conductivity", "Ammonia", "Status"
    ])
    
    df.to_csv(filepath, index=False)
    print(f"Dataset successfully saved to {filepath}")
    print(df["Status"].value_counts().rename({0: "Optimal", 1: "Warning", 2: "Critical"}))

def live_iot_stream(db_path="water_quality.db", interval=2.0):
    print(f"Initializing IoT Live Feed SQLite Database at {db_path}...")
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
    
    # Initialize with a random starting point
    temp, ph, do, turbidity, conductivity, ammonia, _ = generate_sample(mode="optimal")
    
    print("Starting live telemetry broadcast. Press Ctrl+C to stop.")
    try:
        while True:
            # Apply random walk to simulate gradual shifts in water state
            temp = round(max(10.0, min(45.0, temp + random.uniform(-0.15, 0.15))), 2)
            ph = round(max(4.0, min(11.0, ph + random.uniform(-0.05, 0.05))), 2)
            do = round(max(0.5, min(12.0, do + random.uniform(-0.1, 0.1))), 2)
            turbidity = round(max(5.0, min(100.0, turbidity + random.uniform(-0.5, 0.5))), 2)
            conductivity = round(max(100.0, min(5000.0, conductivity + random.uniform(-10.0, 10.0))), 2)
            ammonia = round(max(0.001, min(0.600, ammonia + random.uniform(-0.002, 0.002))), 4)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("""
                INSERT INTO sensor_readings (timestamp, temperature, ph, dissolved_oxygen, turbidity, conductivity, ammonia)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, temp, ph, do, turbidity, conductivity, ammonia))
            conn.commit()
            
            status_label = {0: "Optimal", 1: "Warning", 2: "Critical"}[
                classify_water(temp, ph, do, turbidity, conductivity, ammonia)
            ]
            
            print(f"[{timestamp}] IoT Sensor Broadcast -> Temp: {temp}°C | pH: {ph} | DO: {do}mg/L | Status: {status_label}")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nIoT Telemetry feed stopped.")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IoT Water Quality Data Simulator")
    parser.add_argument("--generate", action="store_true", help="Generate CSV dataset for model training")
    parser.add_argument("--live", action="store_true", help="Simulate a real-time IoT sensor telemetry stream into SQLite")
    parser.add_argument("--records", type=int, default=5000, help="Number of records to generate for CSV")
    
    args = parser.parse_args()
    
    if args.live:
        live_iot_stream()
    else:
        # Default behavior: generate CSV if explicitly requested or if no arguments are provided
        generate_historical_dataset(num_records=args.records)
