import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';

/// WebSocket realtime dengan auto-reconnect.
class WsService {
  final _controller = StreamController<Map<String, dynamic>>.broadcast();
  WebSocketChannel? _channel;
  bool _closed = false;

  Stream<Map<String, dynamic>> get events => _controller.stream;

  void connect() {
    if (_closed) return;
    try {
      _channel = WebSocketChannel.connect(Uri.parse(AppConfig.wsUrl));
      _channel!.stream.listen(
        (msg) => _controller.add(jsonDecode(msg)),
        onDone: _scheduleReconnect,
        onError: (_) => _scheduleReconnect(),
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_closed) return;
    Future.delayed(const Duration(seconds: 5), connect);
  }

  void dispose() {
    _closed = true;
    _channel?.sink.close();
    _controller.close();
  }
}
