import 'dart:async';
import 'dart:convert';
import 'dart:io';

class RealtimeService {
  WebSocket? _socket;
  StreamSubscription? _subscription;

  bool get isConnected => _socket != null;

  Future<void> connect({
    required String wsUrl,
    required void Function(Map<String, dynamic>) onEvent,
    void Function(Object)? onError,
    void Function()? onDone,
  }) async {
    await disconnect();

    final socket = await WebSocket.connect(wsUrl);
    _socket = socket;

    _subscription = socket.listen(
      (data) {
        try {
          final decoded = jsonDecode(data as String);
          if (decoded is Map<String, dynamic>) {
            onEvent(decoded);
          }
        } catch (_) {
          // Ignore invalid frames
        }
      },
      onError: (error) => onError?.call(error),
      onDone: () => onDone?.call(),
      cancelOnError: true,
    );
  }

  Future<void> sendPing() async {
    if (_socket != null) {
      _socket!.add('ping');
    }
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    _subscription = null;
    await _socket?.close();
    _socket = null;
  }
}
