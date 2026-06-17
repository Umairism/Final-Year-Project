import 'package:flutter/material.dart';

class AuthProvider with ChangeNotifier {
  String? _token;
  bool _isAuthenticated = false;

  bool get isAuthenticated => _isAuthenticated;
  String? get token => _token;

  Future<void> login(String email, String password) async {
    // Implement login logic with ApiService
    _token = "mock_token";
    _isAuthenticated = true;
    notifyListeners();
  }

  void logout() {
    _token = null;
    _isAuthenticated = false;
    notifyListeners();
  }
}
