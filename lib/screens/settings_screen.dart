import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/bot_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final bot = context.watch<BotProvider>();
    final s = bot.settings;
    if (s == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Pengaturan Bot')),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const CircularProgressIndicator(),
              const SizedBox(height: 16),
              const Text('Memuat pengaturan dari server...'),
              const SizedBox(height: 8),
              TextButton(onPressed: bot.refresh, child: const Text('Coba lagi')),
            ],
          ),
        ),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('Pengaturan Bot')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Simbol aktif', style: Theme.of(context).textTheme.titleMedium),
          Wrap(
            spacing: 8,
            children: s.symbols
                .map((sym) => Chip(
                      label: Text(sym),
                      onDeleted: () => bot.editSettings((st) => st.symbols.remove(sym)),
                    ))
                .toList(),
          ),
          TextField(
            decoration: const InputDecoration(
                labelText: 'Tambah simbol (mis. XAUUSD.Z)',
                suffixIcon: Icon(Icons.add)),
            onSubmitted: (v) {
              final sym = v.trim().toUpperCase();
              if (sym.isNotEmpty) {
                bot.editSettings((st) => st.symbols.add(sym));
              }
            },
          ),
          const SizedBox(height: 16),
          _slider(bot, 'Skor minimum entry: ${s.minScore}',
              s.minScore.toDouble(), 50, 100,
              (st, v) => st.minScore = v.round()),
          _slider(bot, 'Risiko per trade: ${s.riskPercent.toStringAsFixed(1)}%',
              s.riskPercent, 0.25, 5, (st, v) => st.riskPercent = v),
          _slider(bot, 'SL = ${s.slAtrMult.toStringAsFixed(1)} × ATR',
              s.slAtrMult, 0.5, 4, (st, v) => st.slAtrMult = v),
          _slider(bot, 'TP = ${s.tpAtrMult.toStringAsFixed(1)} × ATR',
              s.tpAtrMult, 0.5, 6, (st, v) => st.tpAtrMult = v),
          _slider(bot, 'Maks. posisi bersamaan: ${s.maxOpenPositions}',
              s.maxOpenPositions.toDouble(), 1, 10,
              (st, v) => st.maxOpenPositions = v.round()),
          SwitchListTile(
            title: const Text('Trailing stop'),
            value: s.trailingEnabled,
            onChanged: (v) => bot.editSettings((st) => st.trailingEnabled = v),
          ),
          SwitchListTile(
            title: const Text('Filter berita high-impact'),
            value: s.newsFilterEnabled,
            onChanged: (v) => bot.editSettings((st) => st.newsFilterEnabled = v),
          ),
          const Divider(height: 32),
          Text('Mode Scalping', style: Theme.of(context).textTheme.titleMedium),
          SwitchListTile(
            title: const Text('Aktifkan mode scalping'),
            subtitle: const Text(
                'Saat aktif, mode utama (swing) NONAKTIF. Murni support/resisten + '
                'momentum RSI — tanpa filter berita & multi-timeframe. Entry di support '
                'untuk BUY, resisten untuk SELL.'),
            value: s.scalpEnabled,
            onChanged: (v) => bot.editSettings((st) => st.scalpEnabled = v),
          ),
          if (s.scalpEnabled) ...[
            _entryPreview(context, s),
            _slider(bot, 'Skor minimum entry (base): ${s.scalpBaseScore}',
                s.scalpBaseScore.toDouble(), 40, 70,
                (st, v) => st.scalpBaseScore = v.round()),
            _slider(bot, 'Tiap +${s.scalpScoreStep} skor → +1 entry',
                s.scalpScoreStep.toDouble(), 1, 10,
                (st, v) => st.scalpScoreStep = v.round()),
            _slider(bot, 'Maks. entry per keputusan: ${s.scalpMaxEntries}',
                s.scalpMaxEntries.toDouble(), 1, 6,
                (st, v) => st.scalpMaxEntries = v.round()),
            _slider(bot, 'Maks. posisi scalp bersamaan per simbol: ${s.scalpMaxPerSymbol}',
                s.scalpMaxPerSymbol.toDouble(), 1, 6,
                (st, v) => st.scalpMaxPerSymbol = v.round()),
            _slider(bot,
                'Risiko per entry scalp: ${s.scalpRiskPercent.toStringAsFixed(2)}%',
                s.scalpRiskPercent, 0.1, 2,
                (st, v) => st.scalpRiskPercent = v),
            _slider(bot, 'Tutup paksa setelah: ${s.scalpMaxHoldMin} menit',
                s.scalpMaxHoldMin.toDouble(), 15, 240,
                (st, v) => st.scalpMaxHoldMin = v.round()),
            const SizedBox(height: 8),
            Text('Penyaring kualitas',
                style: Theme.of(context).textTheme.titleSmall),
            _slider(
                bot,
                s.scalpMaxEfficiency <= 0
                    ? 'Filter regime (ranging): nonaktif'
                    : 'Filter regime: skip jika trending ≥ ${s.scalpMaxEfficiency.toStringAsFixed(2)} (0=off)',
                s.scalpMaxEfficiency, 0, 1,
                (st, v) => st.scalpMaxEfficiency = v),
            _slider(
                bot,
                s.scalpMaxSpreadRatio <= 0
                    ? 'Batas spread: nonaktif'
                    : 'Batas spread: maks ${(s.scalpMaxSpreadRatio * 100).round()}% dari jarak TP (0=off)',
                s.scalpMaxSpreadRatio, 0, 1,
                (st, v) => st.scalpMaxSpreadRatio = v),
            _slider(
                bot,
                s.scalpCooldownMin <= 0
                    ? 'Cooldown setelah rugi: nonaktif'
                    : 'Cooldown setelah scalp rugi: ${s.scalpCooldownMin} menit (0=off)',
                s.scalpCooldownMin.toDouble(), 0, 120,
                (st, v) => st.scalpCooldownMin = v.round()),
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text(
                'Catatan: filter berita, skor minimum swing, dan trailing stop '
                'tidak berlaku selama mode scalping aktif. Regime & spread menyaring '
                'entry berkualitas rendah; konfirmasi candle, kekuatan level, dan volume '
                'menambah skor otomatis.',
                style: TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
              ),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: () async {
              await bot.saveSettings();
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Pengaturan tersimpan')));
              }
            },
            icon: const Icon(Icons.save),
            label: const Text('SIMPAN'),
          ),
        ],
      ),
    );
  }

  /// Pratinjau berapa entry untuk beberapa tingkat skor, mengikuti setting saat ini.
  Widget _entryPreview(BuildContext context, dynamic s) {
    int entries(int score) {
      if (score < s.scalpBaseScore) return 0;
      final n = 1 + (score - s.scalpBaseScore) ~/ (s.scalpScoreStep as int);
      return n.clamp(0, s.scalpMaxEntries as int);
    }

    final samples = <int>[
      s.scalpBaseScore,
      s.scalpBaseScore + s.scalpScoreStep,
      s.scalpBaseScore + s.scalpScoreStep * 2,
      s.scalpBaseScore + s.scalpScoreStep * 5,
    ];
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Contoh: kekuatan sinyal → jumlah entry',
                style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: samples
                  .toSet()
                  .map((sc) => Chip(
                        visualDensity: VisualDensity.compact,
                        label: Text('$sc → ${entries(sc)}×'),
                      ))
                  .toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _slider(BotProvider bot, String label, double value, double min,
      double max, void Function(dynamic st, double v) onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          onChanged: (v) => bot.editSettings((st) => onChanged(st, v)),
        ),
      ],
    );
  }
}
