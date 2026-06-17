import 'package:flutter/services.dart';

class SensorService {
  static const MethodChannel _channel = MethodChannel('com.healsense/sensors');

  static Future<double> getHeartRate() async {
    try {
      final double heartRate = await _channel.invokeMethod('getHeartRate');
      return heartRate;
    } on PlatformException catch (e) {
      print("Failed to get heart rate: '${e.message}'.");
      return 0.0;
    }
  }

  static Future<void> startHeartRateService() async {
    try {
      await _channel.invokeMethod('startHeartRateService');
    } on PlatformException catch (e) {
      print("Failed to start heart rate service: '${e.message}'.");
    }
  }
}
