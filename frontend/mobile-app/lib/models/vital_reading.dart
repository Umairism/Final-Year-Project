class VitalReading {
  final double heartRate;
  final double spo2;
  final double temperature;
  final String bloodPressure;
  final double respiratoryRate;
  final DateTime timestamp;

  VitalReading({
    required this.heartRate,
    required this.spo2,
    required this.temperature,
    required this.bloodPressure,
    required this.respiratoryRate,
    required this.timestamp,
  });

  factory VitalReading.fromJson(Map<String, dynamic> json) {
    return VitalReading(
      heartRate: (json['heartRate'] as num).toDouble(),
      spo2: (json['spo2'] as num).toDouble(),
      temperature: (json['temperature'] as num).toDouble(),
      bloodPressure: json['bloodPressure'] as String,
      respiratoryRate: (json['respiratoryRate'] as num).toDouble(),
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  Map<String, dynamic> toJson() => {
        'heartRate': heartRate,
        'spo2': spo2,
        'temperature': temperature,
        'bloodPressure': bloodPressure,
        'respiratoryRate': respiratoryRate,
        'timestamp': timestamp.toIso8601String(),
      };
}
