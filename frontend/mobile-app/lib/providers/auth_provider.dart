import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:healsense/services/api_service.dart';

class AuthProvider with ChangeNotifier {
  AuthProvider({
    ApiService? apiService,
    FlutterSecureStorage? secureStorage,
  })  : _apiService = apiService ?? ApiService(),
        _secureStorage = secureStorage ?? const FlutterSecureStorage() {
    tryRestoreSession();
  }

  static const _tokenKey = 'healsense_auth_token';

  final ApiService _apiService;
  final FlutterSecureStorage _secureStorage;
  String? _token;
  String? _patientId;
  String? _email;
  String? _fullName;
  bool _isAuthenticated = false;
  bool _isLoading = true;
  String? _error;

  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;
  String? get token => _token;
  String? get patientId => _patientId;
  String? get email => _email;
  String? get fullName => _fullName;
  String? get error => _error;
  ApiService get apiService => _apiService;

  Future<void> tryRestoreSession() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final storedToken = await _secureStorage.read(key: _tokenKey);

      if (storedToken != null && storedToken.isNotEmpty) {
        _apiService.setAuthToken(storedToken);
        final me = await _apiService.getMe();
        _token = storedToken;
        _patientId = me['patient_id']?.toString();
        _email = me['email']?.toString();
        _fullName = me['full_name']?.toString();
        _isAuthenticated = true;
      }
    } catch (_) {
      // Stored token expired or invalid; reset state cleanly
      await logout();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final authData = await _apiService.login(email: email, password: password);
      final accessToken = authData['access_token']?.toString();

      if (accessToken == null || accessToken.isEmpty) {
        throw Exception('Server did not return an access token.');
      }

      _apiService.setAuthToken(accessToken);
      final me = await _apiService.getMe();

      final pid = me['patient_id']?.toString();
      if (pid == null || pid.isEmpty) {
        throw Exception('Account is not linked to a patient profile.');
      }

      _token = accessToken;
      _patientId = pid;
      _email = me['email']?.toString();
      _fullName = me['full_name']?.toString();
      _isAuthenticated = true;

      await _secureStorage.write(key: _tokenKey, value: accessToken);

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString().replaceFirst('Exception: ', '');
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    _patientId = null;
    _email = null;
    _fullName = null;
    _isAuthenticated = false;
    _apiService.setAuthToken(null);

    try {
      await _secureStorage.delete(key: _tokenKey);
    } catch (_) {}

    notifyListeners();
  }
}
