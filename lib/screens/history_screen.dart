import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../models/models.dart';
import '../providers/bot_provider.dart';

/// Riwayat posisi tertutup bot, dengan filter hari dan rentang tanggal.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<TradeHistory> _trades = [];
  bool _loading = true;
  String _filterLabel = '7 hari terakhir';
  DateTime? _from;
  DateTime? _to;

  @override
  void initState() {
    super.initState();
    _applyQuickFilter(7, '7 hari terakhir');
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final api = context.read<BotProvider>().api;
      _trades = await api.history(dateFrom: _from, dateTo: _to);
    } catch (_) {
      _trades = [];
    }
    if (mounted) setState(() => _loading = false);
  }

  void _applyQuickFilter(int days, String label) {
    final now = DateTime.now();
    _from = days == 0
        ? DateTime(now.year, now.month, now.day)
        : now.subtract(Duration(days: days));
    _to = now;
    _filterLabel = label;
    _load();
  }

  Future<void> _pickRange() async {
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2024),
      lastDate: DateTime.now(),
      initialDateRange: _from != null && _to != null
          ? DateTimeRange(start: _from!, end: _to!)
          : null,
    );
    if (range != null) {
      final df = DateFormat('d MMM');
      setState(() {
        _from = range.start;
        _to = range.end;
        _filterLabel = '${df.format(range.start)} – ${df.format(range.end)}';
      });
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final totalProfit = _trades.fold<double>(0, (a, t) => a + t.profit);
    final wins = _trades.where((t) => t.profit > 0).length;
    final dt = DateFormat('dd/MM/yyyy HH:mm');

    return Scaffold(
      appBar: AppBar(
        title: const Text('History Trading'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: Column(
        children: [
          // Filter hari & tanggal
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(children: [
              _chip('Hari ini', () => _applyQuickFilter(0, 'Hari ini')),
              _chip('Kemarin', () {
                final now = DateTime.now();
                setState(() {
                  _from = DateTime(now.year, now.month, now.day - 1);
                  _to = DateTime(now.year, now.month, now.day - 1);
                  _filterLabel = 'Kemarin';
                });
                _load();
              }),
              _chip('7 hari', () => _applyQuickFilter(7, '7 hari terakhir')),
              _chip('30 hari', () => _applyQuickFilter(30, '30 hari terakhir')),
              ActionChip(
                avatar: const Icon(Icons.calendar_month, size: 18),
                label: const Text('Pilih tanggal'),
                onPressed: _pickRange,
              ),
            ]),
          ),
          // Ringkasan
          Card(
            margin: const EdgeInsets.symmetric(horizontal: 12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  Text(_filterLabel,
                      style: const TextStyle(fontWeight: FontWeight.bold)),
                  Text('${_trades.length} trade  ·  $wins win'),
                  Text(
                    totalProfit.toStringAsFixed(2),
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: totalProfit >= 0
                            ? Colors.greenAccent
                            : Colors.redAccent),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _trades.isEmpty
                    ? const Center(child: Text('Tidak ada trade pada periode ini'))
                    : RefreshIndicator(
                        onRefresh: _load,
                        child: ListView.builder(
                          itemCount: _trades.length,
                          itemBuilder: (_, i) {
                            final t = _trades[i];
                            final win = t.profit >= 0;
                            return Card(
                              margin: const EdgeInsets.symmetric(
                                  horizontal: 12, vertical: 4),
                              child: ListTile(
                                leading: Icon(
                                  t.type == 'BUY'
                                      ? Icons.trending_up
                                      : Icons.trending_down,
                                  color: t.type == 'BUY'
                                      ? Colors.greenAccent
                                      : Colors.redAccent,
                                ),
                                title: Text(
                                    '${t.symbol} ${t.type} ${t.volume} lot'
                                    '${t.isScalp ? "  ·  SCALP" : ""}'),
                                subtitle: Text(
                                    '${t.openPrice} → ${t.closePrice}\n'
                                    'Tutup: ${dt.format(t.closedAt)}'),
                                isThreeLine: true,
                                trailing: Text(
                                  t.profit.toStringAsFixed(2),
                                  style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 15,
                                      color: win
                                          ? Colors.greenAccent
                                          : Colors.redAccent),
                                ),
                              ),
                            );
                          },
                        ),
                      ),
          ),
        ],
      ),
    );
  }

  Widget _chip(String label, VoidCallback onTap) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ActionChip(label: Text(label), onPressed: onTap),
    );
  }
}