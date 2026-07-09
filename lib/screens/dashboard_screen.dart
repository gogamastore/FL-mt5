import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/bot_provider.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bot = context.watch<BotProvider>();
    final acc = bot.account;
    return Scaffold(
      appBar: AppBar(
        title: const Text('MT5 Trading Bot'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: bot.refresh),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: bot.refresh,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Card(
              child: ListTile(
                leading: Icon(
                  bot.connected ? Icons.link : Icons.link_off,
                  color: bot.connected ? Colors.greenAccent : Colors.redAccent,
                ),
                title: Text(bot.connected
                    ? 'Terhubung ke MT5'
                    : 'Tidak terhubung ke backend/MT5'),
                subtitle: Text(bot.running ? 'Bot AKTIF' : 'Bot berhenti'),
              ),
            ),
            const SizedBox(height: 8),
            if (acc != null)
              Row(children: [
                _stat('Balance', acc.balance, acc.currency),
                _stat('Equity', acc.equity, acc.currency),
                _stat('P/L', acc.profit, acc.currency,
                    color: acc.profit >= 0 ? Colors.greenAccent : Colors.redAccent),
              ]),
            const SizedBox(height: 24),
            FilledButton.icon(
              style: FilledButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: bot.running ? Colors.red : Colors.teal,
              ),
              onPressed: bot.toggleBot,
              icon: Icon(bot.running ? Icons.stop : Icons.play_arrow),
              label: Text(bot.running ? 'HENTIKAN BOT' : 'JALANKAN BOT'),
            ),
            const SizedBox(height: 16),
            Text('Posisi terbuka: ${bot.positions.length}   ·   '
                'Sinyal tercatat: ${bot.signals.length}'),
          ],
        ),
      ),
    );
  }

  Widget _stat(String label, double value, String cur, {Color? color}) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Text(label, style: const TextStyle(fontSize: 12)),
            const SizedBox(height: 4),
            Text('${value.toStringAsFixed(2)} $cur',
                style: TextStyle(fontWeight: FontWeight.bold, color: color)),
          ]),
        ),
      ),
    );
  }
}
