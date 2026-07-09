import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import '../models/models.dart';

class ApiService {
  final _headers = {
    'Content-Type': 'application/json',
    'X-API-Key': AppConfig.apiKey,
  };

  Uri _u(String path) => Uri.parse('${AppConfig.baseUrl}$path');

  Future<Map<String, dynamic>> status() async {
    final r = await http.get(_u('/status'), headers: _headers);
    return jsonDecode(r.body);
  }

  Future<void> startBot() async =>
      http.post(_u('/bot/start'), headers: _headers);

  Future<void> stopBot() async =>
      http.post(_u('/bot/stop'), headers: _headers);

  Future<List<Position>> positions() async {
    final r = await http.get(_u('/positions'), headers: _headers);
    return (jsonDecode(r.body) as List)
        .map((e) => Position.fromJson(e))
        .toList();
  }

  Future<void> closePosition(int ticket) async =>
      http.post(_u('/positions/$ticket/close'), headers: _headers);

  Future<List<Signal>> signals() async {
    final r = await http.get(_u('/signals'), headers: _headers);
    return (jsonDecode(r.body) as List)
        .map((e) => Signal.fromJson(e))
        .toList();
  }

  Future<List<TradeHistory>> history(
      {DateTime? dateFrom, DateTime? dateTo}) async {
    String d(DateTime x) =>
        '${x.year}-${x.month.toString().padLeft(2, '0')}-${x.day.toString().padLeft(2, '0')}';
    final params = <String, String>{};
    if (dateFrom != null) params['date_from'] = d(dateFrom);
    if (dateTo != null) params['date_to'] = d(dateTo);
    final uri = Uri.parse('${AppConfig.baseUrl}/history')
        .replace(queryParameters: params.isEmpty ? null : params);
    final r = await http.get(uri, headers: _headers);
    return (jsonDecode(r.body) as List)
        .map((e) => TradeHistory.fromJson(e))
        .toList();
  }

  Future<Map<String, dynamic>> getSettingsRaw() async {
    final r = await http.get(_u('/settings'), headers: _headers);
    return jsonDecode(r.body);
  }

  Future<void> updateSettings(Map<String, dynamic> body) async => http.put(
      _u('/settings'), headers: _headers, body: jsonEncode(body));
}