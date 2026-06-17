import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:healsense/core/theme/app_theme.dart';
import 'package:healsense/providers/vitals_provider.dart';
import 'package:healsense/providers/auth_provider.dart';
import 'package:healsense/views/dashboard/dashboard_view.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => VitalsProvider()),
      ],
      child: const HealSenseApp(),
    ),
  );
}

class HealSenseApp extends StatelessWidget {
  const HealSenseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'HealSense',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      home: const DashboardView(),
      debugShowCheckedModeBanner: false,
    );
  }
}
