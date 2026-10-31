import 'package:flutter_test/flutter_test.dart';
import 'package:healsense/models/vital_reading.dart';
import 'package:healsense/providers/vitals_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('VitalReading tests', () {
    test('ESP32 null blood pressure shows "Not measured"', () {
      final json = {
        'id': 'vital-esp-001',
        'heart_rate': 78.0,
        'spo2': 98.0,
        'temperature': 36.8,
        'systolic_bp': null,
        'diastolic_bp': null,
        'timestamp': '2026-10-30T10:00:00Z',
        'data_origin': 'device',
      };

      final reading = VitalReading.fromJson(json);
      expect(reading.id, 'vital-esp-001');
      expect(reading.heartRate, 78.0);
      expect(reading.bloodPressure, 'Not measured');
      expect(reading.dataOrigin, 'device');
    });

    test('Valid cuff blood pressure displays formatted mmHg', () {
      final json = {
        'id': 'vital-cuff-001',
        'heart_rate': 72.0,
        'spo2': 99.0,
        'temperature': 36.6,
        'systolic_bp': 122.0,
        'diastolic_bp': 81.0,
        'timestamp': '2026-10-30T10:05:00Z',
        'data_origin': 'device',
      };

      final reading = VitalReading.fromJson(json);
      expect(reading.bloodPressure, '122/81');
    });
  });

  group('VitalsProvider lifecycle & boundaries', () {
    test('Initializes cleanly without initiating network requests', () {
      final provider = VitalsProvider();
      expect(provider.currentVitals, isNull);
      expect(provider.history, isEmpty);
      expect(provider.isRealtimeConnected, isFalse);
      expect(provider.isLoading, isFalse);
      expect(provider.patientId, isNull);
      provider.dispose();
    });

    test('clear() wipes all state, timers, and patient binding', () {
      final provider = VitalsProvider();
      provider.clear();
      expect(provider.currentVitals, isNull);
      expect(provider.history, isEmpty);
      expect(provider.patientId, isNull);
      provider.dispose();
    });
  });
}

