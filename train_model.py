import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

def train_water_quality_model(data_path="historical_water_data.csv", model_path="water_quality_model.pkl", scaler_path="scaler.pkl"):
    # 1. Load the dataset
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found. Running data generator first...")
        from data_simulator import generate_historical_dataset
        generate_historical_dataset(filepath=data_path, num_records=5000)
        
    df = pd.read_csv(data_path)
    
    # Define features and target variable
    features = ["Temperature", "pH", "Dissolved_Oxygen", "Turbidity", "Conductivity", "Ammonia"]
    X = df[features]
    y = df["Status"]
    
    # 2. Split dataset
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 3. Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 4. Train Random Forest Classifier
    print("Training Machine Learning Model (Random Forest)...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train_scaled, y_train)
    
    # 5. Evaluate Model
    y_pred = clf.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    class_report = classification_report(y_test, y_pred, target_names=["Optimal", "Warning", "Critical"])
    
    print("\n--- Model Evaluation Results ---")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print("\nConfusion Matrix:")
    print(conf_matrix)
    print("\nClassification Report:")
    print(class_report)
    
    # 6. Save Model and Scaler
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
    with open(scaler_path, "wb") as f:
        pickle.dump(scaler, f)
        
    print(f"\nModel saved to: {model_path}")
    print(f"Scaler saved to: {scaler_path}")
    
if __name__ == "__main__":
    train_water_quality_model()
