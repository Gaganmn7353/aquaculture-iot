import os
import pickle
import sqlite3
import time
import requests
import pandas as pd
import numpy as np
import streamlit as st

# Configure page
st.set_page_config(
    page_title="IoT Water Quality AI Dashboard",
    page_icon="🌊",
    layout="wide",
)

# Title & Description
st.title("🌊 IoT-Based Water Quality Monitor for Sustainable Aquaculture")
st.markdown("""
This AI-powered application simulates and analyzes live IoT sensor data from aquaculture ponds.
It uses a trained **Random Forest Classifier** to assess water safety status and suggests physical actions to sustain aquatic life.
""")

# Load ML model and scaler helper
@st.cache_resource
def load_ml_components():
    model_path = "water_quality_model.pkl"
    scaler_path = "scaler.pkl"
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)
        return model, scaler
    return None, None

model, scaler = load_ml_components()

# Recommendation logic
def get_recommendations(temp, ph, do, turbidity, conductivity, ammonia, status_code):
    recs = []
    if status_code == 0:
        return ["🟢 **Status: Optimal.** Water parameters are within the safe biological range for aquaculture. Continue standard feeding and monitoring practices."]
        
    if do < 5.0:
        recs.append("🚨 **Low Dissolved Oxygen (DO < 5.0 mg/L):**\n"
                    "- **Emergency Action:** Turn on all aerators (paddlewheels, bubble diffusers) immediately.\n"
                    "- **Feed Control:** Halt feeding. Digestion increases biological oxygen demand (BOD) and fish metabolism, which can lead to mass suffocation.\n"
                    "- **Water Exchange:** Flush the surface water and pump in fresh oxygenated groundwater if available.")
                    
    if ph < 6.5:
        recs.append("⚠️ **Acidic Water (pH < 6.5):**\n"
                    "- **Treatment:** Apply agricultural limestone (calcium carbonate, $CaCO_3$) or dolomite ($CaMg(CO_3)_2$) at a rate of 50-100 kg per acre to increase alkalinity.\n"
                    "- **Quick Fix:** In case of emergency drops (pH < 5.5), apply small, controlled amounts of sodium bicarbonate ($NaHCO_3$) for fast buffering.")
                    
    if ph > 8.5:
        recs.append("⚠️ **Alkaline Water (pH > 8.5):**\n"
                    "- **Risk:** High pH accelerates the conversion of ammonium ($NH_4^+$) into highly toxic gas ammonia ($NH_3$).\n"
                    "- **Treatment:** Conduct a 15-20% water exchange. Apply agricultural gypsum (calcium sulfate, $CaSO_4$) at 100-200 kg per acre to lower pH.\n"
                    "- **Organic Buffer:** Apply molasses (5-10 kg per acre) to stimulate heterotrophic bacteria, which release carbon dioxide ($CO_2$) to naturally buffer high pH.")
                    
    if ammonia > 0.03:
        recs.append("🚨 **Toxic Ammonia (Ammonia > 0.03 mg/L):**\n"
                    "- **Urgent Action:** Stop feeding immediately to block further nitrogen load from feces and uneaten food.\n"
                    "- **Adsorption:** Apply zeolite powder (15-20 kg per acre) to bind and adsorb ammonium ions from the water column.\n"
                    "- **Bioremediation:** Introduce molasses/sugar (C:N ratio optimizer) to promote heterotrophic bacteria that rapidly consume inorganic nitrogen. Perform a 30% water exchange.")
                    
    if temp > 33.0:
        recs.append("⚠️ **Elevated Temperature (Temp > 33.0°C):**\n"
                    "- **Impact:** Warmer water has lower oxygen holding capacity and increases fish respiration.\n"
                    "- **Mitigation:** Increase water depth (cooler water buffers at the bottom), install shade nets over shallow ponds, and run aerators continuously to promote evaporative cooling.")
    elif temp < 20.0:
        recs.append("⚠️ **Low Temperature (Temp < 20.0°C):**\n"
                    "- **Impact:** Fish metabolism slows down. Feed conversion ratio (FCR) drops significantly.\n"
                    "- **Action:** Reduce daily feed allocation by 50% to prevent feed decay and toxic organic buildup on the pond floor.")
                    
    if turbidity > 50.0:
        recs.append("⚠️ **High Turbidity (Turbidity > 50.0 NTU):**\n"
                    "- **If Clay-Induced (Muddy):** Apply agricultural gypsum ($CaSO_4$) at 100 kg/acre or Alum (aluminum sulfate) at 10-15 kg/acre to clump and settle suspended clay particles.\n"
                    "- **If Algae-Induced (Green bloom):** Reduce fertilizing, stop feeding for 24 hours, increase water exchanges, and run paddlewheel aerators to prevent nighttime oxygen crashes.")
                    
    if conductivity > 2500.0:
        recs.append("⚠️ **High Salinity/Conductivity (> 2500 uS/cm):**\n"
                    "- **Action:** Dilute pond salinity by pumping in fresh groundwater. Inspect filtration/evaporation rates.")
    elif conductivity < 300.0:
        recs.append("⚠️ **Low Conductivity/Minerals (< 300 uS/cm):**\n"
                    "- **Action:** Minerals are too low, which causes osmotic stress in fish. Apply common salt (NaCl) or calcium chloride ($CaCl_2$) to replenish minerals and aid fish osmoregulation.")
        
    if not recs:
        recs.append("⚠️ **General Parameter Instability:** Minor parameters are fluctuating. Inspect pond inlets, drainage valves, and filter beds.")
    return recs

