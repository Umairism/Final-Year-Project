import 'package:dio/dio.dart';
import 'package:healsense/models/vital_reading.dart';

class ApiService {
  ApiService({String? baseUrl})
      : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl ??
                const String.fromEnvironment(
                  'HEALSENSE_API_BASE_URL',
                  defaultValue: 'http://10.10.86.33:5000/api/v1',
                ),
            connectTimeout: const Duration(seconds: 8),
            receiveTimeout: const Duration(seconds: 8),
          ),
        );

  final Dio _dio;

  String get wsBaseUrl {
    final api = _dio.options.baseUrl;
    if (api.startsWith('https://')) {
      return api.replaceFirst('https://', 'wss://').replaceFirst('/api/v1', '');
    }
    return api.replaceFirst('http://', 'ws://').replaceFirst('/api/v1', '');
  }

  VitalReading _mapVital(Map<String, dynamic> json) {
    final systolic = (json['systolic_bp'] ?? 0).toString();
    final diastolic = (json['diastolic_bp'] ?? 0).toString();

    return VitalReading(
      heartRate: (json['heart_rate'] as num?)?.toDouble() ?? 0,
      spo2: (json['spo2'] as num?)?.toDouble() ?? 0,
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0,
      bloodPressure: '$systolic/$diastolic',
      respiratoryRate: (json['respiratory_rate'] as num?)?.toDouble() ?? 0,
      timestamp: DateTime.tryParse((json['timestamp'] ?? '').toString()) ?? DateTime.now(),
    );
  }

  Future<VitalReading> fetchLatestVitals(String patientId) async {
    try {
      final response = await _dio.get('/patients/$patientId/vitals/latest');
      return _mapVital(Map<String, dynamic>.from(response.data));
    } catch (e) {
      rethrow;
    }
  }

  Future<List<VitalReading>> fetchVitalHistory(String patientId, {int minutes = 60}) async {
    try {
      final response = await _dio.get('/patients/$patientId/vitals/history?minutes=$minutes');
      return (response.data as List)
          .map((item) => _mapVital(Map<String, dynamic>.from(item as Map)))
          .toList();
    } catch (e) {
      rethrow;
    }
  }

  Future<void> triggerEmergency(String patientId) async {
    try {
      await _dio.post('/patients/$patientId/emergency');
    } catch (e) {
      rethrow;
    }
  }

  Future<String> registerPhoneDevice({
    required String patientId,
    required String phoneModel,
    required String phoneOs,
    required List<String> sensors,
  }) async {
    try {
      final response = await _dio.post(
        '/devices/register/phone',
        data: {
          'patient_id': patientId,
          'phone_model': phoneModel,
          'phone_os': phoneOs,
          'sensors': sensors,
        },
      );
      return (response.data['device_id'] as String?) ?? 'PHONE_$patientId';
    } catch (e) {
      rethrow;
    }
  }

  Future<void> pushPhoneVitals({
    required String patientId,
    required String deviceId,
    required double heartRate,
    required double spo2,
    required double temperature,
    String activityContext = 'resting',
    double accuracy = 0.9,
  }) async {
    try {
      await _dio.post(
        '/patients/$patientId/vitals/phone',
        queryParameters: {
          'device_id': deviceId,
          'heart_rate': heartRate,
          'spo2': spo2,
          'temperature': temperature,
          'activity_context': activityContext,
          'accuracy': accuracy,
        },
      );
    } catch (e) {
      rethrow;
    }
  }
}
