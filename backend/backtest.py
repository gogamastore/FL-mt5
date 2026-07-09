"""Backtest sederhana untuk strategi scalping — mengukur EDGE terhadap market history.

Menggunakan ulang `strategy.scalping.evaluate` (logika yang sama persis dengan bot live),
lalu mensimulasikan tiap sinyal bar-per-bar: entry di close bar sinyal, keluar saat harga
menyentuh SL atau TP lebih dulu (atau batas waktu). Hasil diukur dalam kelipatan-R
(reward/risk), sehingga bebas dari ukuran lot.

Jalankan di VPS (butuh MT5 + terminal login):
    python backtest.py --symbols XAUUSD EURUSD --tf M5 --bars 5000

Fungsi `simulate()` murni (tanpa MT5) sehingga bisa diuji dengan data sintetis.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field

import pandas as pd

from config import settings
from strategy import scalping
from strategy.indicators import enrich

TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


@dataclass
class BTResult:
    symbol: str
    r_multiples: list[float] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.r_multiples)

    @property
    def wins(self) -> list[float]:
        return [r for r in self.r_multiples if r > 0]

    @property
    def losses(self) -> list[float]:
        return [r for r in self.r_multiples if r <= 0]

    def stats(self) -> dict:
        if not self.r_multiples:
            return {"symbol": self.symbol, "trades": 0}
        total = sum(self.r_multiples)
        gross_win = sum(self.wins)
        gross_loss = abs(sum(self.losses))
        # max drawdown pada kurva ekuitas (dalam R)
        peak = cum = max_dd = 0.0
        max_streak = streak = 0
        for r in self.r_multiples:
            cum += r
            peak = max(peak, cum)
            max_dd = max(max_dd, peak - cum)
            streak = streak + 1 if r <= 0 else 0
            max_streak = max(max_streak, streak)
        return {
            "symbol": self.symbol,
            "trades": self.n,
            "win_rate": round(len(self.wins) / self.n * 100, 1),
            "expectancy_R": round(float(total) / self.n, 3),
            "total_R": round(float(total), 2),
            "profit_factor": round(float(gross_win / gross_loss), 2) if gross_loss else float("inf"),
            "avg_win_R": round(float(sum(self.wins) / len(self.wins)), 2) if self.wins else 0.0,
            "avg_loss_R": round(float(sum(self.losses) / len(self.losses)), 2) if self.losses else 0.0,
            "max_dd_R": round(float(max_dd), 2),
            "max_losing_streak": max_streak,
        }


def simulate(df: pd.DataFrame, symbol: str = "SYM", *,
             rsi_low: float = 35.0, rsi_high: float = 65.0, min_rr: float = 1.0,
             base_score: int = 50, max_efficiency: float = 0.5,
             max_spread_ratio: float = 0.0, spread: float = 0.0,
             max_hold_bars: int = 12) -> BTResult:
    """df: OHLC ber-indikator (enrich). Satu posisi pada satu waktu (mengukur edge)."""
    res = BTResult(symbol)
    if len(df) < 90:
        return res
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()

    i = 80
    n = len(df)
    while i < n - 1:
        window = df.iloc[: i + 1]
        sig = scalping.evaluate(symbol, window, rsi_low, rsi_high, min_rr,
                                spread=spread, max_spread_ratio=max_spread_ratio,
                                max_efficiency=max_efficiency)
        if sig is None or sig.score < base_score:
            i += 1
            continue

        entry = float(close[i])
        risk = abs(entry - sig.sl)
        if risk <= 0:
            i += 1
            continue
        rr = abs(sig.tp - entry) / risk

        outcome = None      # +rr (TP), -1 (SL), atau R saat batas waktu
        exit_i = i
        for j in range(i + 1, min(i + 1 + max_hold_bars, n)):
            exit_i = j
            if sig.direction == "BUY":
                if low[j] <= sig.sl:            # SL diperiksa lebih dulu (konservatif)
                    outcome = -1.0
                    break
                if high[j] >= sig.tp:
                    outcome = rr
                    break
            else:  # SELL
                if high[j] >= sig.sl:
                    outcome = -1.0
                    break
                if low[j] <= sig.tp:
                    outcome = rr
                    break
        if outcome is None:                    # batas waktu: nilai dari harga penutup
            move = (close[exit_i] - entry) if sig.direction == "BUY" else (entry - close[exit_i])
            outcome = move / risk
        res.r_multiples.append(outcome)
        i = exit_i + 1                         # lanjut setelah posisi keluar
    return res


def run_symbol(connector, symbol: str, tf: str, bars: int,
               spread_points: float = 0.0) -> BTResult:
    df = connector.get_rates(symbol, tf, count=bars)
    if df is None or len(df) < 90:
        print(f"  {symbol}: data tidak cukup")
        return BTResult(symbol)
    df = enrich(df, settings.atr_period)
    info = connector.symbol_info(symbol)
    point = getattr(info, "point", 0.0) or 0.0
    spread = spread_points * point
    hold_bars = max(1, settings.scalp_max_hold_min // TF_MINUTES.get(tf, 5))
    return simulate(df, symbol, rsi_low=settings.scalp_rsi_low,
                    rsi_high=settings.scalp_rsi_high, min_rr=settings.scalp_min_rr,
                    base_score=settings.scalp_base_score,
                    max_efficiency=settings.scalp_max_efficiency,
                    max_spread_ratio=settings.scalp_max_spread_ratio,
                    spread=spread, max_hold_bars=hold_bars)


def _print_stats(stats: dict):
    if stats.get("trades", 0) == 0:
        print(f"  {stats['symbol']}: 0 trade")
        return
    print(f"  {stats['symbol']}: {stats['trades']} trade | "
          f"win {stats['win_rate']}% | expectancy {stats['expectancy_R']}R | "
          f"PF {stats['profit_factor']} | total {stats['total_R']}R | "
          f"maxDD {stats['max_dd_R']}R | streak kalah {stats['max_losing_streak']}")


def main():
    ap = argparse.ArgumentParser(description="Backtest strategi scalping")
    ap.add_argument("--symbols", nargs="+", default=settings.symbols)
    ap.add_argument("--tf", default=settings.scalp_timeframe)
    ap.add_argument("--bars", type=int, default=5000)
    ap.add_argument("--spread-points", type=float, default=0.0,
                    help="perkiraan spread dalam point untuk uji sensitivitas biaya")
    args = ap.parse_args()

    from mt5_connector import MT5Connector
    conn = MT5Connector()
    if not conn.connect():
        print("Gagal konek MT5 — jalankan di mesin dengan terminal MT5 aktif.")
        return
    print(f"Backtest {args.tf}, {args.bars} bar, spread~{args.spread_points} point\n")
    all_r: list[float] = []
    for sym in args.symbols:
        res = run_symbol(conn, sym, args.tf, args.bars, args.spread_points)
        _print_stats(res.stats())
        all_r.extend(res.r_multiples)
    conn.shutdown()

    agg = BTResult("GABUNGAN", all_r)
    print()
    _print_stats(agg.stats())


if __name__ == "__main__":
    main()
