import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/bot_provider.dart';

/// Riwayat sinyal + alasan lengkap kenapa bot entry (atau tidak).
class SignalsScreen extends StatelessWidget {
  const SignalsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bot = context.watch<BotProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Sinyal & Alasan Entry')),
      body: bot.signals.isEmpty
          ? const Center(child: Text('Belum ada sinyal'))
          : ListView.builder(
              itemCount: bot.signals.length,
              itemBuilder: (_, i) {
                final s = bot.signals[i];
                final isBuy = s.direction == 'BUY';
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  child: ExpansionTile(
                    leading: CircleAvatar(
                      backgroundColor: s.executed
                          ? (isBuy ? Colors.green : Colors.red)
                          : Colors.grey,
                      child: Text('${s.score}',
                          style: const TextStyle(fontSize: 12)),
                    ),
                    title: Text('${s.symbol}  ${s.direction ?? "-"}'
                        '${s.executed ? "  ✓ DIEKSEKUSI" : ""}'),
                    subtitle: Text(s.time.replaceFirst('T', ' ').split('.').first),
                    children: s.reasons
                        .map((r) => ListTile(
                            dense: true,
                            leading: const Icon(Icons.check, size: 16),
                            title: Text(r, style: const TextStyle(fontSize: 13))))
                        .toList(),
                  ),
                );
              },
            ),
    );
  }
}
