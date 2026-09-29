"""
Quick test script to verify database endpoints are working
"""
import requests
import json

BASE_URL = "http://localhost:5000/api/v1"


def print_response(title, response):
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Success!")
        print(json.dumps(response.json(), indent=2))
    else:
        print("❌ Failed!")
        print(response.text)


def test_endpoints():
    print("\n🚀 Testing HealSense Database Endpoints\n")
    
    # 1. Test Health Check
    response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health")
    print_response("Health Check", response)
    
    # 2. Test Get All Patients
    response = requests.get(f"{BASE_URL}/patients")
    print_response("Get All Patients", response)
    
    # 3. Test Get Patient Profile
    response = requests.get(f"{BASE_URL}/patients/P001/profile")
    print_response("Get Patient P001 Profile", response)
    
    # 4. Test Get Latest Vitals
    response = requests.get(f"{BASE_URL}/patients/P001/vitals/latest")
    print_response("Get Latest Vitals for P001", response)
    
    # 5. Test Get Alerts
    response = requests.get(f"{BASE_URL}/patients/P001/alerts")
    print_response("Get Alerts for P001", response)
    
    # 6. Test Get Device Status
    response = requests.get(f"{BASE_URL}/devices/DEV001/status")
    print_response("Get Device DEV001 Status", response)
    
    print("\n✅ All tests completed!\n")


if __name__ == "__main__":
    test_endpoints()