# Helper to trigger browser beep sound using Web Audio API
def trigger_acoustic_alarm(status_code):
    if status_code > 0:
        # 880 Hz (A5 pitch) for Critical, 440 Hz (A4 pitch) for Warning
        frequency = 880 if status_code == 2 else 440
        beep_type = "sawtooth" if status_code == 2 else "sine"
        
        beep_js = f"""
        <script>
        (function() {{
            try {{
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                var context = new AudioContext();
                
                // Play sound pattern
                var osc = context.createOscillator();
                var gain = context.createGain();
                
                osc.type = "{beep_type}";
                osc.frequency.setValueAtTime({frequency}, context.currentTime);
                
                osc.connect(gain);
                gain.connect(context.destination);
                osc.start();
                
                if ({status_code} === 2) {{
                    // Critical: Rapid double beep (Buzzer sound)
                    gain.gain.setValueAtTime(0.3, context.currentTime);
                    gain.gain.setValueAtTime(0.01, context.currentTime + 0.15);
                    gain.gain.setValueAtTime(0.3, context.currentTime + 0.25);
                    gain.gain.setValueAtTime(0.01, context.currentTime + 0.40);
                    setTimeout(function() {{ osc.stop(); context.close(); }}, 500);
                }} else {{
                    // Warning: Slow single beep
                    gain.gain.setValueAtTime(0.2, context.currentTime);
                    gain.gain.setValueAtTime(0.01, context.currentTime + 0.30);
                    setTimeout(function() {{ osc.stop(); context.close(); }}, 400);
                }}
            }} catch(e) {{
                console.log("Audio play blocked or unsupported by browser: ", e);
            }}
        }})();
        </script>
        """
        # Inject the invisible iframe to run the JavaScript code
        st.components.v1.html(beep_js, height=0, width=0)

# Sidebar navigation & configuration
st.sidebar.image("https://img.icons8.com/color/150/000000/fish.png", width=100)
st.sidebar.header("Navigation Panel")
mode = st.sidebar.radio("Select Mode", ["Live IoT Telemetry Feed", "Manual Prediction Playground"])

# Cloud configuration settings
st.sidebar.markdown("---")
st.sidebar.header("☁️ Cloud Database Settings")

# Check secrets first
default_fb_url = st.secrets.get("FIREBASE_URL", "https://aquacultureiot-17060-default-rtdb.asia-southeast1.firebasedatabase.app/")
firebase_url = st.sidebar.text_input("Firebase Realtime DB URL:", value=default_fb_url, 
                                     placeholder="https://your-project-default-rtdb.firebaseio.com/")

if firebase_url:
    # Normalize URL (ensure it has a trailing slash)
    if not firebase_url.endswith("/"):
        firebase_url += "/"
    st.sidebar.info("🔗 Connected to Firebase Cloud")
else:
    st.sidebar.info("📁 Connected to Local SQLite Database")

# Check if model trained
if model is None or scaler is None:
    st.sidebar.error("❌ AI Model Not Found!")
    st.info("💡 **Getting Started:** To train the AI model first, run the following commands in your terminal:")
    st.code("python data_simulator.py\npython train_model.py", language="bash")
    st.stop()
else:
    st.sidebar.success("🤖 AI Model Connected")

