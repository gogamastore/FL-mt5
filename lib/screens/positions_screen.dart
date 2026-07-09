import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/bot_provider.dart';

class PositionsScreen extends StatelessWidget {
  const PositionsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bot = context.watch<BotProvider>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('Posisi Terbuka'),
        actions: [
          IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: bot.refreshPositions),
        ],
      ),
      body: bot.positions.isEmpty
          ? const Center(child: Text('Tidak ada posisi terbuka'))
          : ListView.builder(
              itemCount: bot.positions.length,
              itemBuilder: (_, i) {
                final p = bot.positions[i];
                final profit = p.profit >= 0;
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  child: ListTile(
                    leading: Icon(
                      p.type == 'BUY' ? Icons.trending_up : Icons.trending_down,
                      color: p.type == 'BUY' ? Colors.greenAccent : Colors.redAccent,
                    ),
                    title: Text('${p.symbol} ${p.type} ${p.volume} lot'),
                    subtitle: Text('Entry ${p.priceOpen} → ${p.priceCurrent}\n'
                        'SL ${p.sl}  ·  TP ${p.tp}'),
                    isThreeLine: true,
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(p.profit.toStringAsFixed(2),
                            style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: profit ? Colors.greenAccent : Colors.redAccent)),
                        TextButton(
                          onPressed: () => _confirmClose(context, bot, p.ticket),
                          child: const Text('TUTUP'),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
    );
  }

  void _confirmClose(BuildContext context, BotProvider bot, int ticket) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Tutup posisi?'),
        content: Text('Posisi #$ticket akan ditutup di harga pasar.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Batal')),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              bot.closePosition(ticket);
            },
            child: const Text('Tutup'),
          ),
        ],
      ),
    );
  }
}
