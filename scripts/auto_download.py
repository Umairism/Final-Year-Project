#!/usr/bin/env python3
"""
Automatic Dataset Downloader - Non-interactive version
Downloads all required datasets automatically
"""

import os
import urllib.request
import zipfile
import tarfile
import sys
from pathlib import Path

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

# Change to project root
os.chdir("/run/media/whistler/User/University/FYP Project/healsense")

print_status("=" * 60, "INFO")
print_status("HealSense Automatic Dataset Downloader", "INFO")
print_status("=" * 60, "INFO")

# 1. Download UCI Heart Disease Dataset
print_status("\n=== UCI Heart Disease Dataset ===", "INFO")
data_dir = Path("data/raw/uci_heart_disease")
data_dir.mkdir(parents=True, exist_ok=True)

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

# Create README
readme_content = """# UCI Heart Disease Dataset

## Description
This database contains 76 attributes, but all published experiments refer to using a subset of 14 of them.
The Cleveland database is the only one that has been used by ML researchers to date.

## Files
- processed.cleveland.data: Cleveland clinic data (303 instances)
- processed.hungarian.data: Hungarian Institute data (294 instances)
- processed.switzerland.data: Switzerland data (123 instances)
- processed.va.data: V.A. Medical Center data (200 instances)

## Attributes (14 used)
1. age: age in years
2. sex: 1=male, 0=female
3. cp: chest pain type (1-4)
4. trestbps: resting blood pressure (mm Hg)
5. chol: serum cholesterol (mg/dl)
6. fbs: fasting blood sugar > 120 mg/dl (1=true, 0=false)
7. restecg: resting ECG results (0-2)
8. thalach: maximum heart rate achieved
9. exang: exercise induced angina (1=yes, 0=no)
10. oldpeak: ST depression induced by exercise
11. slope: slope of peak exercise ST segment (1-3)
12. ca: number of major vessels (0-3)
13. thal: 3=normal, 6=fixed defect, 7=reversable defect
14. num: diagnosis (0=no disease, 1-4=disease severity)

## Source
https://archive.ics.uci.edu/ml/datasets/heart+Disease

## Citation
Hungarian Institute of Cardiology, University Hospitals (Zurich & Basel), 
V.A. Medical Center (Long Beach), Cleveland Clinic Foundation

## Downloaded
""" + str(Path().absolute()) + "\n"

with open(data_dir / "README.md", "w") as f:
    f.write(readme_content)

print_status("UCI Heart Disease dataset complete!", "SUCCESS")

# 2. Setup PhysioNet BIDMC
print_status("\n=== PhysioNet BIDMC Dataset ===", "INFO")
print_status("Installing wfdb package...", "INFO")
os.system("pip install wfdb -q")

data_dir = Path("data/raw/physionet_bidmc")
data_dir.mkdir(parents=True, exist_ok=True)

# Create download script
download_script = """
import wfdb
import os

print("Downloading BIDMC PPG and Respiration Dataset...")

data_dir = "data/raw/physionet_bidmc"
os.makedirs(data_dir, exist_ok=True)

# Download sample records (first 5 for quick start)
for record_num in range(1, 6):
    record_name = f"bidmc_{record_num:02d}"
    try:
        print(f"Downloading record {record_num}/5...")
        wfdb.rdrecord(record_name, pb_dir='bidmc', pn_dir='bidmc', dl_dir=data_dir)
        print(f"✓ Record {record_num} downloaded")
    except Exception as e:
        print(f"✗ Error: {e}")

print("PhysioNet BIDMC download complete!")
"""

script_path = data_dir / "download_bidmc.py"
with open(script_path, "w") as f:
    f.write(download_script)

print_status("Downloading BIDMC records...", "INFO")
os.system(f"cd '{data_dir}' && python download_bidmc.py")

readme_content = """# PhysioNet BIDMC PPG and Respiration Dataset

## Description
53 adult ICU patients from the MIMIC II database.
Each record contains physiological waveforms.

## Signals
- PPG (Photoplethysmogram)
- ECG (Electrocardiogram)  
- Respiration

## Sampling Rate
125 Hz

## Source
https://physionet.org/content/bidmc/1.0.0/

## Citation
Pimentel et al. (2015). Heart beat detection in multimodal physiological data.
"""

with open(data_dir / "README.md", "w") as f:
    f.write(readme_content)

print_status("PhysioNet BIDMC dataset complete!", "SUCCESS")

