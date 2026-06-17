import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:healsense/providers/vitals_provider.dart';
import 'package:healsense/widgets/vital_card.dart';
import 'package:healsense/core/theme/app_theme.dart';

class DashboardView extends StatelessWidget {
  const DashboardView({super.key});

  Future<void> _showHistoryDialog(BuildContext context) async {
    final vitalsProvider = context.read<VitalsProvider>();
    await vitalsProvider.refreshHistory(minutes: 120);

    if (!context.mounted) return;

    final history = vitalsProvider.history;
    final error = vitalsProvider.error;

    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Vital History (Last 120 min)'),
        content: SizedBox(
          width: 360,
          child: error != null
              ? Text(error)
              : history.isEmpty
                  ? const Text('No history data found.')
                  : ListView.builder(
                      shrinkWrap: true,
                      itemCount: history.length > 10 ? 10 : history.length,
                      itemBuilder: (context, index) {
                        final vital = history[index];
                        final time =
                            '${vital.timestamp.hour.toString().padLeft(2, '0')}:${vital.timestamp.minute.toString().padLeft(2, '0')}';
                        return ListTile(
                          dense: true,
                          title: Text('HR ${vital.heartRate.toStringAsFixed(0)} | SpO2 ${vital.spo2.toStringAsFixed(0)}%'),
                          subtitle: Text('Temp ${vital.temperature.toStringAsFixed(1)}C  BP ${vital.bloodPressure}  RR ${vital.respiratoryRate.toStringAsFixed(0)}'),
                          trailing: Text(time),
                        );
                      },
                    ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text('CLOSE'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('HealSense Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () {
              // Navigate to profile
            },
          ),
        ],
      ),
      body: Consumer<VitalsProvider>(
        builder: (context, vitalsProvider, child) {
          final vitals = vitalsProvider.currentVitals;

          if (vitals == null) {
            return const Center(child: CircularProgressIndicator());
          }

          return RefreshIndicator(
            onRefresh: () async {
              await vitalsProvider.refreshLatestVitals();
              await vitalsProvider.refreshHistory();
            },
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (vitalsProvider.error != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12.0),
                      child: Material(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                        child: Padding(
                          padding: const EdgeInsets.all(10.0),
                          child: Text(
                            vitalsProvider.error!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        ),
                      ),
                    ),
                  Text(
                    'Real-time Vitals',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      Chip(
                        avatar: Icon(
                          vitalsProvider.isRealtimeConnected ? Icons.wifi : Icons.sync,
                          size: 18,
                          color: vitalsProvider.isRealtimeConnected ? Colors.green : Colors.orange,
                        ),
                        label: Text(
                          vitalsProvider.isRealtimeConnected
                              ? 'Realtime stream active'
                              : 'Polling fallback active',
                        ),
                      ),
                      Chip(
                        avatar: const Icon(Icons.memory, size: 18),
                        label: Text(vitalsProvider.deviceId ?? 'IoT device pending'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    children: [
                      VitalCard(
                        label: 'Heart Rate',
                        value: vitals.heartRate.toStringAsFixed(0),
                        unit: 'bpm',
                        icon: Icons.favorite,
                        color: Colors.red,
                      ),
                      VitalCard(
                        label: 'SpO2',
                        value: vitals.spo2.toStringAsFixed(0),
                        unit: '%',
                        icon: Icons.bloodtype,
                        color: Colors.blue,
                      ),
                      VitalCard(
                        label: 'Temperature',
                        value: vitals.temperature.toStringAsFixed(1),
                        unit: '°C',
                        icon: Icons.thermostat,
                        color: Colors.orange,
                      ),
                      VitalCard(
                        label: 'Blood Pressure',
                        value: vitals.bloodPressure,
                        unit: 'mmHg',
                        icon: Icons.speed,
                        color: Colors.purple,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          const ListTile(
                            leading: Icon(Icons.history),
                            title: Text('Vital History'),
                            subtitle: Text('View trends over the last 24 hours'),
                          ),
                          ElevatedButton(
                            onPressed: () => _showHistoryDialog(context),
                            child: const Text('View Charts'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showEmergencyDialog(context),
        label: const Text('EMERGENCY'),
        icon: const Icon(Icons.warning),
        backgroundColor: AppTheme.criticalRed,
      ),
    );
  }

  void _showEmergencyDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Trigger Emergency?'),
        content: const Text('This will alert your emergency contacts and medical services.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('CANCEL'),
          ),
          ElevatedButton(
            onPressed: () async {
              final navigator = Navigator.of(context);
              final messenger = ScaffoldMessenger.of(context);
              final vitalsProvider = context.read<VitalsProvider>();

              Navigator.pop(context);

              try {
                await vitalsProvider.triggerEmergency();
                if (navigator.context.mounted) {
                  messenger.showSnackBar(
                    const SnackBar(content: Text('Emergency Alert Sent!')),
                  );
                }
              } catch (_) {
                if (navigator.context.mounted) {
                  messenger.showSnackBar(
                    SnackBar(content: Text(vitalsProvider.error ?? 'Failed to send emergency alert')),
                  );
                }
              }
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.criticalRed),
            child: const Text('CONFIRM'),
          ),
        ],
      ),
    );
  }
}
