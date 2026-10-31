import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:healsense/core/theme/app_theme.dart';
import 'package:healsense/providers/vitals_provider.dart';
import 'package:healsense/providers/auth_provider.dart';
import 'package:healsense/views/auth/login_view.dart';
import 'package:healsense/views/dashboard/dashboard_view.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
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
      title: 'HealSense Mobile',
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      home: const AuthGate(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  String? _lastConfiguredToken;

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    if (auth.isLoading) {
      return const Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: Color(0xFF0D9488)),
        ),
      );
    }

    if (!auth.isAuthenticated || auth.patientId == null || auth.token == null) {
      _lastConfiguredToken = null;
      return const LoginView();
    }

    // Configure vitals provider once per session
    if (_lastConfiguredToken != auth.token) {
      _lastConfiguredToken = auth.token;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          context.read<VitalsProvider>().configure(
                patientId: auth.patientId!,
                token: auth.token!,
              );
        }
      });
    }

    return const DashboardView();
  }
}
