import sys
import os
import asyncio
from datetime import datetime

# Setup path so we can import api modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.services.prediction_service import prediction_service

def run_test():
    print("Testing PredictionService Initialization...")
    success = prediction_service.load_artifacts()
    if not success:
        print("FAIL: Could not load artifacts.")
        return
        
    print("SUCCESS: Artifacts loaded.")
    
    print("\nTesting Inference...")
    vitals = []
    # Create 60 mock readings to pass sequence_length=60
    for i in range(60):
        vitals.append({
            "heart_rate": 80.0 + (i % 5),
            "spo2": 98.0,
            "temperature": 37.0,
            "systolic_bp": 120.0,
            "diastolic_bp": 80.0
        })
        
    prediction = prediction_service.predict_risk(vitals)
    if prediction:
        print("SUCCESS: Prediction generated!")
        print(f"Predicted Class: {prediction['predicted_class']}")
        print(f"Confidence: {prediction['probability']:.2f}")
        print(f"Model Version: {prediction['model_version']}")
    else:
        print("FAIL: Prediction returned None.")

if __name__ == "__main__":
    run_test()
