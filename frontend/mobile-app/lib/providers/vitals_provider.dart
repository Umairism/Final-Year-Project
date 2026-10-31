import 'dart:async';
import 'package:flutter/material.dart';
import 'package:healsense/models/bp_entry_result.dart';
import 'package:healsense/models/vital_reading.dart';
import 'package:healsense/services/api_service.dart';
import 'package:healsense/services/realtime_service.dart';

class VitalsProvider with ChangeNotifier {
  VitalsProvider({ApiService? apiService})
      : _apiService = apiService ?? ApiService();

  final ApiService _apiService;
  final RealtimeService _realtimeService = RealtimeService();

  String? _patientId;
  String? _token;
  VitalReading? _currentVitals;
  List<VitalReading> _history = [];
  Timer? _pollingTimer;
  Timer? _pingTimer;
  bool _isLoading = false;
  String? _error;
  bool _isRealtimeConnected = false;

  VitalReading? get currentVitals => _currentVitals;
  List<VitalReading> get history => _history;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isRealtimeConnected => _isRealtimeConnected;
  String? get patientId => _patientId;

  /// Configure with authenticated patient ID and JWT token.
  /// Starts live WebSocket connection and loads initial vitals.
  Future<void> configure({
    required String patientId,
    required String token,
  }) async {
    if (_patientId == patientId && _token == token && (_isRealtimeConnected || _isLoading)) {
      return;
    }

    clear();
    _patientId = patientId;
    _token = token;
    _apiService.setAuthToken(token);

    _isLoading = true;
    notifyListeners();

    await refreshLatestVitals();
    await refreshHistory();
    await _connectRealtime();

    _isLoading = false;
    notifyListeners();
  }

  /// Reset state and tear down all network connections on logout.
  void clear() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _pingTimer?.cancel();
    _pingTimer = null;
    _realtimeService.disconnect();

    _patientId = null;
    _token = null;
    _currentVitals = null;
    _history = [];
    _isRealtimeConnected = false;
    _isLoading = false;
    _error = null;
    notifyListeners();
  }

  void _startPollingFallback() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!_isRealtimeConnected && _patientId != null) {
        refreshLatestVitals();
      }
    });
  }

  Future<void> _connectRealtime() async {
    if (_patientId == null || _token == null) return;

    final wsBase = _apiService.wsBaseUrl;
    final encodedPatient = Uri.encodeComponent(_patientId!);
    final encodedToken = Uri.encodeComponent(_token!);
    final wsUrl = '$wsBase/ws/patients/$encodedPatient?token=$encodedToken';

    try {
      await _realtimeService.connect(
        wsUrl: wsUrl,
        onEvent: _handleRealtimeEvent,
        onError: (err) {
          _isRealtimeConnected = false;
          _error = 'Realtime stream disconnected: $err';
          notifyListeners();
          _startPollingFallback();
        },
        onDone: () {
          _isRealtimeConnected = false;
          notifyListeners();
          _startPollingFallback();
        },
      );

      _isRealtimeConnected = true;
      _pollingTimer?.cancel();
      _pollingTimer = null;
      _error = null;
      notifyListeners();

      _pingTimer?.cancel();
      _pingTimer = Timer.periodic(const Duration(seconds: 25), (_) {
        _realtimeService.sendPing();
      });
    } catch (e) {
      _isRealtimeConnected = false;
      _error = 'Realtime connection failed: $e';
      notifyListeners();
      _startPollingFallback();
    }
  }

  void _handleRealtimeEvent(Map<String, dynamic> event) {
    final eventType = event['event_type']?.toString() ?? '';
    final payload = event['payload'];
    if (payload is! Map<String, dynamic>) return;

    VitalReading? reading;
    if (eventType == 'patient.vitals.created') {
      final rawVital = payload['vital'];
      if (rawVital is Map<String, dynamic>) {
        reading = VitalReading.fromJson(Map<String, dynamic>.from(rawVital));
      } else {
        reading = VitalReading.fromJson(payload);
      }
    }

    if (reading != null) {
      _mergeReading(reading);
    }
  }

  /// Deduplicate reading by ID and preserve chronological order.
  void _mergeReading(VitalReading reading) {
    _currentVitals = reading;

    final updated = <VitalReading>[];
    bool replaced = false;

    for (final item in _history) {
      final isSameId = reading.id != null && item.id != null && reading.id == item.id;
      final isSameTs = reading.id == null && reading.timestamp.millisecondsSinceEpoch == item.timestamp.millisecondsSinceEpoch;

      if (isSameId || isSameTs) {
        updated.add(reading);
        replaced = true;
      } else {
        updated.add(item);
      }
    }

    if (!replaced) {
      updated.add(reading);
    }

    // Sort descending for display history (newest first)
    updated.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    _history = updated.take(120).toList();

    _checkThresholds(reading);
    notifyListeners();
  }

  void _checkThresholds(VitalReading vitals) {
    if (vitals.heartRate < 40 || vitals.heartRate > 140) {
      debugPrint('ALERT: Heart Rate ${vitals.heartRate} out of range');
    }
    if (vitals.spo2 < 90) {
      debugPrint('ALERT: Critical SpO2 level ${vitals.spo2}%');
    }
    if (vitals.temperature > 38.5) {
      debugPrint('ALERT: High Temperature ${vitals.temperature}°C');
    }
  }

  Future<void> refreshLatestVitals() async {
    if (_patientId == null) return;
    try {
      final latest = await _apiService.fetchLatestVitals(_patientId!);
      _mergeReading(latest);
      _error = null;
    } catch (e) {
      // 404 is normal when no readings exist yet for this patient
      if (!e.toString().contains('404')) {
        _error = 'Failed to fetch latest vitals: $e';
      }
    } finally {
      notifyListeners();
    }
  }

  Future<void> refreshHistory({int minutes = 120}) async {
    if (_patientId == null) return;
    try {
      final list = await _apiService.fetchVitalHistory(_patientId!, minutes: minutes);
      for (final r in list) {
        _mergeReading(r);
      }
      _error = null;
    } catch (e) {
      if (!e.toString().contains('404')) {
        _error = 'Failed to fetch vitals history: $e';
      }
    } finally {
      notifyListeners();
    }
  }

  Future<BpEntryResult> recordBloodPressure({
    required double systolic,
    required double diastolic,
    double? pulse,
    double? heartRate,
    double? spo2,
    double? temperature,
    String bpSource = 'manual_entry',
    String? note,
  }) async {
    if (_patientId == null) throw Exception('No authenticated patient profile.');

    final result = await _apiService.recordBloodPressure(
      patientId: _patientId!,
      systolic: systolic,
      diastolic: diastolic,
      pulse: pulse,
      heartRate: heartRate,
      spo2: spo2,
      temperature: temperature,
      bpSource: bpSource,
      note: note,
    );

    await refreshLatestVitals();
    return result;
  }

  Future<BpEntryResult> submitBloodPressure({
    required double systolic,
    required double diastolic,
    double? pulse,
    String? note,
  }) => recordBloodPressure(
    systolic: systolic,
    diastolic: diastolic,
    pulse: pulse,
    note: note,
  );

  Future<void> triggerEmergency() async {
    if (_patientId == null) throw Exception('No authenticated patient profile.');
    await _apiService.triggerEmergency(_patientId!);
  }

  @override
  void dispose() {
    clear();
    super.dispose();
  }
}
