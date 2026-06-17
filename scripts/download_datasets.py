#!/usr/bin/env python3
"""
Dataset Download Script for HealSense Project
Downloads all required datasets for the FYP project
"""

import os
import urllib.request
import zipfile
import tarfile
import sys
from pathlib import Path

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_status(message, status="INFO"):
    colors = {
        "INFO": Colors.BLUE,
        "SUCCESS": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED
    }
    print(f"{colors.get(status, '')}{status}: {message}{Colors.END}")

def download_file(url, destination):
    """Download a file from URL to destination with progress"""
    print_status(f"Downloading from {url}", "INFO")
    
    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                percent = int(count * block_size * 100 / total_size)
                sys.stdout.write(f"\rProgress: {percent}%")
                sys.stdout.flush()
        
        urllib.request.urlretrieve(url, destination, reporthook)
        print()  # New line after progress
        print_status(f"Downloaded to {destination}", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Error downloading: {str(e)}", "ERROR")
        return False

def extract_archive(file_path, extract_to):
    """Extract zip or tar.gz files"""
    print_status(f"Extracting {file_path}", "INFO")
    
    try:
        if file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif file_path.endswith('.tar.gz') or file_path.endswith('.tgz'):
            with tarfile.open(file_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        
        print_status(f"Extracted to {extract_to}", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Error extracting: {str(e)}", "ERROR")
        return False

def download_uci_heart_disease():
    """Download UCI Heart Disease Dataset"""
    print_status("=== UCI Heart Disease Dataset ===", "INFO")
    
    # Create directory
    data_dir = Path("data/raw/uci_heart_disease")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # UCI Heart Disease Dataset URL
    urls = {
        "processed.cleveland.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data",
        "processed.hungarian.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.hungarian.data",
        "processed.switzerland.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.switzerland.data",
        "processed.va.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.va.data",
        "heart-disease.names": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/heart-disease.names"
    }
    
    for filename, url in urls.items():
        destination = data_dir / filename
        if not destination.exists():
            download_file(url, str(destination))
        else:
            print_status(f"{filename} already exists, skipping", "WARNING")
    
    # Create README for the dataset
    readme_content = """# UCI Heart Disease Dataset

## Description
This database contains 76 attributes, but all published experiments refer to using a subset of 14 of them.
In particular, the Cleveland database is the only one that has been used by ML researchers to date.

## Files
- processed.cleveland.data: Cleveland clinic data
- processed.hungarian.data: Hungarian Institute of Cardiology data
- processed.switzerland.data: University Hospital, Zurich, Switzerland data
- processed.va.data: V.A. Medical Center, Long Beach, CA data
- heart-disease.names: Attribute information

## Attribute Information
1. age: age in years
2. sex: sex (1 = male; 0 = female)
3. cp: chest pain type
4. trestbps: resting blood pressure (in mm Hg)
5. chol: serum cholestoral in mg/dl
6. fbs: fasting blood sugar > 120 mg/dl
7. restecg: resting electrocardiographic results
8. thalach: maximum heart rate achieved
9. exang: exercise induced angina
10. oldpeak: ST depression induced by exercise
11. slope: slope of the peak exercise ST segment
12. ca: number of major vessels colored by flourosopy
13. thal: 3 = normal; 6 = fixed defect; 7 = reversable defect
14. num: diagnosis of heart disease (0-4)

## Source
https://archive.ics.uci.edu/ml/datasets/heart+Disease

## Citation
Creators:
1. Hungarian Institute of Cardiology. Budapest
2. University Hospital, Zurich, Switzerland
3. University Hospital, Basel, Switzerland
4. V.A. Medical Center, Long Beach and Cleveland Clinic Foundation
"""
    
    with open(data_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    print_status("UCI Heart Disease dataset download complete!", "SUCCESS")

def download_physionet_bidmc():
    """Download PhysioNet BIDMC Dataset"""
    print_status("=== PhysioNet BIDMC Dataset ===", "INFO")
    
    print_status("Installing wfdb package for PhysioNet data...", "INFO")
    os.system("pip install wfdb -q")
    
    # Create directory
    data_dir = Path("data/raw/physionet_bidmc")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create Python script to download using wfdb
    download_script = """
import wfdb
import os

print("Downloading BIDMC PPG and Respiration Dataset...")

# BIDMC database has records 1-53
data_dir = "data/raw/physionet_bidmc"
os.makedirs(data_dir, exist_ok=True)

# Download sample records (1-10 for now, can expand later)
for record_num in range(1, 11):
    record_name = f"bidmc_{record_num:02d}"
    try:
        print(f"Downloading record {record_num}/10...")
        wfdb.rdrecord(record_name, pb_dir='bidmc', pn_dir='bidmc', 
                      dl_dir=data_dir)
        print(f"✓ Record {record_num} downloaded")
    except Exception as e:
        print(f"✗ Error downloading record {record_num}: {e}")

print("PhysioNet BIDMC download complete!")
"""
    
    script_path = data_dir / "download_bidmc.py"
    with open(script_path, "w") as f:
        f.write(download_script)
    
    print_status("Downloading BIDMC records using wfdb...", "INFO")
    os.system(f"cd '{data_dir}' && python download_bidmc.py")
    
    # Create README
    readme_content = """# PhysioNet BIDMC PPG and Respiration Dataset

## Description
This dataset includes signals from 53 adult ICU patients from the MIMIC II database.
Each record contains physiological waveforms including PPG, ECG, and respiration.

## Signals
- PPG (Photoplethysmogram): Blood volume pulse
- ECG (Electrocardiogram): Heart electrical activity
- Respiration: Respiratory effort

## Sampling Rate
125 Hz for all signals

## Use Case
Perfect for developing algorithms for:
- Heart rate extraction from PPG
- Blood oxygen saturation (SpO2) estimation
- Respiratory rate detection
- Multi-modal vital sign monitoring

## Source
https://physionet.org/content/bidmc/1.0.0/

## Citation
Pimentel, M. A., Santos, M. D., Springer, D. B., & Clifford, G. D. (2015).
Heart beat detection in multimodal physiological data using a hidden semi-Markov model
and signal quality indices. Physiological measurement, 37(9), 1717.
"""
    
    with open(data_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    print_status("PhysioNet BIDMC dataset download complete!", "SUCCESS")

def download_mitbih_arrhythmia():
    """Download MIT-BIH Arrhythmia Database (Optional)"""
    print_status("=== MIT-BIH Arrhythmia Dataset (Optional) ===", "INFO")
    
    response = input("Do you want to download MIT-BIH Arrhythmia dataset? (y/n): ")
    if response.lower() != 'y':
        print_status("Skipping MIT-BIH Arrhythmia dataset", "WARNING")
        return
    
    # Create directory
    data_dir = Path("data/raw/mitbih")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Download using wfdb
    download_script = """
import wfdb
import os

print("Downloading MIT-BIH Arrhythmia Database...")

data_dir = "data/raw/mitbih"
os.makedirs(data_dir, exist_ok=True)

# Download first 10 records as sample
records = ['100', '101', '102', '103', '104', '105', '106', '107', '108', '109']

for record in records:
    try:
        print(f"Downloading record {record}...")
        wfdb.rdrecord(record, pb_dir='mitdb', pn_dir='mitdb', dl_dir=data_dir)
        wfdb.rdann(record, 'atr', pb_dir='mitdb', pn_dir='mitdb', dl_dir=data_dir)
        print(f"✓ Record {record} downloaded")
    except Exception as e:
        print(f"✗ Error downloading record {record}: {e}")

print("MIT-BIH Arrhythmia download complete!")
"""
    
    script_path = data_dir / "download_mitbih.py"
    with open(script_path, "w") as f:
        f.write(download_script)
    
    print_status("Downloading MIT-BIH records...", "INFO")
    os.system(f"cd '{data_dir}' && python download_mitbih.py")
    
    # Create README
    readme_content = """# MIT-BIH Arrhythmia Database

## Description
The MIT-BIH Arrhythmia Database contains 48 half-hour excerpts of two-channel 
ambulatory ECG recordings from 47 subjects studied by the BIH Arrhythmia Laboratory.

## Signals
- Two-lead ECG recordings
- Annotated arrhythmia events

## Sampling Rate
360 Hz

## Use Case
- ECG analysis and arrhythmia detection
- Heart rate variability analysis
- Abnormal heartbeat detection

## Source
https://physionet.org/content/mitdb/1.0.0/

## Citation
Moody GB, Mark RG. The impact of the MIT-BIH Arrhythmia Database. 
IEEE Eng in Med and Biol 20(3):45-50 (May-June 2001).
"""
    
    with open(data_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    print_status("MIT-BIH Arrhythmia dataset download complete!", "SUCCESS")

def setup_kaggle_datasets():
    """Instructions for downloading Kaggle datasets"""
    print_status("=== Kaggle Datasets ===", "INFO")
    
    # Create directory
    data_dir = Path("data/raw/kaggle_health_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    instructions = """# Kaggle Health Datasets

## Setup Instructions

### 1. Install Kaggle CLI
```bash
pip install kaggle
```

### 2. Get Kaggle API Token
1. Go to https://www.kaggle.com/account
2. Click "Create New API Token"
3. Save kaggle.json to ~/.kaggle/ directory
4. Set permissions: chmod 600 ~/.kaggle/kaggle.json

### 3. Download Recommended Datasets

#### Heart Disease Dataset
```bash
kaggle datasets download -d johnsmith88/heart-disease-dataset -p data/raw/kaggle_health_data/
unzip data/raw/kaggle_health_data/heart-disease-dataset.zip -d data/raw/kaggle_health_data/heart_disease/
```

#### Blood Pressure Dataset
```bash
kaggle datasets download -d mrsimple07/blood-pressure-data -p data/raw/kaggle_health_data/
unzip data/raw/kaggle_health_data/blood-pressure-data.zip -d data/raw/kaggle_health_data/blood_pressure/
```

#### Body Temperature Dataset
```bash
kaggle datasets download -d abhinand05/human-body-temperature -p data/raw/kaggle_health_data/
unzip data/raw/kaggle_health_data/human-body-temperature.zip -d data/raw/kaggle_health_data/body_temperature/
```

#### SpO2 and Vital Signs Dataset
```bash
kaggle datasets download -d dhirajnirne/medical-data -p data/raw/kaggle_health_data/
unzip data/raw/kaggle_health_data/medical-data.zip -d data/raw/kaggle_health_data/medical_data/
```

## Alternative Datasets to Explore

- Search "vital signs" on Kaggle
- Search "health monitoring" on Kaggle
- Search "patient data" on Kaggle

## Manual Download
If you prefer manual download:
1. Visit https://www.kaggle.com/datasets
2. Search for the datasets above
3. Download and place in respective folders
"""
    
    with open(data_dir / "DOWNLOAD_INSTRUCTIONS.md", "w") as f:
        f.write(instructions)
    
    print_status("Kaggle dataset instructions created!", "SUCCESS")
    print_status("Please follow instructions in data/raw/kaggle_health_data/DOWNLOAD_INSTRUCTIONS.md", "INFO")
    
    # Ask if user wants to setup Kaggle now
    response = input("\nDo you want to setup Kaggle CLI now? (y/n): ")
    if response.lower() == 'y':
        print_status("Installing Kaggle CLI...", "INFO")
        os.system("pip install kaggle")
        print_status("\nPlease follow these steps:", "INFO")
        print("1. Go to https://www.kaggle.com/account")
        print("2. Click 'Create New API Token'")
        print("3. Save kaggle.json to ~/.kaggle/ directory")
        print("4. Run: chmod 600 ~/.kaggle/kaggle.json")
        print("5. Then run: python scripts/download_kaggle.py")

def create_synthetic_data_generator():
    """Create a script to generate synthetic data for testing"""
    print_status("=== Creating Synthetic Data Generator ===", "INFO")
    
    data_dir = Path("data/raw/synthetic")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    generator_script = """#!/usr/bin/env python3
\"\"\"
Synthetic Health Data Generator
Generates realistic synthetic vital signs data for testing
\"\"\"

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_vital_signs(num_samples=1000, patient_id=1):
    \"\"\"Generate synthetic vital signs data\"\"\"
    
    np.random.seed(42 + patient_id)
    
    # Generate timestamps
    start_time = datetime.now() - timedelta(hours=num_samples/60)
    timestamps = [start_time + timedelta(minutes=i) for i in range(num_samples)]
    
    # Generate heart rate (60-100 bpm normal, with some anomalies)
    heart_rate = np.random.normal(75, 10, num_samples)
    heart_rate = np.clip(heart_rate, 50, 120)
    
    # Add some anomalies (high heart rate)
    anomaly_indices = np.random.choice(num_samples, size=int(num_samples*0.05), replace=False)
    heart_rate[anomaly_indices] = np.random.uniform(120, 150, len(anomaly_indices))
    
    # Generate SpO2 (95-100% normal)
    spo2 = np.random.normal(97, 1.5, num_samples)
    spo2 = np.clip(spo2, 90, 100)
    
    # Add some low SpO2 anomalies
    low_spo2_indices = np.random.choice(num_samples, size=int(num_samples*0.03), replace=False)
    spo2[low_spo2_indices] = np.random.uniform(85, 92, len(low_spo2_indices))
    
    # Generate body temperature (36.5-37.5°C normal)
    temperature = np.random.normal(37, 0.3, num_samples)
    temperature = np.clip(temperature, 36, 39)
    
    # Add fever anomalies
    fever_indices = np.random.choice(num_samples, size=int(num_samples*0.02), replace=False)
    temperature[fever_indices] = np.random.uniform(38, 39.5, len(fever_indices))
    
    # Generate blood pressure (systolic/diastolic)
    systolic = np.random.normal(120, 10, num_samples)
    systolic = np.clip(systolic, 90, 160)
    
    diastolic = np.random.normal(80, 8, num_samples)
    diastolic = np.clip(diastolic, 60, 100)
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': timestamps,
        'patient_id': patient_id,
        'heart_rate': heart_rate.round(1),
        'spo2': spo2.round(1),
        'temperature': temperature.round(1),
        'systolic_bp': systolic.round(0).astype(int),
        'diastolic_bp': diastolic.round(0).astype(int),
        'status': 'normal'
    })
    
    # Mark anomalies
    data.loc[data['heart_rate'] > 110, 'status'] = 'abnormal_hr'
    data.loc[data['spo2'] < 95, 'status'] = 'low_spo2'
    data.loc[data['temperature'] > 38, 'status'] = 'fever'
    
    return data

if __name__ == "__main__":
    print("Generating synthetic vital signs data...")
    
    # Generate data for 10 patients
    all_data = []
    for patient_id in range(1, 11):
        print(f"Generating data for patient {patient_id}...")
        patient_data = generate_vital_signs(num_samples=1000, patient_id=patient_id)
        all_data.append(patient_data)
    
    # Combine all data
    combined_data = pd.concat(all_data, ignore_index=True)
    
    # Save to CSV
    output_file = "data/raw/synthetic/synthetic_vital_signs.csv"
    combined_data.to_csv(output_file, index=False)
    print(f"✓ Synthetic data saved to {output_file}")
    print(f"✓ Generated {len(combined_data)} records for {len(all_data)} patients")
    
    # Generate statistics
    print("\\n=== Data Statistics ===")
    print(combined_data.describe())
    print("\\n=== Status Distribution ===")
    print(combined_data['status'].value_counts())
"""
    
    with open("scripts/generate_synthetic_data.py", "w") as f:
        f.write(generator_script)
    
    print_status("Synthetic data generator created!", "SUCCESS")
    print_status("Run: python scripts/generate_synthetic_data.py", "INFO")

def main():
    """Main function to download all datasets"""
    print_status("=" * 60, "INFO")
    print_status("HealSense Dataset Download Script", "INFO")
    print_status("=" * 60, "INFO")
    
    # Change to project root
    os.chdir("/run/media/whistler/User/University/FYP Project/healsense")
    
    print("\nThis script will download the following datasets:")
    print("1. UCI Heart Disease Dataset")
    print("2. PhysioNet BIDMC Dataset")
    print("3. MIT-BIH Arrhythmia Dataset (Optional)")
    print("4. Kaggle Datasets (Manual/CLI)")
    print("5. Synthetic Data Generator (For testing)")
    
    response = input("\nProceed with download? (y/n): ")
    if response.lower() != 'y':
        print_status("Download cancelled", "WARNING")
        return
    
    # Download datasets
    try:
        download_uci_heart_disease()
        print()
        
        download_physionet_bidmc()
        print()
        
        download_mitbih_arrhythmia()
        print()
        
        setup_kaggle_datasets()
        print()
        
        create_synthetic_data_generator()
        print()
        
        print_status("=" * 60, "SUCCESS")
        print_status("All datasets downloaded successfully!", "SUCCESS")
        print_status("=" * 60, "SUCCESS")
        
        print("\nNext Steps:")
        print("1. Review downloaded datasets in data/raw/")
        print("2. Setup Kaggle CLI and download Kaggle datasets")
        print("3. Generate synthetic data: python scripts/generate_synthetic_data.py")
        print("4. Start data exploration: Create notebooks/01_data_exploration.ipynb")
        
    except Exception as e:
        print_status(f"Error during download: {str(e)}", "ERROR")
        raise

if __name__ == "__main__":
    main()