# Aquaculture Guide Expander
st.sidebar.markdown("---")
with st.sidebar.expander("📚 Fish Health Standard Guide"):
    st.markdown("""
    **Optimal Ranges for Fish Health:**
    * **Temperature:** 24.0 - 30.0 °C
    * **pH Level:** 6.8 - 8.2
    * **Dissolved Oxygen:** > 5.5 mg/L
    * **Turbidity:** < 30.0 NTU
    * **Conductivity:** 500 - 1500 µS/cm
    * **Ammonia:** < 0.02 mg/L
    
    *Values outside these bounds cause biological stress, reduced feeding, or mortality.*
    """)

# --- MODE 1: LIVE IoT FEED ---
if mode == "Live IoT Telemetry Feed":
    st.subheader("📊 Real-Time IoT Pond Telemetry")
    
    auto_refresh = st.sidebar.checkbox("Enable Live Real-Time Updates", value=True)
    refresh_rate = st.sidebar.slider("Refresh Interval (seconds)", min_value=1, max_value=10, value=2)
    
    df_live = pd.DataFrame()
    data_source = ""
    
    # CASE 1: Load from Firebase Cloud
    if firebase_url:
        data_source = "Firebase Cloud Database"
        try:
            # Query the last 50 entries sorted by push-ID keys (lexicographically chronological)
            req_url = f"{firebase_url}sensor_readings.json?orderBy=\"$key\"&limitToLast=50"
            res = requests.get(req_url, timeout=4.0)
            
            if res.status_code == 200:
                raw_data = res.json()
                if raw_data:
                    # Convert dict values to a list of dicts
                    readings = [val for val in raw_data.values()]
                    df_live = pd.DataFrame(readings)
                    # Reverse so latest data point is first
                    df_live = df_live.iloc[::-1].reset_index(drop=True)
                else:
                    st.warning("🔄 Connected to Firebase, but no sensor records found yet. Please turn on your ESP32 node.")
            else:
                st.error(f"Failed to fetch from Firebase: HTTP {res.status_code}")
        except Exception as e:
            st.error(f"Firebase connection error: {e}")
            st.info("⚠️ Falling back to local SQLite database...")
            firebase_url = "" # Reset to force SQLite load below
            
    # CASE 2: Load from Local SQLite (Fallback or default)
    if not firebase_url:
        data_source = "Local SQLite Database (water_quality.db)"
        db_path = "water_quality.db"
        
        if not os.path.exists(db_path):
            st.warning("⚠️ **Waiting for IoT Stream:** No local database found.")
            st.info("💡 **Instructions:** Start your simulator bridge or the physical ESP32 bridge using:")
            st.code("python data_simulator.py --live", language="bash")
            st.stop()
            
        try:
            conn = sqlite3.connect(db_path)
            df_live = pd.read_sql_query("SELECT * FROM sensor_readings ORDER BY id DESC LIMIT 50", conn)
            conn.close()
        except Exception as e:
            st.error(f"Error reading SQLite database: {e}")
            st.stop()
            
        if df_live.empty:
            st.warning("🔄 SQLite database exists but is currently empty. Run `python data_simulator.py --live` to begin broadcasting.")
            time.sleep(2)
            st.rerun()

    # If data is successfully loaded
    if not df_live.empty:
        latest = df_live.iloc[0]
        
        # AI Prediction
        input_data = np.array([[latest['temperature'], latest['ph'], latest['dissolved_oxygen'], 
                                latest['turbidity'], latest['conductivity'], latest['ammonia']]])
        input_scaled = scaler.transform(input_data)
        pred_status = model.predict(input_scaled)[0]
        pred_probs = model.predict_proba(input_scaled)[0]
        
        # Trigger browser acoustic alarm
        trigger_acoustic_alarm(pred_status)
        
        # Display Current status banner
        if pred_status == 0:
            st.success("### 🟢 Water Quality Status: OPTIMAL (Safe for Aquaculture)")
        elif pred_status == 1:
            st.warning("### 🟡 Water Quality Status: WARNING (Biological Stress Detected)")
        else:
            st.error("### 🔴 Water Quality Status: CRITICAL (Lethal Environment!)")
            
        # Display data source indicator
        st.caption(f"📡 Feed Active from: **{data_source}**")
            
        # Metric KPI cards
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("Temperature", f"{latest['temperature']} °C", delta=None)
            st.caption("Ideal: 24 - 30 °C")
        with col2:
            st.metric("pH Level", f"{latest['ph']}", delta=None)
            st.caption("Ideal: 6.8 - 8.2")
        with col3:
            st.metric("Dissolved Oxygen (DO)", f"{latest['dissolved_oxygen']} mg/L", delta=None)
            st.caption("Ideal: > 5.5 mg/L")
        with col4:
            st.metric("Turbidity", f"{latest['turbidity']} NTU", delta=None)
            st.caption("Ideal: < 30 NTU")
        with col5:
            st.metric("Conductivity", f"{int(latest['conductivity'])} µS/cm", delta=None)
            st.caption("Ideal: 500-1500")
        with col6:
            st.metric("Ammonia", f"{latest['ammonia']} mg/L", delta=None)
            st.caption("Ideal: < 0.02 mg/L")
            
        st.write("---")
        
        # Core Dashboard Columns
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            st.markdown("#### 📈 Historical IoT Telemetry Charts")
            # Plot parameters
            chart_df = df_live.iloc[::-1]  # reverse to chronological order
            chart_df.set_index("timestamp", inplace=True)
            
            param_to_plot = st.selectbox("Select Parameter to Plot", 
                                         ["Dissolved_Oxygen", "pH", "Temperature", "Ammonia", "Turbidity", "Conductivity"])
            st.line_chart(chart_df[param_to_plot.lower()])
            
        with col_right:
            st.markdown("#### 🤖 AI Recommendation Engine")
            recs = get_recommendations(
                latest['temperature'], latest['ph'], latest['dissolved_oxygen'], 
                latest['turbidity'], latest['conductivity'], latest['ammonia'], 
                pred_status
            )
            for r in recs:
                st.info(r)
                
            st.markdown("#### AI Confidence Probabilities")
            prob_df = pd.DataFrame({
                "Status": ["Optimal", "Warning", "Critical"],
                "Probability (%)": [round(p * 100, 1) for p in pred_probs]
            })
            st.dataframe(prob_df, hide_index=True)
            
        # Auto-refresh loop
        if auto_refresh:
            time.sleep(refresh_rate)
            st.rerun()

