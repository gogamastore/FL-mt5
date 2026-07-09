"""Mode scalping MANDIRI: range trading di timeframe kecil (M1-M5).
Murni support/resisten + momentum — TANPA multi-timeframe & filter berita.
Entry di swing low/high (support-resistance) dengan konfirmasi RSI + candle,
SL ketat di luar swing, TP di level seberang.

Penyaring kualitas (opsional, dikontrol dari config):
- Regime filter (Efficiency Ratio): hanya entry saat pasar ranging.
- Spread guard: tolak setup saat spread lebar relatif ke target.
- Konfirmasi candle (pinbar/engulfing di level) & lonjakan volume → bonus skor.
- Kekuatan level (berapa kali level diuji) → bonus skor."""
from dataclasses import dataclass, field

import pandas as pd

from strategy import price_action as pa
from strategy.indicators import efficiency_ratio


@dataclass
class ScalpSignal:
    symbol: str
    direction: str          # "BUY" / "SELL"
    sl: float
    tp: float
    score: int = 50         # kekuatan sinyal 0-100 (menentukan jumlah entry)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self):
        return {"symbol": self.symbol, "direction": self.direction,
                "sl": self.sl, "tp": self.tp, "reasons": self.reasons,
                "mode": "scalping", "score": self.score}


def _conviction_score(dist: float, near: float, rsi_dev: float, rr: float,
                      min_rr: float, candle_ok: bool, touches: int,
                      vol_ok: bool) -> int:
    """Skor 0-100. Baseline 50 saat setup valid; bonus (maks +50) menuju 100.
    Komponen: kedekatan S/R (+10), ekstremitas RSI (+10), RR (+10),
    konfirmasi candle (+8), kekuatan level/touch (+7), lonjakan volume (+5)."""
    prox = (1 - min(dist / near, 1.0)) * 10 if near > 0 else 0
    rsi_b = min(max(rsi_dev, 0.0), 10.0)
    rr_b = min(max(rr - min_rr, 0.0) * 10, 10.0)
    candle_b = 8 if candle_ok else 0
    level_b = min(max(touches - 1, 0) * 3, 7)   # 1 sentuhan=0, 2=3, 3=6, 4+=7
    vol_b = 5 if vol_ok else 0
    return int(max(0, min(100, round(50 + prox + rsi_b + rr_b + candle_b + level_b + vol_b))))


def _volume_spike(w: pd.DataFrame, period: int = 20, mult: float = 1.2) -> bool:
    if "tick_volume" not in w.columns:
        return False
    v = w["tick_volume"]
    if len(v) < period:
        return False
    return float(v.iloc[-1]) > float(v.iloc[-period:].mean()) * mult


def evaluate(symbol: str, df: pd.DataFrame, rsi_low: float = 35.0,
             rsi_high: float = 65.0, min_rr: float = 1.0, lookback: int = 3,
             spread: float = 0.0, max_spread_ratio: float = 0.0,
             max_efficiency: float = 0.0, er_period: int = 20) -> ScalpSignal | None:
    """df: OHLC timeframe scalping yang sudah ber-indikator (enrich).
    spread: jarak ask-bid dalam satuan harga (0 = tak dicek).
    max_spread_ratio: tolak jika spread > ratio × jarak ke TP (0 = nonaktif).
    max_efficiency: regime gate, tolak jika ER >= nilai ini (0 = nonaktif)."""
    if len(df) < 80:
        return None
    w = df.iloc[-80:].reset_index(drop=True)

    # Regime filter: mean-reversion hanya masuk akal saat pasar ranging.
    if max_efficiency > 0:
        er = efficiency_ratio(w["close"], er_period)
        if er >= max_efficiency:
            return None  # pasar trending kuat — jangan lawan arah

    highs, lows = pa.swing_points(w, lookback)
    if not highs or not lows:
        return None

    last = w.iloc[-1]
    close = float(last["close"])
    atr = float(last["atr"])
    rsi_now = float(last["rsi"])
    rsi_prev = float(w["rsi"].iloc[-2])
    if atr <= 0:
        return None

    sw_highs = [float(w["high"].iloc[i]) for i in highs]
    sw_lows = [float(w["low"].iloc[i]) for i in lows]
    overhead = [h for h in sw_highs if h > close]   # resistance di atas
    below = [l for l in sw_lows if l < close]       # support di bawah
    if not overhead or not below:
        return None
    resistance = min(overhead)   # level terdekat
    support = max(below)
    near = 0.3 * atr             # "dekat" = dalam 0.3 ATR
    tol = 0.5 * atr              # toleransi klaster level (untuk hitung sentuhan)
    vol_ok = _volume_spike(w)
    pattern = pa.candle_pattern(w)

    # BUY: harga menyentuh support + RSI oversold dan mulai berbalik naik
    if (close - support) <= near and rsi_now <= rsi_low and rsi_now > rsi_prev:
        sl = support - 0.5 * atr
        tp = resistance
        rr = (tp - close) / max(close - sl, 1e-12)
        if rr >= min_rr and _spread_ok(spread, tp - close, max_spread_ratio):
            candle_ok = pattern in ("bullish_engulfing", "bullish_pinbar")
            touches = sum(1 for l in sw_lows if abs(l - support) <= tol)
            score = _conviction_score(close - support, near, rsi_low - rsi_now,
                                      rr, min_rr, candle_ok, touches, vol_ok)
            reasons = [
                f"Scalp BUY: harga di support {support:.5f} (swing low)",
                f"RSI {rsi_now:.1f} oversold & mulai naik",
                f"TP di resistance {resistance:.5f}, RR 1:{rr:.1f}",
            ]
            if candle_ok:
                reasons.append(f"Konfirmasi candle: {pattern}")
            if touches >= 2:
                reasons.append(f"Level support diuji {touches}× (kuat)")
            if vol_ok:
                reasons.append("Lonjakan volume mendukung")
            reasons.append(f"Skor kekuatan {score}")
            return ScalpSignal(symbol, "BUY", sl, tp, score, reasons)

    # SELL: harga menyentuh resistance + RSI overbought dan mulai berbalik turun
    if (resistance - close) <= near and rsi_now >= rsi_high and rsi_now < rsi_prev:
        sl = resistance + 0.5 * atr
        tp = support
        rr = (close - tp) / max(sl - close, 1e-12)
        if rr >= min_rr and _spread_ok(spread, close - tp, max_spread_ratio):
            candle_ok = pattern in ("bearish_engulfing", "bearish_pinbar")
            touches = sum(1 for h in sw_highs if abs(h - resistance) <= tol)
            score = _conviction_score(resistance - close, near, rsi_now - rsi_high,
                                      rr, min_rr, candle_ok, touches, vol_ok)
            reasons = [
                f"Scalp SELL: harga di resistance {resistance:.5f} (swing high)",
                f"RSI {rsi_now:.1f} overbought & mulai turun",
                f"TP di support {support:.5f}, RR 1:{rr:.1f}",
            ]
            if candle_ok:
                reasons.append(f"Konfirmasi candle: {pattern}")
            if touches >= 2:
                reasons.append(f"Level resistance diuji {touches}× (kuat)")
            if vol_ok:
                reasons.append("Lonjakan volume mendukung")
            reasons.append(f"Skor kekuatan {score}")
            return ScalpSignal(symbol, "SELL", sl, tp, score, reasons)
    return None


def _spread_ok(spread: float, target_dist: float, max_ratio: float) -> bool:
    """True jika spread masih layak dibanding jarak ke TP."""
    if max_ratio <= 0 or spread <= 0:
        return True
    return spread <= target_dist * max_ratio
