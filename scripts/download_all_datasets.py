#!/usr/bin/env python3
"""
HealSense Master Dataset Downloader
Downloads all required datasets from multiple sources:
- Kaggle (health datasets)
- UCI Machine Learning Repository (heart disease)
- PhysioNet (physiological signals)
- Generate synthetic data as fallback

Author: HealSense Team
Date: January 2026
"""

import os
import sys
import json
import urllib.request
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List
import subprocess

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


class DatasetDownloader:
    """Main dataset downloader class"""
    
    def __init__(self, base_path: str = None):
        """Initialize downloader with base path"""
        if base_path is None:
            # Use current working directory
            self.base_path = Path.cwd()
        else:
            self.base_path = Path(base_path)
        
        self.data_dir = self.base_path / "data" / "raw"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Track download status
        self.downloaded_datasets = []
        self.failed_datasets = []
        
    def check_dependencies(self) -> bool:
        """Check if required packages are installed"""
        print_header("Checking Dependencies")
        
        dependencies = {
            'requests': 'requests',
            'pandas': 'pandas',
            'numpy': 'numpy'
        }
        
        # Check kaggle separately (without importing to avoid auth error)
        try:
            subprocess.check_output([sys.executable, "-m", "pip", "show", "kaggle"], 
                                    stderr=subprocess.DEVNULL)
            print_success("kaggle is installed")
        except subprocess.CalledProcessError:
            print_warning("kaggle is NOT installed")
            dependencies['kaggle'] = 'kaggle'
        
        missing = []
        for package, import_name in dependencies.items():
            if package == 'kaggle':
                missing.append(package)
                continue
            try:
                __import__(import_name)
                print_success(f"{package} is installed")
            except ImportError:
                print_warning(f"{package} is NOT installed")
                missing.append(package)
        
        if missing:
            print_info(f"Installing missing packages: {', '.join(missing)}")
            for package in missing:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print_success("All dependencies installed!")
        
        return True
    
    def setup_kaggle_api(self) -> bool:
        """Setup Kaggle API credentials"""
        print_header("Setting Up Kaggle API")
        
        kaggle_dir = Path.home() / ".kaggle"
        kaggle_json = kaggle_dir / "kaggle.json"
        
        if kaggle_json.exists():
            print_success("Kaggle API token found")
            return True
        
        print_warning("Kaggle API token not found!")
        print_info("Please follow these steps:")
        print("   1. Go to https://www.kaggle.com/account")
        print("   2. Scroll to 'API' section")
        print("   3. Click 'Create New API Token'")
        print("   4. This will download kaggle.json")
        
        # Try to get credentials from .env file
        env_file = self.base_path / ".env"
        if env_file.exists():
            print_info("Checking .env file for Kaggle credentials...")
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('KAGGLE_USERNAME'):
                        username = line.split('=')[1].strip()
                    if line.startswith('KAGGLE_KEY'):
                        key = line.split('=')[1].strip()
            
            if 'username' in locals() and 'key' in locals():
                # Create kaggle.json
                kaggle_dir.mkdir(exist_ok=True)
                kaggle_config = {"username": username, "key": key}
                with open(kaggle_json, 'w') as f:
                    json.dump(kaggle_config, f)
                os.chmod(kaggle_json, 0o600)
                print_success("Created kaggle.json from .env file")
                return True
        
        # Manual setup
        response = input("\nDo you want to setup Kaggle API now? (y/n): ")
        if response.lower() == 'y':
            username = input("Enter Kaggle username: ")
            key = input("Enter Kaggle API key: ")
            
            kaggle_dir.mkdir(exist_ok=True)
            kaggle_config = {"username": username, "key": key}
            
            with open(kaggle_json, 'w') as f:
                json.dump(kaggle_config, f)
            
            # Set permissions (Unix-like systems)
            if os.name != 'nt':
                os.chmod(kaggle_json, 0o600)
            
            print_success("Kaggle API configured successfully!")
            return True
        else:
            print_warning("Kaggle datasets will be skipped")
            return False
    
    def download_uci_heart_disease(self):
        """Download UCI Heart Disease dataset"""
        print_header("Downloading UCI Heart Disease Dataset")
        
        uci_dir = self.data_dir / "uci_heart_disease"
        uci_dir.mkdir(parents=True, exist_ok=True)
        
        # UCI Heart Disease data files
        base_url = "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/"
        files = [
            "processed.cleveland.data",
            "processed.hungarian.data",
            "processed.switzerland.data",
            "processed.va.data",
            "heart-disease.names"
        ]
        
        for filename in files:
            url = base_url + filename
            filepath = uci_dir / filename
            
            try:
                print_info(f"Downloading {filename}...")
                urllib.request.urlretrieve(url, filepath)
                print_success(f"Downloaded {filename}")
            except Exception as e:
                print_error(f"Failed to download {filename}: {e}")
                self.failed_datasets.append(f"UCI - {filename}")
                continue
        
        # Create README
        readme_content = """# UCI Heart Disease Dataset

Downloaded from: https://archive.ics.uci.edu/ml/datasets/heart+Disease

## Files
- processed.cleveland.data: Cleveland clinic (303 records)
- processed.hungarian.data: Hungarian Institute (294 records)  
- processed.switzerland.data: Switzerland (123 records)
- processed.va.data: V.A. Medical Center (200 records)
- heart-disease.names: Attribute information

## Total: ~920 patient records
"""
        with open(uci_dir / "README.md", "w") as f:
            f.write(readme_content)
        
        print_success("UCI Heart Disease dataset downloaded successfully!")
        self.downloaded_datasets.append("UCI Heart Disease (920 records)")
    
    def download_kaggle_datasets(self):
        """Download health datasets from Kaggle"""
        print_header("Downloading Kaggle Health Datasets")
        
        try:
            import kaggle
        except ImportError:
            print_error("Kaggle package not available. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "kaggle"])
            import kaggle
        
        kaggle_dir = self.data_dir / "kaggle_health_data"
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        
        # List of important Kaggle datasets for vital signs
        datasets = [
            {
                "name": "Human Vital Signs 2024",
                "id": "rabieelkharoua/human-vital-signs-dataset-2024",
                "description": "200K+ records with all vital signs"
            },
            {
                "name": "Body Signals Dataset",
                "id": "kukuroo3/body-signal-of-smoking",
                "description": "55K+ records with BP, blood sugar, cholesterol"
            },
            {
                "name": "CVD Vital Signs",
                "id": "kamilpytlak/personal-key-indicators-of-heart-disease",
                "description": "Heart disease indicators"
            },
            {
                "name": "Heart Disease UCI",
                "id": "ronitf/heart-disease-uci",
                "description": "UCI heart disease data"
            },
            {
                "name": "Medical Cost Dataset",
                "id": "mirichoi0218/insurance",
                "description": "Medical insurance costs"
            }
        ]
        
        for dataset in datasets:
            print_info(f"\nDownloading: {dataset['name']}")
            print(f"   Description: {dataset['description']}")
            print(f"   Dataset ID: {dataset['id']}")
            
            try:
                # Download and unzip
                kaggle.api.dataset_download_files(
                    dataset['id'],
                    path=kaggle_dir,
                    unzip=True
                )
                print_success(f"Downloaded {dataset['name']}")
                self.downloaded_datasets.append(dataset['name'])
            except Exception as e:
                print_error(f"Failed to download {dataset['name']}: {e}")
                self.failed_datasets.append(dataset['name'])
                continue
        
        print_success("Kaggle datasets download complete!")
    
    def download_physionet_bidmc(self):
        """Download PhysioNet BIDMC dataset"""
        print_header("Downloading PhysioNet BIDMC Dataset")
        
        physionet_dir = self.data_dir / "physionet_bidmc"
        physionet_dir.mkdir(parents=True, exist_ok=True)
        
        print_info("PhysioNet BIDMC requires manual download")
        print("This dataset contains PPG, ECG, and respiration signals")
        print_warning("Manual download required due to PhysioNet access policies")
        
        print("\nTo download manually:")
        print("1. Visit: https://physionet.org/content/bidmc/1.0.0/")
        print("2. Click 'Files' tab")
        print("3. Download bidmc-1.0.0.zip")
        print(f"4. Extract to: {physionet_dir}")
        
        # Create download helper script
        download_script = physionet_dir / "download_bidmc.py"
        script_content = """#!/usr/bin/env python3
'''
PhysioNet BIDMC Dataset Downloader
Requires: wfdb package
'''
import wfdb
from pathlib import Path

# Record names for BIDMC dataset
records = [f'bidmc_{i:02d}' for i in range(1, 54)]

download_dir = Path(__file__).parent
download_dir.mkdir(exist_ok=True)

print("Downloading BIDMC records...")
for record in records:
    try:
        wfdb.rdrecord(record, pn_dir='bidmc', dl_dir=str(download_dir))
        print(f"✅ Downloaded {record}")
    except Exception as e:
        print(f"❌ Failed {record}: {e}")

print("\\nDownload complete!")
"""
        with open(download_script, 'w') as f:
            f.write(script_content)
        
        print_info(f"Alternative: Run the script at {download_script}")
        print("   (Requires: pip install wfdb)")
        
        self.failed_datasets.append("PhysioNet BIDMC (Manual download required)")
    
    def generate_synthetic_data(self):
        """Generate synthetic vital signs data"""
        print_header("Generating Synthetic Vital Signs Data")
        
        try:
            import numpy as np
            import pandas as pd
        except ImportError:
            print_error("NumPy and Pandas required for synthetic data generation")
            return
        
        synthetic_dir = self.data_dir / "synthetic"
        synthetic_dir.mkdir(parents=True, exist_ok=True)
        
        print_info("Generating 10,000 synthetic vital sign readings...")
        
        # Set random seed for reproducibility
        np.random.seed(42)
        
        # Generate data for 10 patients, 1000 readings each
        n_patients = 10
        readings_per_patient = 1000
        total_readings = n_patients * readings_per_patient
        
        data = {
            'patient_id': np.repeat(range(1, n_patients + 1), readings_per_patient),
            'timestamp': pd.date_range('2024-01-01', periods=total_readings, freq='1min'),
            'heart_rate': np.random.normal(75, 15, total_readings).clip(50, 150),
            'spo2': np.random.normal(97, 2, total_readings).clip(85, 100),
            'temperature': np.random.normal(37.0, 0.4, total_readings).clip(36.0, 39.5),
            'systolic_bp': np.random.normal(120, 10, total_readings).clip(90, 160),
            'diastolic_bp': np.random.normal(80, 8, total_readings).clip(60, 100),
        }
        
        df = pd.DataFrame(data)
        
        # Add anomalies (15% of data)
        anomaly_indices = np.random.choice(total_readings, size=int(total_readings * 0.15), replace=False)
        
        anomaly_types = []
        for idx in range(total_readings):
            if idx in anomaly_indices:
                anomaly_type = np.random.choice(['low_spo2', 'high_heart_rate', 'fever'], p=[0.6, 0.3, 0.1])
                anomaly_types.append(anomaly_type)
                
                if anomaly_type == 'low_spo2':
                    df.loc[idx, 'spo2'] = np.random.uniform(85, 92)
                elif anomaly_type == 'high_heart_rate':
                    df.loc[idx, 'heart_rate'] = np.random.uniform(120, 150)
                elif anomaly_type == 'fever':
                    df.loc[idx, 'temperature'] = np.random.uniform(38.0, 39.5)
            else:
                anomaly_types.append('normal')
        
        df['alert_type'] = anomaly_types
        
        # Save to CSV
        output_file = synthetic_dir / "synthetic_vital_signs.csv"
        df.to_csv(output_file, index=False)
        
        print_success(f"Generated {total_readings} synthetic readings")
        print_info(f"Saved to: {output_file}")
        print(f"\n   📊 Normal: {(df['alert_type'] == 'normal').sum()} ({(df['alert_type'] == 'normal').sum()/total_readings*100:.1f}%)")
        print(f"   ⚠️  Anomalies: {(df['alert_type'] != 'normal').sum()} ({(df['alert_type'] != 'normal').sum()/total_readings*100:.1f}%)")
        
        self.downloaded_datasets.append("Synthetic Vital Signs (10,000 records)")
    
    def create_summary_report(self):
        """Create a summary report of all downloads"""
        print_header("Download Summary Report")
        
        print(f"{Colors.BOLD}Successfully Downloaded:{Colors.ENDC}")
        for dataset in self.downloaded_datasets:
            print(f"   {Colors.OKGREEN}✅{Colors.ENDC} {dataset}")
        
        if self.failed_datasets:
            print(f"\n{Colors.BOLD}Failed/Skipped:{Colors.ENDC}")
            for dataset in self.failed_datasets:
                print(f"   {Colors.WARNING}⚠️{Colors.ENDC} {dataset}")
        
        # Count total files
        total_files = sum(1 for _ in self.data_dir.rglob('*') if _.is_file())
        total_size = sum(f.stat().st_size for f in self.data_dir.rglob('*') if f.is_file())
        
        print(f"\n{Colors.BOLD}Statistics:{Colors.ENDC}")
        print(f"   📁 Total Files: {total_files}")
        print(f"   💾 Total Size: {total_size / (1024*1024):.2f} MB")
        print(f"   📍 Location: {self.data_dir}")
        
        # Create markdown report
        report_file = self.base_path / "DOWNLOAD_REPORT.md"
        with open(report_file, 'w') as f:
            f.write("# HealSense Dataset Download Report\n\n")
            f.write(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Successfully Downloaded\n")
            for dataset in self.downloaded_datasets:
                f.write(f"- ✅ {dataset}\n")
            
            if self.failed_datasets:
                f.write("\n## Failed/Skipped\n")
                for dataset in self.failed_datasets:
                    f.write(f"- ⚠️ {dataset}\n")
            
            f.write(f"\n## Statistics\n")
            f.write(f"- Total Files: {total_files}\n")
            f.write(f"- Total Size: {total_size / (1024*1024):.2f} MB\n")
            f.write(f"- Location: `{self.data_dir}`\n")
        
        print_success(f"Report saved to: {report_file}")
    
    def run(self, skip_kaggle=False, skip_physionet=False):
        """Run the complete download process"""
        print_header("HealSense Master Dataset Downloader")
        print(f"Base Path: {self.base_path}")
        print(f"Data Directory: {self.data_dir}")
        
        # Step 1: Check dependencies
        if not self.check_dependencies():
            print_error("Dependency check failed!")
            return
        
        # Step 2: Setup Kaggle API (if needed)
        kaggle_setup = False
        if not skip_kaggle:
            kaggle_setup = self.setup_kaggle_api()
        
        # Step 3: Download UCI Heart Disease
        try:
            self.download_uci_heart_disease()
        except Exception as e:
            print_error(f"Error downloading UCI dataset: {e}")
        
        # Step 4: Download Kaggle datasets
        if kaggle_setup and not skip_kaggle:
            try:
                self.download_kaggle_datasets()
            except Exception as e:
                print_error(f"Error downloading Kaggle datasets: {e}")
        
        # Step 5: PhysioNet instructions
        if not skip_physionet:
            try:
                self.download_physionet_bidmc()
            except Exception as e:
                print_error(f"Error with PhysioNet setup: {e}")
        
        # Step 6: Generate synthetic data
        try:
            self.generate_synthetic_data()
        except Exception as e:
            print_error(f"Error generating synthetic data: {e}")
        
        # Step 7: Create summary report
        self.create_summary_report()
        
        print_header("Download Process Complete!")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HealSense Dataset Downloader')
    parser.add_argument('--path', type=str, help='Base path for the project', default=None)
    parser.add_argument('--skip-kaggle', action='store_true', help='Skip Kaggle datasets')
    parser.add_argument('--skip-physionet', action='store_true', help='Skip PhysioNet setup')
    
    args = parser.parse_args()
    
    # Create downloader instance
    downloader = DatasetDownloader(base_path=args.path)
    
    # Run the download process
    downloader.run(
        skip_kaggle=args.skip_kaggle,
        skip_physionet=args.skip_physionet
    )


if __name__ == "__main__":
    main()
