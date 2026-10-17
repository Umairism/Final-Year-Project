import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import 'package:healsense/core/theme/app_theme.dart';
import 'package:healsense/models/bp_entry_result.dart';
import 'package:healsense/providers/vitals_provider.dart';

/// Manual blood-pressure entry screen.
///
/// Built for an intermittent upper-arm cuff (Braun ExactFit 1): the user reads
/// SYS / DIA / pulse off the display and types them in. The backend attaches
/// the reading to the newest wearable row within the last 60 minutes.
class BpEntryView extends StatefulWidget {
  const BpEntryView({super.key});

  @override
  State<BpEntryView> createState() => _BpEntryViewState();
}

class _BpEntryViewState extends State<BpEntryView> {
  final _systolicController = TextEditingController();
  final _diastolicController = TextEditingController();
  final _pulseController = TextEditingController();
  final _heartRateController = TextEditingController();
  final _spo2Controller = TextEditingController();
  final _temperatureController = TextEditingController();
  final _noteController = TextEditingController();

  bool _submitting = false;
  bool _showFallbackFields = false;
  String? _errorText;
  bool _errorIsNoAnchor = false;
  BpEntryResult? _result;

  @override
  void dispose() {
    _systolicController.dispose();
    _diastolicController.dispose();
    _pulseController.dispose();
    _heartRateController.dispose();
    _spo2Controller.dispose();
    _temperatureController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  double? _parse(TextEditingController controller) {
    final text = controller.text.trim();
    if (text.isEmpty) return null;
    return double.tryParse(text);
  }

  Future<void> _submit() async {
    final systolic = _parse(_systolicController);
    final diastolic = _parse(_diastolicController);

    if (systolic == null || diastolic == null) {
      setState(() {
        _errorText = 'Enter both a systolic and a diastolic value.';
        _errorIsNoAnchor = false;
      });
      return;
    }
    if (systolic <= diastolic) {
      setState(() {
        _errorText = 'Systolic must be higher than diastolic '
            '(it is the first number on the cuff display).';
        _errorIsNoAnchor = false;
      });
      return;
    }
    if (systolic - diastolic < 10) {
      setState(() {
        _errorText = 'Pulse pressure looks too small — re-check the display.';
        _errorIsNoAnchor = false;
      });
      return;
    }

    setState(() {
      _submitting = true;
      _errorText = null;
      _result = null;
    });

    try {
      final result = await context.read<VitalsProvider>().recordBloodPressure(
            systolic: systolic,
            diastolic: diastolic,
            pulse: _parse(_pulseController),
            heartRate: _parse(_heartRateController),
            spo2: _parse(_spo2Controller),
            temperature: _parse(_temperatureController),
            note: _noteController.text.trim(),
          );

      if (!mounted) return;
      setState(() {
        _result = result;
        _submitting = false;
      });
    } on BpEntryException catch (e) {
      if (!mounted) return;
      setState(() {
        _errorText = e.message;
        _errorIsNoAnchor = e.isNoAnchor;
        _showFallbackFields = e.isNoAnchor ? true : _showFallbackFields;
        _submitting = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorText = 'Could not reach the server: $e';
        _errorIsNoAnchor = false;
        _submitting = false;
      });
    }
  }

  Color _statusColor(String status) {
    switch (status) {
      case 'critical':
        return AppTheme.criticalRed;
      case 'warning':
        return AppTheme.warningOrange;
      default:
        return AppTheme.emeraldGreen;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Log Blood Pressure'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _buildTechniqueCard(),
            const SizedBox(height: 16),
            Text(
              'Reading from the cuff display',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _NumberField(
                    controller: _systolicController,
                    label: 'Systolic',
                    hint: 'e.g. 128',
                    unit: 'mmHg',
                    enabled: !_submitting,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _NumberField(
                    controller: _diastolicController,
                    label: 'Diastolic',
                    hint: 'e.g. 82',
                    unit: 'mmHg',
                    enabled: !_submitting,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _NumberField(
              controller: _pulseController,
              label: 'Pulse (optional)',
              hint: 'e.g. 74',
              unit: 'bpm',
              enabled: !_submitting,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _noteController,
              enabled: !_submitting,
              decoration: const InputDecoration(
                labelText: 'Note (optional)',
                hintText: 'left arm, seated, 5 min rest',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            ExpansionTile(
              key: ValueKey(_showFallbackFields),
              initiallyExpanded: _showFallbackFields,
              tilePadding: EdgeInsets.zero,
              title: const Text('Wrist device not running?'),
              subtitle: const Text(
                'Only needed if no wearable reading exists in the last 60 minutes',
                style: TextStyle(fontSize: 12),
              ),
              children: [
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Column(
                    children: [
                      _NumberField(
                        controller: _heartRateController,
                        label: 'Heart rate',
                        hint: '76',
                        unit: 'bpm',
                        enabled: !_submitting,
                      ),
                      const SizedBox(height: 12),
                      _NumberField(
                        controller: _spo2Controller,
                        label: 'SpO2',
                        hint: '97',
                        unit: '%',
                        enabled: !_submitting,
                      ),
                      const SizedBox(height: 12),
                      _NumberField(
                        controller: _temperatureController,
                        label: 'Body temperature',
                        hint: '36.8',
                        unit: '°C',
                        enabled: !_submitting,
                        allowDecimal: true,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_errorText != null) _buildErrorCard(),
            if (_result != null) _buildResultCard(_result!),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.favorite),
              label: Text(_submitting ? 'Saving…' : 'Save reading'),
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: AppTheme.primaryTeal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTechniqueCard() {
    return Card(
      color: AppTheme.primaryTeal.withValues(alpha: 0.06),
      child: const Padding(
        padding: EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.info_outline, size: 18, color: AppTheme.primaryTeal),
                SizedBox(width: 8),
                Text(
                  'Measure the same way every time',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            SizedBox(height: 8),
            Text(
              '• Sit for 5 minutes before measuring\n'
              '• Back supported, feet flat, arm resting at heart level\n'
              '• Cuff 2–3 cm above the elbow, tube over the brachial artery\n'
              '• Same arm, no talking, no caffeine or smoking for 30 min\n'
              '• Take two readings 1 minute apart and log both',
              style: TextStyle(fontSize: 13, height: 1.45),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade200),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.error_outline, color: Colors.red.shade700, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _errorIsNoAnchor
                  ? '$_errorText\n\nStart the wrist device first, or fill in '
                      'heart rate, SpO₂ and temperature below.'
                  : _errorText!,
              style: TextStyle(color: Colors.red.shade800, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildResultCard(BpEntryResult result) {
    final color = _statusColor(result.status);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: color, width: 2),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  result.reading,
                  style: TextStyle(
                    fontSize: 40,
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
                ),
                const SizedBox(width: 6),
                const Padding(
                  padding: EdgeInsets.only(top: 14),
                  child: Text('mmHg', style: TextStyle(fontSize: 13)),
                ),
                const Spacer(),
                Chip(
                  label: Text(
                    result.categoryLabel,
                    style: const TextStyle(fontSize: 12, color: Colors.white),
                  ),
                  backgroundColor: color,
                ),
              ],
            ),
            if (result.pulse != null)
              Text('Pulse ${result.pulse!.toStringAsFixed(0)} bpm',
                  style: const TextStyle(fontSize: 13)),
            const SizedBox(height: 8),
            Text(result.message, style: const TextStyle(fontSize: 13)),
            if (result.triggeredRules.isNotEmpty) ...[
              const SizedBox(height: 8),
              ...result.triggeredRules.map(
                (rule) => Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.flag, size: 14, color: color),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(rule, style: const TextStyle(fontSize: 12)),
                    ),
                  ],
                ),
              ),
            ],
            if (result.alertId != null) ...[
              const SizedBox(height: 10),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppTheme.criticalRed.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Text(
                  'A critical alert was raised for the care team.',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
            ],
            const SizedBox(height: 8),
            Text(
              result.attached
                  ? 'Attached to the latest wrist-device reading.'
                  : 'Stored as a standalone reading.',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
            ),
          ],
        ),
      ),
    );
  }
}

class _NumberField extends StatelessWidget {
  const _NumberField({
    required this.controller,
    required this.label,
    required this.hint,
    required this.unit,
    this.enabled = true,
    this.allowDecimal = false,
  });

  final TextEditingController controller;
  final String label;
  final String hint;
  final String unit;
  final bool enabled;
  final bool allowDecimal;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      enabled: enabled,
      keyboardType: TextInputType.numberWithOptions(decimal: allowDecimal),
      inputFormatters: [
        FilteringTextInputFormatter.allow(
          allowDecimal ? RegExp(r'[0-9.]') : RegExp(r'[0-9]'),
        ),
      ],
      decoration: InputDecoration(
        labelText: label,
        hintText: hint,
        suffixText: unit,
        border: const OutlineInputBorder(),
      ),
    );
  }
}
