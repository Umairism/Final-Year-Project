class VitalReading {
  final String? id;
  final double heartRate;
  final double spo2;
  final double temperature;
  final String bloodPressure;
  final double respiratoryRate;
  final DateTime timestamp;
  final String dataOrigin;

  VitalReading({
    this.id,
    required this.heartRate,
    required this.spo2,
    required this.temperature,
    required this.bloodPressure,
    required this.respiratoryRate,
    required this.timestamp,
    this.dataOrigin = 'device',
  });

  factory VitalReading.fromJson(Map<String, dynamic> json) {
    final systolic = json['systolic_bp'] as num? ?? json['systolic'] as num?;
    final diastolic = json['diastolic_bp'] as num? ?? json['diastolic'] as num?;

    final String bpText;
    if (systolic == null || diastolic == null) {
      bpText = 'Not measured';
    } else {
      bpText = '${systolic.toStringAsFixed(0)}/${diastolic.toStringAsFixed(0)}';
    }

    return VitalReading(
      id: json['id']?.toString(),
      heartRate: (json['heart_rate'] as num? ?? json['heartRate'] as num? ?? 0).toDouble(),
      spo2: (json['spo2'] as num? ?? 0).toDouble(),
      temperature: (json['temperature'] as num? ?? 0).toDouble(),
      bloodPressure: bpText,
      respiratoryRate: (json['respiratory_rate'] as num? ?? json['respiratoryRate'] as num? ?? 0).toDouble(),
      timestamp: DateTime.tryParse((json['timestamp'] ?? '').toString()) ?? DateTime.now(),
      dataOrigin: json['data_origin']?.toString() ?? 'device',
    );
  }

  Map<String, dynamic> toJson() => {
        if (id != null) 'id': id,
        'heartRate': heartRate,
        'spo2': spo2,
        'temperature': temperature,
        'bloodPressure': bloodPressure,
        'respiratoryRate': respiratoryRate,
        'timestamp': timestamp.toIso8601String(),
        'dataOrigin': dataOrigin,
      };
}
