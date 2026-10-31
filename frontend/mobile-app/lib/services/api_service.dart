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
                  defaultValue: 'http://127.0.0.1:5000/api/v1',
                ),
            connectTimeout: const Duration(seconds: 8),
            receiveTimeout: const Duration(seconds: 8),
            headers: {'Content-Type': 'application/json'},
          ),
        ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (_authToken != null && _authToken!.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $_authToken';
          }
          return handler.next(options);
        },
      ),
    );
  }

  final Dio _dio;
  String? _authToken;

  void setAuthToken(String? token) {
    _authToken = token;
  }

  String get wsBaseUrl {
    final api = _dio.options.baseUrl;
    if (api.startsWith('https://')) {
      return api.replaceFirst('https://', 'wss://').replaceFirst('/api/v1', '');
    }
    return api.replaceFirst('http://', 'ws://').replaceFirst('/api/v1', '');
  }

  /// Authenticate with email and password to receive a JWT access token.
  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await _dio.post(
        '/auth/login',
        data: {
          'email': email.trim().toLowerCase(),
          'password': password,
        },
      );
      final data = Map<String, dynamic>.from(response.data as Map);
      return data;
    } on DioException catch (e) {
      final detail = e.response?.data;
      if (detail is Map && detail['detail'] != null) {
        final d = detail['detail'];
        if (d is Map && d['message'] != null) {
          throw Exception(d['message']);
        }
        if (d is String) throw Exception(d);
      }
      throw Exception('Login failed: ${e.message}');
    }
  }

  /// Get current authenticated user profile (/auth/me)
  Future<Map<String, dynamic>> getMe() async {
    try {
      final response = await _dio.get('/auth/me');
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (e) {
      throw Exception('Failed to fetch user profile: ${e.message}');
    }
  }

  /// Fetches latest vitals for the authenticated patient.
  Future<VitalReading> fetchLatestVitals(String patientId) async {
    try {
      final response = await _dio.get('/patients/$patientId/vitals/latest');
      final data = Map<String, dynamic>.from(response.data as Map);
      return VitalReading.fromJson(data);
    } catch (e) {
      rethrow;
    }
  }

  /// Fetches historical vitals for the authenticated patient.
  Future<List<VitalReading>> fetchVitalHistory(String patientId, {int minutes = 60}) async {
    try {
      final response = await _dio.get('/patients/$patientId/vitals/history?minutes=$minutes');
      return (response.data as List)
          .map((item) => VitalReading.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } catch (e) {
      rethrow;
    }
  }

  /// Posts an intermittent BP reading from a cuff or clinician entry.
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

    if (data is Map && data['detail'] is List && (data['detail'] as List).isNotEmpty) {
      final first = (data['detail'] as List).first;
      if (first is Map) {
        return BpEntryException(message: (first['msg'] ?? 'Invalid reading').toString());
      }
    }

    return BpEntryException(message: e.message ?? 'Failed to record blood pressure');
  }

  Future<void> triggerEmergency(String patientId) async {
    try {
      await _dio.post('/patients/$patientId/emergency');
    } catch (e) {
      rethrow;
    }
  }
}
