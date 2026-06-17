"""
Test script for Phone Sensor Integration
Demonstrates dual-mode operation: IoT Device + Phone Sensors
"""
import requests
import json
import time

BASE_URL = "http://localhost:5000/api/v1"


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_phone_sensor_integration():
    print("\n🚀 Testing HealSense Phone Sensor Integration")
    print("📱 Simulating Samsung Galaxy S8+ as monitoring device\n")
    
    # Step 1: Register phone as device
    print_section("Step 1: Register Samsung S8+ as monitoring device")
    
    phone_data = {
        "patient_id": "P001",
        "phone_model": "Samsung Galaxy S8+",
        "phone_os": "Android 11",
        "sensors": ["heart_rate", "spo2", "accelerometer", "gps", "gyroscope"]
    }
    
    response = requests.post(
        f"{BASE_URL}/devices/register/phone",
        json=phone_data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Phone registered successfully!")
        print(f"   Device ID: {data['device_id']}")
        print(f"   Device Type: {data['device_type']}")
        print(f"   Phone Model: {data['phone_model']}")
        print(f"   Available Sensors: {', '.join(data['sensors'])}")
    else:
        print(f"❌ Registration failed: {response.text}")
        return
    
    # Step 2: Send vitals from phone
    print_section("Step 2: Send vitals from phone sensors")
    
    # Simulate resting vitals
    vitals_data = {
        "device_id": "PHONE_P001",
        "heart_rate": 72.0,
        "spo2": 98.5,
        "temperature": 36.8,
        "activity_context": "resting",
        "accuracy": 0.95,
        "location_lat": 31.5497,  # Lahore coordinates
        "location_lng": 74.3436
    }
    
    response = requests.post(
        f"{BASE_URL}/patients/P001/vitals/phone",
        params=vitals_data
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Phone vitals recorded!")
        print(f"   Vital ID: {data['vital_id']}")
        print(f"   Health Status: {data['status']}")
        print(f"   Data Source: {data['data_source']}")
        print(f"   Activity: {data['activity_context']}")
        print(f"   Alert Created: {'Yes' if data['alert_created'] else 'No'}")
    
    time.sleep(1)
    
    # Step 3: Send elevated vitals (walking)
    print_section("Step 3: Send vitals while walking (elevated HR)")
    
    vitals_walking = {
        "device_id": "PHONE_P001",
        "heart_rate": 95.0,
        "spo2": 97.0,
        "temperature": 37.2,
        "activity_context": "walking",
        "accuracy": 0.88
    }
    
    response = requests.post(
        f"{BASE_URL}/patients/P001/vitals/phone",
        params=vitals_walking
    )
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Walking vitals recorded!")
        print(f"   Heart Rate: {vitals_walking['heart_rate']} bpm (elevated, but normal for walking)")
        print(f"   Health Status: {data['status']}")
        print(f"   Activity: {data['activity_context']}")
    
    time.sleep(1)
    
    # Step 4: Send abnormal vitals (alert trigger)
    print_section("Step 4: Send abnormal vitals (trigger alert)")
    
    vitals_abnormal = {
        "device_id": "PHONE_P001",
        "heart_rate": 135.0,
        "spo2": 90.0,
        "temperature": 37.8,
        "activity_context": "resting",
        "accuracy": 0.93,
        "location_lat": 31.5497,
        "location_lng": 74.3436
    }
    
    response = requests.post(
        f"{BASE_URL}/patients/P001/vitals/phone",
        params=vitals_abnormal
    )
    
    if response.status_code == 201:
        data = response.json()
        print(f"⚠️  Abnormal vitals detected!")
        print(f"   Heart Rate: {vitals_abnormal['heart_rate']} bpm (HIGH)")
        print(f"   SpO2: {vitals_abnormal['spo2']}% (LOW)")
        print(f"   Health Status: {data['status']}")
        print(f"   Alert Created: {'Yes ⚠️' if data['alert_created'] else 'No'}")
    
    time.sleep(1)
    
    # Step 5: Check all data sources for patient
    print_section("Step 5: View all data sources for patient")
    
    response = requests.get(f"{BASE_URL}/devices/patient/P001/sources")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Patient: {data['patient_id']}")
        print(f"Total Devices: {data['total_devices']}")
        print(f"Primary Source: {data['primary_source']}\n")
        
        for i, source in enumerate(data['data_sources'], 1):
            print(f"{i}. {source['device_id']}")
            print(f"   Type: {source['device_type']}")
            if source.get('phone_model'):
                print(f"   Model: {source['phone_model']}")
            print(f"   Connected: {'✅' if source['connected'] else '❌'}")
            print(f"   Battery: {source['battery_level']}%")
            print()
    
    # Step 6: Get latest vitals (should show phone data)
    print_section("Step 6: Get latest vitals from all sources")
    
    response = requests.get(f"{BASE_URL}/patients/P001/vitals/latest")
    
    if response.status_code == 200:
        vitals = response.json()
        print(f"Latest Vitals:")
        print(f"   Heart Rate: {vitals['heart_rate']} bpm")
        print(f"   SpO2: {vitals['spo2']}%")
        print(f"   Temperature: {vitals['temperature']}°C")
        print(f"   Status: {vitals['status']}")
        if vitals.get('activity_context'):
            print(f"   Activity: {vitals['activity_context']}")
        if vitals.get('location_lat'):
            print(f"   Location: ({vitals['location_lat']}, {vitals['location_lng']})")
    
    # Step 7: Check alerts
    print_section("Step 7: Check alerts generated from phone data")
    
    response = requests.get(f"{BASE_URL}/patients/P001/alerts")
    
    if response.status_code == 200:
        alerts = response.json()
        print(f"Total Alerts: {len(alerts)}")
        for alert in alerts[-3:]:  # Show last 3 alerts
            print(f"\n• {alert['message']}")
            print(f"  Severity: {alert['severity']}")
            print(f"  Time: {alert['timestamp']}")
            print(f"  Acknowledged: {'✅' if alert['acknowledged'] else '❌'}")
    
    print_section("✅ Phone Sensor Integration Test Complete!")
    print("Your Samsung S8+ is now fully integrated with HealSense!")
    print("\nBenefits:")
    print("  • No need for dedicated IoT device initially")
    print("  • Use phone sensors when IoT device unavailable")
    print("  • Activity-aware monitoring (resting vs. walking)")
    print("  • GPS location for emergencies")
    print("  • Seamless fallback between IoT and phone\n")


if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
        if response.status_code == 200:
            test_phone_sensor_integration()
        else:
            print("❌ Backend server not responding. Please start the server first.")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server.")
        print("Please start the server with: python run.py")
