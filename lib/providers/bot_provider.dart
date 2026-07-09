import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';

class BotProvider extends ChangeNotifier {
  final api = ApiService();
  final ws = WsService();

  bool running = false;
  bool connected = false;
  AccountInfo? account;
  List<Position> positions = [];
  List<Signal> signals = [];
  Map<String, dynamic> rawSettings = {};
  BotSettings? settings;
  Timer? _poll;

  BotProvider() {
    ws.connect();
    ws.events.listen(_onEvent);
    refresh();
    _poll = Timer.periodic(const Duration(seconds: 10), (_) => refresh());
  }

  void _onEvent(Map<String, dynamic> msg) {
    switch (msg['event']) {
      case 'account':
        account = AccountInfo.fromJson(msg['data']);
        break;
      case 'signal':
        signals.insert(0, Signal.fromJson(msg['data']));
        if (signals.length > 200) signals.removeLast();
        break;
      case 'trade_opened':
      case 'trailing':
        refreshPositions();
        break;
    }
    notifyListeners();
  }

  Future<void> refresh() async {
    try {
      final s = await api.status();
      running = s['running'] ?? false;
      connected = s['mt5_connected'] ?? false;
      if (s['account'] != null && (s['account'] as Map).isNotEmpty) {
        account = AccountInfo.fromJson(s['account']);
      }
      positions = await api.positions();
      signals = await api.signals();
      rawSettings = await api.getSettingsRaw();
      settings = BotSettings.fromJson(rawSettings);
    } catch (_) {
      connected = false;
    }
    notifyListeners();
  }

  Future<void> refreshPositions() async {
    try {
      positions = await api.positions();
      notifyListeners();
    } catch (_) {}
  }

  Future<void> toggleBot() async {
    running ? await api.stopBot() : await api.startBot();
    await refresh();
  }

  Future<void> closePosition(int ticket) async {
    await api.closePosition(ticket);
    await refreshPositions();
  }


  /// Ubah pengaturan lokal lalu beri tahu UI (dipanggil dari layar Settings).
  void editSettings(void Function(BotSettings s) edit) {
    if (settings == null) return;
    edit(settings!);
    notifyListeners();
  }

  Future<void> saveSettings() async {
    if (settings == null) return;
    await api.updateSettings(settings!.toJson(rawSettings));
    await refresh();
  }

  @override
  void dispose() {
    _poll?.cancel();
    ws.dispose();
    super.dispose();
  }
}
