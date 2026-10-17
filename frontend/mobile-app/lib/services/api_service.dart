import 'package:dio/dio.dart';
import 'package:healsense/models/bp_entry_result.dart';
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
    final systolic = json['systolic_bp'] as num?;
    final diastolic = json['diastolic_bp'] as num?;

    return VitalReading(
      heartRate: (json['heart_rate'] as num?)?.toDouble() ?? 0,
      spo2: (json['spo2'] as num?)?.toDouble() ?? 0,
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0,
      // A missing BP is "not measured", never 0/0.
      bloodPressure: (systolic == null || diastolic == null)
          ? 'Not measured'
          : '${systolic.toStringAsFixed(0)}/${diastolic.toStringAsFixed(0)}',
      respiratoryRate: (json['respiratory_rate'] as num?)?.toDouble() ?? 0,
      timestamp: DateTime.tryParse((json['timestamp'] ?? '').toString()) ?? DateTime.now(),
    );
  }

  /// Posts an intermittent BP reading from a cuff (Braun ExactFit 1, BLE cuff)
  /// or from clinician entry.
  ///
  /// [heartRate], [spo2] and [temperature] are only used by the backend when
  /// there is no wearable reading to attach the BP to; pass them to allow a
  /// standalone entry.
  Future<BpEntryResult> recordBloodPressure({
    required String patientId,
    required double systolic,
    required double diastolic,
    double? pulse,
    double? heartRate,
    double? spo2,
    double? temperature,
    String bpSource = 'manual_entry',
    String? note,
  }) async {
    try {
      final response = await _dio.post(
        '/patients/$patientId/bp',
        data: {
          'systolic_bp': systolic,
          'diastolic_bp': diastolic,
          'bp_source': bpSource,
          if (pulse != null) 'pulse': pulse,
          if (heartRate != null) 'heart_rate': heartRate,
          if (spo2 != null) 'spo2': spo2,
          if (temperature != null) 'temperature': temperature,
          if (note != null && note.isNotEmpty) 'note': note,
        },
      );
      return BpEntryResult.fromJson(Map<String, dynamic>.from(response.data as Map));
    } on DioException catch (e) {
      throw _toBpException(e);
    }
  }

  BpEntryException _toBpException(DioException e) {
    final data = e.response?.data;

    if (data is Map && data['detail'] is Map) {
      final detail = Map<String, dynamic>.from(data['detail'] as Map);
      if (detail['error'] == 'no_anchor_reading') {
        return BpEntryException(
          message: (detail['message'] ?? 'No wearable reading to attach this BP to.').toString(),
          isNoAnchor: true,
          missingFields: (detail['missing_fields'] as List<dynamic>? ?? const [])
              .map((e) => e.toString())
              .toList(),
          category: detail['category']?.toString(),
        );
      }
      if (detail['message'] != null) {
        return BpEntryException(message: detail['message'].toString());
      }
    }

    // FastAPI validation errors arrive as a list of {msg, loc, ...}.
    if (data is Map && data['detail'] is List && (data['detail'] as List).isNotEmpty) {
      final first = (data['detail'] as List).first;
      if (first is Map) {
        return BpEntryException(message: (first['msg'] ?? 'Invalid reading').toString());
      }
    }

    return BpEntryException(message: e.message ?? 'Failed to record blood pressure');
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