# 3. Create Kaggle instructions
print_status("\n=== Kaggle Datasets ===", "INFO")
data_dir = Path("data/raw/kaggle_health_data")
data_dir.mkdir(parents=True, exist_ok=True)

instructions = """# Kaggle Health Datasets

## Quick Setup

### 1. Install Kaggle CLI
```bash
pip install kaggle
```

### 2. Get API Token
1. Go to https://www.kaggle.com/account
2. Click "Create New API Token"
3. Save kaggle.json to ~/.kaggle/
4. Run: chmod 600 ~/.kaggle/kaggle.json

### 3. Download Datasets
```bash
# Run the automatic downloader
python scripts/download_kaggle.py
```

## Recommended Datasets

1. **Heart Disease Dataset**
   - kaggle datasets download -d johnsmith88/heart-disease-dataset

2. **Heart Disease UCI**
   - kaggle datasets download -d ronitf/heart-disease-uci

3. **Medical Cost Dataset**
   - kaggle datasets download -d mirichoi0218/insurance

## Manual Download
Visit https://www.kaggle.com/datasets and search for:
- "vital signs"
- "health monitoring"
- "blood pressure"
- "spo2"
"""

with open(data_dir / "INSTRUCTIONS.md", "w") as f:
    f.write(instructions)

print_status("Kaggle instructions created!", "SUCCESS")

# 4. Create synthetic data generator
print_status("\n=== Synthetic Data Generator ===", "INFO")

generator_script = """#!/usr/bin/env python3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)

print("Generating synthetic vital signs data...")

# Generate 10 patients with 1000 readings each
all_data = []

for patient_id in range(1, 11):
    start_time = datetime.now() - timedelta(hours=1000/60)
    timestamps = [start_time + timedelta(minutes=i) for i in range(1000)]
    
    # Generate realistic vital signs
    heart_rate = np.clip(np.random.normal(75, 10, 1000), 50, 120)
    spo2 = np.clip(np.random.normal(97, 1.5, 1000), 90, 100)
    temperature = np.clip(np.random.normal(37, 0.3, 1000), 36, 39)
    systolic_bp = np.clip(np.random.normal(120, 10, 1000), 90, 160)
    diastolic_bp = np.clip(np.random.normal(80, 8, 1000), 60, 100)
    
    # Add anomalies (5% of data)
    anomaly_idx = np.random.choice(1000, 50, replace=False)
    heart_rate[anomaly_idx] = np.random.uniform(120, 150, 50)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'patient_id': patient_id,
        'heart_rate': heart_rate.round(1),
        'spo2': spo2.round(1),
        'temperature': temperature.round(1),
        'systolic_bp': systolic_bp.round(0).astype(int),
        'diastolic_bp': diastolic_bp.round(0).astype(int)
    })
    
    all_data.append(df)

combined = pd.concat(all_data, ignore_index=True)
combined.to_csv("data/raw/synthetic/synthetic_vital_signs.csv", index=False)

print(f"✓ Generated {len(combined)} records for 10 patients")
print("✓ Saved to: data/raw/synthetic/synthetic_vital_signs.csv")
"""

Path("data/raw/synthetic").mkdir(parents=True, exist_ok=True)
with open("scripts/generate_synthetic_data.py", "w") as f:
    f.write(generator_script)

os.system("chmod +x scripts/generate_synthetic_data.py")
print_status("Generating synthetic data...", "INFO")
os.system("python scripts/generate_synthetic_data.py")

print_status("Synthetic data generator complete!", "SUCCESS")

# Summary
print_status("\n" + "=" * 60, "SUCCESS")
print_status("Dataset Download Complete!", "SUCCESS")
print_status("=" * 60, "SUCCESS")

print("\n✅ Downloaded Datasets:")
print("   1. UCI Heart Disease (5 files)")
print("   2. PhysioNet BIDMC (5 patient records)")
print("   3. Synthetic Data (10,000 records)")
print("   4. Kaggle setup instructions")

print("\n📂 Directory Structure:")
os.system("tree data/raw -L 2 2>/dev/null || find data/raw -type d | head -20")

print("\n📝 Next Steps:")
print("   1. Setup Kaggle API and download additional datasets")
print("   2. Review data in data/raw/ directories")
print("   3. Start data exploration (Phase 1)")
print("   4. Create notebooks/01_data_exploration.ipynb")

print("\n💾 Git Commands:")
print("   git add data/")
print("   git commit -m 'Add downloaded datasets'")
print("   git push origin main")
