import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:healsense/providers/auth_provider.dart';
import 'package:healsense/providers/vitals_provider.dart';
import 'package:healsense/views/bp/bp_entry_view.dart';
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
                          subtitle: Text('Temp ${vital.temperature.toStringAsFixed(1)}°C  BP ${vital.bloodPressure}  RR ${vital.respiratoryRate.toStringAsFixed(0)}'),
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
    final authProvider = context.watch<AuthProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text(authProvider.fullName != null && authProvider.fullName!.isNotEmpty
            ? '${authProvider.fullName} - Dashboard'
            : 'HealSense Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.monitor_heart),
            tooltip: 'Log blood pressure',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const BpEntryView()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'View history',
            onPressed: () => _showHistoryDialog(context),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: () async {
              context.read<VitalsProvider>().clear();
              await context.read<AuthProvider>().logout();
            },
          ),
        ],
      ),
      body: Consumer<VitalsProvider>(
        builder: (context, vitalsProvider, child) {
          final vitals = vitalsProvider.currentVitals;

          if (vitalsProvider.isLoading && vitals == null) {
            return const Center(child: CircularProgressIndicator());
          }

          if (vitals == null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.sensors_outlined, size: 64, color: Colors.grey),
                    const SizedBox(height: 16),
                    const Text(
                      'Waiting for Telemetry',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Connect ESP32 hardware to stream live vitals for patient ${vitalsProvider.patientId ?? authProvider.patientId ?? ""}.',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton.icon(
                      onPressed: () {
                        vitalsProvider.refreshLatestVitals();
                        vitalsProvider.refreshHistory();
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Refresh'),
                    ),
                  ],
                ),
              ),
            );
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
                        avatar: const Icon(Icons.badge, size: 18),
                        label: Text('Patient: ${vitalsProvider.patientId ?? authProvider.patientId ?? "N/A"}'),
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
                        unit: vitals.bloodPressure == 'Not measured' ? '' : 'mmHg',
                        icon: Icons.speed,
                        color: AppTheme.primaryTeal,
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Recent History',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      TextButton.icon(
                        icon: const Icon(Icons.open_in_new, size: 16),
                        label: const Text('View Full'),
                        onPressed: () => _showHistoryDialog(context),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  if (vitalsProvider.history.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24.0),
                      child: Center(
                        child: Text('No historical readings yet.'),
                      ),
                    )
                  else
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: vitalsProvider.history.length > 5 ? 5 : vitalsProvider.history.length,
                      itemBuilder: (context, index) {
                        final vital = vitalsProvider.history[index];
                        final time =
                            '${vital.timestamp.hour.toString().padLeft(2, '0')}:${vital.timestamp.minute.toString().padLeft(2, '0')}:${vital.timestamp.second.toString().padLeft(2, '0')}';
                        return Card(
                          margin: const EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: Colors.teal.shade50,
                              child: const Icon(Icons.monitor_heart, color: Colors.teal),
                            ),
                            title: Text('HR ${vital.heartRate.toStringAsFixed(0)} bpm  |  SpO2 ${vital.spo2.toStringAsFixed(0)}%'),
                            subtitle: Text('Temp ${vital.temperature.toStringAsFixed(1)}°C  |  BP: ${vital.bloodPressure}'),
                            trailing: Text(time, style: const TextStyle(color: Colors.grey, fontSize: 12)),
                          ),
                        );
                      },
                    ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red.shade700,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      icon: const Icon(Icons.warning_amber_rounded),
                      label: const Text('TRIGGER EMERGENCY ALERT', style: TextStyle(fontWeight: FontWeight.bold)),
                      onPressed: () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('Trigger Emergency Alert?'),
                            content: const Text(
                              'This will notify emergency contacts and log a priority alert event.',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: const Text('CANCEL'),
                              ),
                              ElevatedButton(
                                style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                                onPressed: () => Navigator.pop(ctx, true),
                                child: const Text('CONFIRM'),
                              ),
                            ],
                          ),
                        );

                        if (confirm == true && context.mounted) {
                          try {
                            await vitalsProvider.triggerEmergency();
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Emergency alert sent successfully.'),
                                  backgroundColor: Colors.red,
                                ),
                              );
                            }
                          } catch (e) {
                            if (context.mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Failed to trigger emergency: $e')),
                              );
                            }
                          }
                        }
                      },
                    ),
                  ),
                  const SizedBox(height: 32),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
