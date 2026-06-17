#!/usr/bin/env python3
"""
Kaggle Dataset Downloader for HealSense Project
Automatically downloads health-related datasets from Kaggle
"""

import os
import sys
from pathlib import Path

def check_kaggle_setup():
    """Check if Kaggle API is properly configured"""
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_json = kaggle_dir / "kaggle.json"
    
    if not kaggle_json.exists():
        print("❌ Kaggle API token not found!")
        print("\nPlease follow these steps:")
        print("1. Go to https://www.kaggle.com/account")
        print("2. Scroll to 'API' section")
        print("3. Click 'Create New API Token'")
        print("4. Save kaggle.json to ~/.kaggle/")
        print("5. Run: chmod 600 ~/.kaggle/kaggle.json")
        return False
    
    print("✅ Kaggle API token found")
    return True

def download_kaggle_datasets():
    """Download health datasets from Kaggle"""
    
    # Ensure we're in the right directory
    os.chdir("/run/media/whistler/User/University/FYP Project/healsense")
    
    data_dir = Path("data/raw/kaggle_health_data")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    datasets = [
        {
            "name": "Heart Disease Dataset",
            "id": "johnsmith88/heart-disease-dataset",
            "folder": "heart_disease"
        },
        {
            "name": "Heart Disease UCI",
            "id": "ronitf/heart-disease-uci",
            "folder": "heart_disease_uci"
        },
        {
            "name": "Medical Cost Personal",
            "id": "mirichoi0218/insurance",
            "folder": "medical_cost"
        }
    ]
    
    print("=" * 60)
    print("Downloading Kaggle Health Datasets")
    print("=" * 60)
    
    for dataset in datasets:
        print(f"\n📦 Downloading: {dataset['name']}")
        print(f"   Dataset ID: {dataset['id']}")
        
        # Download dataset
        download_path = data_dir / dataset['folder']
        download_path.mkdir(parents=True, exist_ok=True)
        
        cmd = f"kaggle datasets download -d {dataset['id']} -p {data_dir} --unzip"
        print(f"   Running: {cmd}")
        
        result = os.system(cmd)
        
        if result == 0:
            print(f"   ✅ Successfully downloaded {dataset['name']}")
            
            # Move files to specific folder if needed
            # This helps organize datasets better
            
        else:
            print(f"   ❌ Failed to download {dataset['name']}")
    
    print("\n" + "=" * 60)
    print("Kaggle dataset download complete!")
    print("=" * 60)
    
    # List downloaded files
    print("\n📂 Downloaded datasets:")
    for item in data_dir.iterdir():
        if item.is_file():
            size_mb = item.stat().st_size / (1024 * 1024)
            print(f"   - {item.name} ({size_mb:.2f} MB)")
        elif item.is_dir():
            file_count = len(list(item.glob("*")))
            print(f"   - {item.name}/ ({file_count} files)")

def search_kaggle_datasets(query="health vital signs"):
    """Search for additional datasets on Kaggle"""
    print(f"\n🔍 Searching Kaggle for: {query}")
    os.system(f"kaggle datasets list -s '{query}'")

def main():
    print("=" * 60)
    print("HealSense Kaggle Dataset Downloader")
    print("=" * 60)
    
    # Check if kaggle is installed
    print("\n1. Checking Kaggle CLI installation...")
    result = os.system("kaggle --version")
    
    if result != 0:
        print("\n❌ Kaggle CLI not installed")
        print("Installing Kaggle CLI...")
        os.system("pip install kaggle")
    else:
        print("✅ Kaggle CLI installed")
    
    # Check if API token is configured
    print("\n2. Checking Kaggle API configuration...")
    if not check_kaggle_setup():
        sys.exit(1)
    
    # Download datasets
    print("\n3. Downloading datasets...")
    response = input("Proceed with download? (y/n): ")
    
    if response.lower() == 'y':
        download_kaggle_datasets()
        
        # Option to search for more datasets
        print("\n")
        search_more = input("Search for more datasets? (y/n): ")
        if search_more.lower() == 'y':
            query = input("Enter search query (e.g., 'blood pressure'): ")
            search_kaggle_datasets(query)
    else:
        print("Download cancelled")

if __name__ == "__main__":
    main()
