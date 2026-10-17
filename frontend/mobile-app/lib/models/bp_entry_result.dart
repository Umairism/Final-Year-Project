/// Result of posting a manual blood-pressure reading to
/// `POST /api/v1/patients/{id}/bp`.
class BpEntryResult {
  const BpEntryResult({
    required this.attached,
    required this.vitalId,
    required this.systolic,
    required this.diastolic,
    required this.category,
    required this.status,
    required this.message,
    this.pulse,
    this.triggeredRules = const [],
    this.alertId,
  });

  /// True when the BP was attached to an existing wearable reading.
  final bool attached;
  final String vitalId;
  final double systolic;
  final double diastolic;
  final double? pulse;
  final String category;
  final String status; // normal | warning | critical
  final String message;
  final List<String> triggeredRules;
  final String? alertId;

  factory BpEntryResult.fromJson(Map<String, dynamic> json) {
    return BpEntryResult(
      attached: json['attached'] as bool? ?? false,
      vitalId: (json['vital_id'] ?? '').toString(),
      systolic: (json['systolic_bp'] as num?)?.toDouble() ?? 0,
      diastolic: (json['diastolic_bp'] as num?)?.toDouble() ?? 0,
      pulse: (json['pulse'] as num?)?.toDouble(),
      category: (json['category'] ?? 'normal').toString(),
      status: (json['status'] ?? 'normal').toString(),
      message: (json['message'] ?? '').toString(),
      triggeredRules: (json['triggered_rules'] as List<dynamic>? ?? const [])
          .map((e) => e.toString())
          .toList(),
      alertId: json['alert_id']?.toString(),
    );
  }

  String get reading => '${systolic.toStringAsFixed(0)}/${diastolic.toStringAsFixed(0)}';

  String get categoryLabel {
    switch (category) {
      case 'hypertensive_crisis':
        return 'Hypertensive crisis';
      case 'stage_2_hypertension':
        return 'Stage 2 hypertension';
      case 'stage_1_hypertension':
        return 'Stage 1 hypertension';
      case 'elevated':
        return 'Elevated';
      case 'hypotension':
        return 'Hypotension';
      default:
        return 'Normal';
    }
  }

  bool get isCritical => status == 'critical';
}

/// Thrown when the backend refuses a reading because there is no wearable row
/// to attach it to (HTTP 409) — the body still carries the BP assessment.
class BpEntryException implements Exception {
  const BpEntryException({
    required this.message,
    this.isNoAnchor = false,
    this.missingFields = const [],
    this.category,
  });

  final String message;
  final bool isNoAnchor;
  final List<String> missingFields;
  final String? category;

  @override
  String toString() => message;
}
