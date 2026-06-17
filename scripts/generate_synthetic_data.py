#!/usr/bin/env python3
"""
Synthetic Health Data Generator
Generates realistic vital signs data for HealSense model training
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def evaluate_health_status(row):
    """
    Classify health status based on clinical thresholds
    Returns: 'normal', 'warning', or 'critical'
    """
    # Critical thresholds (immediate danger)
    if (row['heart_rate'] < 40 or row['heart_rate'] > 130 or
        row['spo2'] < 90 or
        row['temperature'] > 40 or
        row['systolic_bp'] < 80 or row['systolic_bp'] > 180 or
        row['diastolic_bp'] < 50 or row['diastolic_bp'] > 120):
        return 'critical'
    
    # Warning thresholds (concerning but not immediately dangerous)
    if (row['heart_rate'] < 50 or row['heart_rate'] > 120 or
        row['spo2'] < 92 or
        row['temperature'] > 38.0 or
        row['systolic_bp'] < 90 or row['systolic_bp'] > 140 or
        row['diastolic_bp'] < 60 or row['diastolic_bp'] > 90):
        return 'warning'
    
    return 'normal'

def generate_vital_signs(num_samples=1000, patient_id=1):
    """Generate synthetic vital signs with realistic patterns"""
    
    np.random.seed(42 + patient_id)
    
    # Generate timestamps (1 reading per minute)
    start_time = datetime.now() - timedelta(hours=num_samples/60)
    timestamps = [start_time + timedelta(minutes=i) for i in range(num_samples)]
    
    # Heart Rate: Normal range with natural variations
    heart_rate = np.random.normal(75, 10, num_samples)
    heart_rate = np.clip(heart_rate, 45, 110)
    
    # Add warning-level episodes (5%)
    warning_hr = np.random.choice(num_samples, size=int(num_samples*0.05), replace=False)
    heart_rate[warning_hr] = np.random.uniform(120, 130, len(warning_hr))
    
    # Add critical episodes (2%)
    critical_hr = np.random.choice(num_samples, size=int(num_samples*0.02), replace=False)
    heart_rate[critical_hr] = np.random.uniform(135, 150, len(critical_hr))
    
    # SpO2: Normally high (95-100%)
    spo2 = np.random.normal(97.5, 1.2, num_samples)
    spo2 = np.clip(spo2, 88, 100)
    
    # Add warning SpO2 (3%)
    warning_spo2 = np.random.choice(num_samples, size=int(num_samples*0.03), replace=False)
    spo2[warning_spo2] = np.random.uniform(90, 92, len(warning_spo2))
    
    # Add critical SpO2 (1.5%)
    critical_spo2 = np.random.choice(num_samples, size=int(num_samples*0.015), replace=False)
    spo2[critical_spo2] = np.random.uniform(85, 89, len(critical_spo2))
    
    # Temperature: Stable with occasional fever
    temperature = np.random.normal(36.8, 0.3, num_samples)
    temperature = np.clip(temperature, 36, 37.5)
    
    # Add warning fever (2%)
    warning_temp = np.random.choice(num_samples, size=int(num_samples*0.02), replace=False)
    temperature[warning_temp] = np.random.uniform(38.1, 39.5, len(warning_temp))
    
    # Add critical fever (0.5%)
    critical_temp = np.random.choice(num_samples, size=int(num_samples*0.005), replace=False)
    temperature[critical_temp] = np.random.uniform(40, 41, len(critical_temp))
    
    # Blood Pressure: Systolic (normal ~120)
    systolic = np.random.normal(118, 8, num_samples)
    systolic = np.clip(systolic, 85, 135)
    
    # Add warning BP (4%)
    warning_sys = np.random.choice(num_samples, size=int(num_samples*0.04), replace=False)
    systolic[warning_sys] = np.random.uniform(145, 170, len(warning_sys))
    
    # Add critical BP (1%)
    critical_sys = np.random.choice(num_samples, size=int(num_samples*0.01), replace=False)
    systolic[critical_sys] = np.random.uniform(185, 200, len(critical_sys))
    
    # Diastolic (normal ~80)
    diastolic = np.random.normal(78, 6, num_samples)
    diastolic = np.clip(diastolic, 55, 85)
    
    # Add warning diastolic (3%)
    warning_dia = np.random.choice(num_samples, size=int(num_samples*0.03), replace=False)
    diastolic[warning_dia] = np.random.uniform(95, 110, len(warning_dia))
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': timestamps,
        'patient_id': patient_id,
        'heart_rate': heart_rate.round(1),
        'spo2': spo2.round(1),
        'temperature': temperature.round(2),
        'systolic_bp': systolic.round(0).astype(int),
        'diastolic_bp': diastolic.round(0).astype(int),
    })
    
    # Apply clinical classification
    data['status'] = data.apply(evaluate_health_status, axis=1)
    
    return data

if __name__ == "__main__":
    print("🏥 HealSense: Generating synthetic vital signs dataset...\n")
    
    # Generate data for 10 patients
    all_data = []
    for patient_id in range(1, 11):
        print(f"   Patient {patient_id:02d}/10...", end=" ")
        patient_data = generate_vital_signs(num_samples=1000, patient_id=patient_id)
        all_data.append(patient_data)
        print("✓")
    
    # Combine all data
    combined_data = pd.concat(all_data, ignore_index=True)
    
    # Save to CSV
    import os
    output_dir = "data/raw/synthetic"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/synthetic_vital_signs.csv"
    combined_data.to_csv(output_file, index=False)
    
    print(f"\n✓ Dataset saved: {output_file}")
    print(f"✓ Total records: {len(combined_data):,}")
    print(f"✓ Patients: {len(all_data)}")
    print(f"✓ Duration per patient: ~{1000/60:.1f} hours")
    
    # Class distribution
    print("\n📊 Health Status Distribution:")
    status_counts = combined_data['status'].value_counts()
    for status, count in status_counts.items():
        percentage = (count / len(combined_data)) * 100
        print(f"   {status.capitalize():10s}: {count:5d} ({percentage:5.2f}%)")
    
    # Statistics
    print("\n📈 Vital Signs Statistics:")
    stats = combined_data[['heart_rate', 'spo2', 'temperature', 'systolic_bp', 'diastolic_bp']].describe()
    print(stats.round(2).to_string())
    
    print("\n✅ Dataset generation complete!")
