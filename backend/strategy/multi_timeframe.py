"""Skor confluence multi-timeframe. Menghasilkan sinyal + daftar alasan (transparan)."""
from dataclasses import dataclass, field

import pandas as pd

from strategy import price_action as pa


@dataclass
class Signal:
    symbol: str
    direction: str | None = None   # "BUY" / "SELL" / None
    score: int = 0
    atr: float = 0.0
    reasons: list[str] = field(default_factory=list)

    def to_dict(self):
        return {"symbol": self.symbol, "direction": self.direction,
                "score": self.score, "atr": self.atr, "reasons": self.reasons}


def _trend(df: pd.DataFrame) -> str | None:
    last = df.iloc[-1]
    if last["ema50"] > last["ema200"] and last["close"] > last["ema50"]:
        return "bullish"
    if last["ema50"] < last["ema200"] and last["close"] < last["ema50"]:
        return "bearish"
    return None


def evaluate(symbol: str, trend_dfs: dict[str, pd.DataFrame],
             entry_df: pd.DataFrame, news_ok: bool,
             min_atr_ratio: float = 0.0003) -> Signal:
    """trend_dfs: {timeframe: df ber-indikator}; entry_df: timeframe eksekusi ber-indikator."""
    sig = Signal(symbol=symbol)
    last = entry_df.iloc[-1]
    sig.atr = float(last["atr"])

    # 1. Trend timeframe besar (25)
    trends = {tf: _trend(df) for tf, df in trend_dfs.items()}
    if all(t == "bullish" for t in trends.values()):
        bias = "bullish"
        sig.score += 25
        sig.reasons.append(f"Trend {'/'.join(trends)} bullish (EMA50>EMA200)")
    elif all(t == "bearish" for t in trends.values()):
        bias = "bearish"
        sig.score += 25
        sig.reasons.append(f"Trend {'/'.join(trends)} bearish (EMA50<EMA200)")
    else:
        sig.reasons.append("Trend timeframe besar tidak selaras — tidak entry")
        return sig

    # 2. Momentum (20)
    prev = entry_df.iloc[-2]
    rsi_now = last["rsi"]
    macd_cross_up = prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]
    macd_cross_dn = prev["macd"] >= prev["macd_signal"] and last["macd"] < last["macd_signal"]
    if bias == "bullish" and (35 <= rsi_now <= 65) and (macd_cross_up or last["macd_hist"] > 0):
        sig.score += 20
        sig.reasons.append(f"Momentum bullish: RSI {rsi_now:.1f}, MACD positif")
    elif bias == "bearish" and (35 <= rsi_now <= 65) and (macd_cross_dn or last["macd_hist"] < 0):
        sig.score += 20
        sig.reasons.append(f"Momentum bearish: RSI {rsi_now:.1f}, MACD negatif")

    # 3. Price action (25)
    pa_points = 0
    bos = pa.break_of_structure(entry_df)
    if bos == bias:
        pa_points += 15
        sig.reasons.append(f"Break of Structure {bias}")
    pattern = pa.candle_pattern(entry_df)
    if pattern and bias in pattern:
        pa_points += 10
        sig.reasons.append(f"Pola candle: {pattern}")
    ob = pa.last_order_block(entry_df, bias)
    if ob and ob[0] <= last["close"] <= ob[1]:
        pa_points = min(pa_points + 10, 25)
        sig.reasons.append(f"Harga di zona order block {ob[0]:.5f}-{ob[1]:.5f}")
    sig.score += min(pa_points, 25)

    # 4. Volatilitas (15)
    if sig.atr / last["close"] >= min_atr_ratio:
        sig.score += 15
        sig.reasons.append(f"Volatilitas cukup (ATR {sig.atr:.5f})")
    else:
        sig.reasons.append("ATR terlalu kecil — pasar sepi")

    # 5. Berita (15)
    if news_ok:
        sig.score += 15
        sig.reasons.append("Tidak ada berita high-impact dalam waktu dekat")
    else:
        sig.reasons.append("Berita high-impact terdeteksi — skor dikurangi")

    sig.direction = "BUY" if bias == "bullish" else "SELL"
    return sig