# --- MODE 2: MANUAL PLAYGROUND ---
else:
    st.subheader("🧪 Machine Learning Prediction Playground")
    st.markdown("Adjust the sliders below to simulate custom pond sensor readings and check how the AI model responds.")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        sim_temp = st.slider("Temperature (°C)", min_value=10.0, max_value=45.0, value=26.5, step=0.1)
        sim_ph = st.slider("pH Level", min_value=3.0, max_value=12.0, value=7.4, step=0.1)
    with col_s2:
        sim_do = st.slider("Dissolved Oxygen (mg/L)", min_value=0.2, max_value=15.0, value=6.2, step=0.1)
        sim_turbidity = st.slider("Turbidity (NTU)", min_value=2.0, max_value=120.0, value=20.0, step=0.5)
    with col_s3:
        sim_conductivity = st.slider("Conductivity (µS/cm)", min_value=100.0, max_value=5000.0, value=1100.0, step=10.0)
        sim_ammonia = st.slider("Ammonia (mg/L)", min_value=0.0, max_value=1.0, value=0.012, step=0.001, format="%.3f")
        
    st.write("---")
    
    # Run Prediction
    sim_data = np.array([[sim_temp, sim_ph, sim_do, sim_turbidity, sim_conductivity, sim_ammonia]])
    sim_scaled = scaler.transform(sim_data)
    sim_pred = model.predict(sim_scaled)[0]
    sim_probs = model.predict_proba(sim_scaled)[0]
    
    # Trigger browser acoustic alarm
    trigger_acoustic_alarm(sim_pred)
    
    col_r1, col_r2 = st.columns([1, 1])
    
    with col_r1:
        st.markdown("### AI Classification Output")
        if sim_pred == 0:
            st.success("### 🟢 STATUS: OPTIMAL (Safe)")
        elif sim_pred == 1:
            st.warning("### 🟡 STATUS: WARNING (Stressed)")
        else:
            st.error("### 🔴 STATUS: CRITICAL (Dangerous)")
            
        # Class probabilities bar chart
        prob_data = pd.DataFrame({
            "Probability": sim_probs,
            "Class": ["Optimal", "Warning", "Critical"]
        })
        st.bar_chart(prob_data.set_index("Class"))
        
    with col_r2:
        st.markdown("### Suggested Aquaculture Interventions")
        recs = get_recommendations(sim_temp, sim_ph, sim_do, sim_turbidity, sim_conductivity, sim_ammonia, sim_pred)
        for r in recs:
            st.info(r)
