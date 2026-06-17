import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:healsense/models/vital_reading.dart';
import 'package:healsense/services/api_service.dart';
import 'package:healsense/services/realtime_service.dart';
import 'package:healsense/services/sensor_service.dart';

class VitalsProvider with ChangeNotifier {
  VitalsProvider({ApiService? apiService, String patientId = 'P001'})
      : _apiService = apiService ?? ApiService(),
        _patientId = patientId {
    _initializeRealtimeAndIot();
  }

  VitalReading? _currentVitals;
  List<VitalReading> _history = [];
  String? _deviceId;
  Timer? _pollingTimer;
  Timer? _iotPushTimer;
  Timer? _pingTimer;
  bool _isLoading = false;
  String? _error;
  bool _isRealtimeConnected = false;

  final ApiService _apiService;
  final RealtimeService _realtimeService = RealtimeService();
  final String _patientId;

  VitalReading? get currentVitals => _currentVitals;
  List<VitalReading> get history => _history;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isRealtimeConnected => _isRealtimeConnected;
  String? get deviceId => _deviceId;

  Future<void> _initializeRealtimeAndIot() async {
    await _registerPhoneAsDevice();
    await _connectRealtime();
    _startPhoneSensorPush();
    if (!_isRealtimeConnected) {
      startPolling();
    }
  }

  void startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      refreshLatestVitals();
    });

    refreshLatestVitals();
  }

  Future<void> _registerPhoneAsDevice() async {
    try {
      _deviceId = await _apiService.registerPhoneDevice(
        patientId: _patientId,
        phoneModel: 'Flutter Phone Client',
        phoneOs: Platform.operatingSystem,
        sensors: const ['heart_rate', 'spo2', 'temperature'],
      );
    } catch (e) {
      _error = 'Failed to register phone device: $e';
      notifyListeners();
    }
  }

  Future<void> _connectRealtime() async {
    final wsUrl = '${_apiService.wsBaseUrl}/ws/patients/$_patientId';

    try {
      await _realtimeService.connect(
        wsUrl: wsUrl,
        onEvent: _handleRealtimeEvent,
        onError: (error) {
          _isRealtimeConnected = false;
          _error = 'Realtime connection error: $error';
          notifyListeners();
          startPolling();
        },
        onDone: () {
          _isRealtimeConnected = false;
          notifyListeners();
          startPolling();
        },
      );

      _isRealtimeConnected = true;
      _pollingTimer?.cancel();
      _error = null;
      notifyListeners();

      _pingTimer?.cancel();
      _pingTimer = Timer.periodic(const Duration(seconds: 20), (_) {
        _realtimeService.sendPing();
      });
    } catch (e) {
      _isRealtimeConnected = false;
      _error = 'Failed to connect realtime stream: $e';
      notifyListeners();
      startPolling();
    }
  }

  void _handleRealtimeEvent(Map<String, dynamic> event) {
    final eventType = event['event_type']?.toString() ?? '';
    final payload = event['payload'];
    if (payload is! Map<String, dynamic>) return;

    VitalReading? reading;
    if (eventType == 'patient.vitals.created' && payload['vital'] is Map<String, dynamic>) {
      reading = _readingFromBackend(Map<String, dynamic>.from(payload['vital'] as Map));
    } else if (eventType == 'patient.vitals.phone_created') {
      reading = _readingFromPhoneEvent(payload);
    }

    if (reading != null) {
      _currentVitals = reading;
      _history = [reading, ..._history].take(120).toList();
      _checkThresholds(reading);
      notifyListeners();
    }
  }

  VitalReading _readingFromBackend(Map<String, dynamic> json) {
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

  VitalReading _readingFromPhoneEvent(Map<String, dynamic> json) {
    return VitalReading(
      heartRate: (json['heart_rate'] as num?)?.toDouble() ?? 0,
      spo2: (json['spo2'] as num?)?.toDouble() ?? 0,
      temperature: (json['temperature'] as num?)?.toDouble() ?? 0,
      bloodPressure: '120/80',
      respiratoryRate: 16,
      timestamp: DateTime.now(),
    );
  }

  void _startPhoneSensorPush() {
    _iotPushTimer?.cancel();
    _iotPushTimer = Timer.periodic(const Duration(seconds: 8), (_) async {
      if (_deviceId == null) return;

      try {
        final measuredHeartRate = await SensorService.getHeartRate();
        final base = _currentVitals;
        final heartRate = measuredHeartRate > 0 ? measuredHeartRate : (base?.heartRate ?? 72);
        final spo2 = base?.spo2 ?? 98;
        final temperature = base?.temperature ?? 36.8;

        await _apiService.pushPhoneVitals(
          patientId: _patientId,
          deviceId: _deviceId!,
          heartRate: heartRate,
          spo2: spo2,
          temperature: temperature,
          activityContext: 'resting',
          accuracy: measuredHeartRate > 0 ? 0.95 : 0.75,
        );
      } catch (e) {
        _error = 'IoT push failed: $e';
        notifyListeners();
      }
    });
  }

  void _checkThresholds(VitalReading vitals) {
    if (vitals.heartRate < 60 || vitals.heartRate > 100) {
      _triggerLocalAlert("Heart Rate", vitals.heartRate.toString(), "Irregular Heart Rate detected");
    }
    if (vitals.spo2 < 90) {
      _triggerLocalAlert("SpO2", vitals.spo2.toString(), "Critical SpO2 levels!");
    }
    if (vitals.temperature > 37.5) {
      _triggerLocalAlert("Temperature", vitals.temperature.toString(), "High Fever detected");
    }
  }

  void _triggerLocalAlert(String type, String value, String message) {
    debugPrint("ALERT: $type - $value: $message");
  }

  Future<void> refreshLatestVitals() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final newVitals = await _apiService.fetchLatestVitals(_patientId);
      _currentVitals = newVitals;
      _checkThresholds(newVitals);
    } catch (e) {
      _error = 'Failed to fetch latest vitals: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> refreshHistory({int minutes = 60}) async {
    try {
      _history = await _apiService.fetchVitalHistory(_patientId, minutes: minutes);
      notifyListeners();
    } catch (e) {
      _error = 'Failed to fetch vital history: $e';
      notifyListeners();
    }
  }

  Future<void> triggerEmergency() async {
    try {
      await _apiService.triggerEmergency(_patientId);
    } catch (e) {
      _error = 'Failed to trigger emergency: $e';
      notifyListeners();
      rethrow;
    }
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    _iotPushTimer?.cancel();
    _pingTimer?.cancel();
    _realtimeService.disconnect();
    super.dispose();
  }
}
