import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';

class RealtimeService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  bool get isConnected => _channel != null;

  Future<void> connect({
    required String wsUrl,
    required void Function(Map<String, dynamic>) onEvent,
    void Function(Object)? onError,
    void Function()? onDone,
  }) async {
    await disconnect();

    try {
      final uri = Uri.parse(wsUrl);
      final channel = WebSocketChannel.connect(uri);
      _channel = channel;

      _subscription = channel.stream.listen(
        (data) {
          try {
            final decoded = jsonDecode(data.toString());
            if (decoded is Map<String, dynamic>) {
              onEvent(decoded);
            }
          } catch (_) {
            // Ignore malformed frames
          }
        },
        onError: (error) {
          onError?.call(error);
        },
        onDone: () {
          onDone?.call();
        },
        cancelOnError: true,
      );
    } catch (e) {
      onError?.call(e);
      rethrow;
    }
  }

  void sendPing() {
    if (_channel != null) {
      try {
        _channel!.sink.add('ping');
      } catch (_) {
        // Ignore sink errors if closing
      }
    }
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    _subscription = null;
    try {
      await _channel?.sink.close();
    } catch (_) {}
    _channel = null;
  }
}
