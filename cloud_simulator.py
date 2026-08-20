import time
import random
import requests
import argparse
from datetime import datetime

# Helper to classify water quality (same as your ML model logic)
def classify_water(temp, ph, do, turbidity, conductivity, ammonia):
    if (do < 3.0 or ph < 5.5 or ph > 9.5 or ammonia > 0.10 or temp < 15.0 or temp > 36.0):
        return "Critical"
    if (do < 5.0 or ph < 6.5 or ph > 8.5 or ammonia > 0.03 or temp < 20.0 or temp > 33.0 or turbidity > 50.0 or conductivity > 2500.0 or conductivity < 300.0):
        return "Warning"
    return "Optimal"

def run_cloud_simulator(firebase_url, interval=2.0):
    # Ensure URL ends with /
    if not firebase_url.endswith("/"):
        firebase_url += "/"
        
    print(f"Starting Cloud Simulation to: {firebase_url}")
    print("Publishing data points to Firebase Realtime Database. Press Ctrl+C to stop.\n")
    
    # Starting baseline values
    temp = 26.5
    ph = 7.4
    do = 6.2
    turbidity = 20.0
    conductivity = 1100.0
    ammonia = 0.012
    
    try:
        while True:
            # Apply a random walk to simulate smooth time-series changes
            temp = round(max(15.0, min(38.0, temp + random.uniform(-0.15, 0.15))), 2)
            ph = round(max(5.0, min(10.0, ph + random.uniform(-0.05, 0.05))), 2)
            do = round(max(1.0, min(10.0, do + random.uniform(-0.1, 0.1))), 2)
            turbidity = round(max(5.0, min(80.0, turbidity + random.uniform(-0.5, 0.5))), 2)
            conductivity = round(max(300.0, min(3000.0, conductivity + random.uniform(-10.0, 10.0))), 2)
            ammonia = round(max(0.002, min(0.15, ammonia + random.uniform(-0.001, 0.001))), 4)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status = classify_water(temp, ph, do, turbidity, conductivity, ammonia)
            
            # Match database schema expected by app.py
            payload = {
                "timestamp": timestamp,
                "temperature": temp,
                "ph": ph,
                "dissolved_oxygen": do,
                "turbidity": turbidity,
                "conductivity": conductivity,
                "ammonia": ammonia
            }
            
            # Send HTTP POST request directly to Firebase REST endpoint
            target_endpoint = f"{firebase_url}sensor_readings.json"
            response = requests.post(target_endpoint, json=payload)
            
            if response.status_code == 200:
                print(f"[{timestamp}] Sent -> Temp: {temp}°C | pH: {ph} | DO: {do}mg/L | Status: {status} (HTTP 200)")
            else:
                print(f"❌ Error sending data: HTTP {response.status_code} - {response.text}")
                
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nCloud simulator stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firebase Cloud IoT Data Simulator")
    parser.add_argument("--url", type=str, required=True, help="Your Firebase Database URL (starts with https://)")
    parser.add_argument("--rate", type=float, default=2.0, help="Interval in seconds between broadcasts (default 2.0)")
    
    args = parser.parse_args()
    run_cloud_simulator(args.url, args.rate)
