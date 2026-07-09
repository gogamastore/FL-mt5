/// Model data yang dikirim backend.
class AccountInfo {
  final double balance, equity, profit, freeMargin;
  final String currency;
  AccountInfo({required this.balance, required this.equity,
      required this.profit, required this.freeMargin, required this.currency});
  factory AccountInfo.fromJson(Map<String, dynamic> j) => AccountInfo(
        balance: (j['balance'] ?? 0).toDouble(),
        equity: (j['equity'] ?? 0).toDouble(),
        profit: (j['profit'] ?? 0).toDouble(),
        freeMargin: (j['free_margin'] ?? 0).toDouble(),
        currency: j['currency'] ?? 'USD',
      );
}

class Position {
  final int ticket;
  final String symbol, type;
  final double volume, priceOpen, priceCurrent, sl, tp, profit;
  Position({required this.ticket, required this.symbol, required this.type,
      required this.volume, required this.priceOpen, required this.priceCurrent,
      required this.sl, required this.tp, required this.profit});
  factory Position.fromJson(Map<String, dynamic> j) => Position(
        ticket: j['ticket'],
        symbol: j['symbol'],
        type: j['type'],
        volume: (j['volume'] ?? 0).toDouble(),
        priceOpen: (j['price_open'] ?? 0).toDouble(),
        priceCurrent: (j['price_current'] ?? 0).toDouble(),
        sl: (j['sl'] ?? 0).toDouble(),
        tp: (j['tp'] ?? 0).toDouble(),
        profit: (j['profit'] ?? 0).toDouble(),
      );
}

class Signal {
  final String symbol;
  final String? direction;
  final int score;
  final List<String> reasons;
  final bool executed;
  final String time;
  Signal({required this.symbol, this.direction, required this.score,
      required this.reasons, required this.executed, required this.time});
  factory Signal.fromJson(Map<String, dynamic> j) => Signal(
        symbol: j['symbol'] ?? '',
        direction: j['direction'],
        score: j['score'] ?? 0,
        reasons: List<String>.from(j['reasons'] ?? []),
        executed: j['executed'] ?? false,
        time: j['time'] ?? '',
      );
}

class BotSettings {
  List<String> symbols;
  int minScore;
  double riskPercent, slAtrMult, tpAtrMult;
  bool trailingEnabled, newsFilterEnabled;
  int maxOpenPositions;
  bool scalpEnabled;
  int scalpMaxPerSymbol, scalpMaxHoldMin;
  int scalpBaseScore, scalpScoreStep, scalpMaxEntries, scalpCooldownMin;
  double scalpRiskPercent, scalpMaxEfficiency, scalpMaxSpreadRatio;
  BotSettings({required this.symbols, required this.minScore,
      required this.riskPercent, required this.slAtrMult,
      required this.tpAtrMult, required this.trailingEnabled,
      required this.newsFilterEnabled, required this.maxOpenPositions,
      required this.scalpEnabled, required this.scalpMaxPerSymbol,
      required this.scalpMaxHoldMin, required this.scalpRiskPercent,
      required this.scalpBaseScore, required this.scalpScoreStep,
      required this.scalpMaxEntries, required this.scalpMaxEfficiency,
      required this.scalpMaxSpreadRatio, required this.scalpCooldownMin});
  factory BotSettings.fromJson(Map<String, dynamic> j) => BotSettings(
        symbols: List<String>.from(j['symbols'] ?? []),
        minScore: j['min_score'] ?? 70,
        riskPercent: (j['risk_percent'] ?? 1.0).toDouble(),
        slAtrMult: (j['sl_atr_mult'] ?? 1.5).toDouble(),
        tpAtrMult: (j['tp_atr_mult'] ?? 2.5).toDouble(),
        trailingEnabled: j['trailing_enabled'] ?? true,
        newsFilterEnabled: j['news_filter_enabled'] ?? true,
        maxOpenPositions: j['max_open_positions'] ?? 3,
        scalpEnabled: j['scalp_enabled'] ?? false,
        scalpMaxPerSymbol: j['scalp_max_per_symbol'] ?? 6,
        scalpMaxHoldMin: j['scalp_max_hold_min'] ?? 60,
        scalpRiskPercent: (j['scalp_risk_percent'] ?? 0.5).toDouble(),
        scalpBaseScore: j['scalp_base_score'] ?? 50,
        scalpScoreStep: j['scalp_score_step'] ?? 5,
        scalpMaxEntries: j['scalp_max_entries'] ?? 6,
        scalpMaxEfficiency: (j['scalp_max_efficiency'] ?? 0.5).toDouble(),
        scalpMaxSpreadRatio: (j['scalp_max_spread_ratio'] ?? 0.25).toDouble(),
        scalpCooldownMin: j['scalp_cooldown_min'] ?? 15,
      );
  Map<String, dynamic> toJson(Map<String, dynamic> base) => {
        ...base,
        'symbols': symbols,
        'min_score': minScore,
        'risk_percent': riskPercent,
        'sl_atr_mult': slAtrMult,
        'tp_atr_mult': tpAtrMult,
        'trailing_enabled': trailingEnabled,
        'news_filter_enabled': newsFilterEnabled,
        'max_open_positions': maxOpenPositions,
        'scalp_enabled': scalpEnabled,
        'scalp_max_per_symbol': scalpMaxPerSymbol,
        'scalp_max_hold_min': scalpMaxHoldMin,
        'scalp_risk_percent': scalpRiskPercent,
        'scalp_base_score': scalpBaseScore,
        'scalp_score_step': scalpScoreStep,
        'scalp_max_entries': scalpMaxEntries,
        'scalp_max_efficiency': scalpMaxEfficiency,
        'scalp_max_spread_ratio': scalpMaxSpreadRatio,
        'scalp_cooldown_min': scalpCooldownMin,
      };
}

class TradeHistory {
  final int positionId;
  final String symbol, type, comment;
  final double volume, openPrice, closePrice, profit;
  final int openTime, closeTime; // epoch detik (waktu server broker)
  TradeHistory({required this.positionId, required this.symbol,
      required this.type, required this.comment, required this.volume,
      required this.openPrice, required this.closePrice, required this.profit,
      required this.openTime, required this.closeTime});
  factory TradeHistory.fromJson(Map<String, dynamic> j) => TradeHistory(
        positionId: j['position_id'] ?? 0,
        symbol: j['symbol'] ?? '',
        type: j['type'] ?? '',
        comment: j['comment'] ?? '',
        volume: (j['volume'] ?? 0).toDouble(),
        openPrice: (j['open_price'] ?? 0).toDouble(),
        closePrice: (j['close_price'] ?? 0).toDouble(),
        profit: (j['profit'] ?? 0).toDouble(),
        openTime: j['open_time'] ?? 0,
        closeTime: j['close_time'] ?? 0,
      );
  DateTime get closedAt =>
      DateTime.fromMillisecondsSinceEpoch(closeTime * 1000);
  bool get isScalp => comment.startsWith('scalp');
}