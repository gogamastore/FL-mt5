"""Deteksi price action: swing, Break of Structure, order block, pola candle."""
import pandas as pd


def swing_points(df: pd.DataFrame, lookback: int = 3):
    """Indeks swing high/low: bar tertinggi/terendah dibanding `lookback` bar di kiri-kanan."""
    highs, lows = [], []
    for i in range(lookback, len(df) - lookback):
        window_h = df["high"].iloc[i - lookback:i + lookback + 1]
        window_l = df["low"].iloc[i - lookback:i + lookback + 1]
        if df["high"].iloc[i] == window_h.max():
            highs.append(i)
        if df["low"].iloc[i] == window_l.min():
            lows.append(i)
    return highs, lows


def break_of_structure(df: pd.DataFrame, lookback: int = 3) -> str | None:
    """'bullish' jika close menembus swing high terakhir, 'bearish' jika menembus swing low."""
    highs, lows = swing_points(df.iloc[:-1], lookback)
    close = df["close"].iloc[-1]
    if highs and close > df["high"].iloc[highs[-1]]:
        return "bullish"
    if lows and close < df["low"].iloc[lows[-1]]:
        return "bearish"
    return None


def last_order_block(df: pd.DataFrame, direction: str) -> tuple[float, float] | None:
    """Order block sederhana: candle berlawanan terakhir sebelum pergerakan impulsif.
    Return (low, high) zona, atau None."""
    body = (df["close"] - df["open"]).iloc[-20:]
    for i in range(len(body) - 2, 0, -1):
        idx = body.index[i]
        nxt = body.index[i + 1]
        if direction == "bullish" and body[idx] < 0 and body[nxt] > abs(body[idx]) * 1.5:
            return float(df.loc[idx, "low"]), float(df.loc[idx, "high"])
        if direction == "bearish" and body[idx] > 0 and -body[nxt] > body[idx] * 1.5:
            return float(df.loc[idx, "low"]), float(df.loc[idx, "high"])
    return None


def candle_pattern(df: pd.DataFrame) -> str | None:
    """Engulfing / pinbar pada candle tertutup terakhir."""
    prev, cur = df.iloc[-3], df.iloc[-2]  # -1 adalah bar berjalan
    prev_body = prev["close"] - prev["open"]
    cur_body = cur["close"] - cur["open"]
    rng = cur["high"] - cur["low"]
    if rng <= 0:
        return None
    # Engulfing
    if prev_body < 0 < cur_body and cur["close"] > prev["open"] and cur["open"] < prev["close"]:
        return "bullish_engulfing"
    if prev_body > 0 > cur_body and cur["close"] < prev["open"] and cur["open"] > prev["close"]:
        return "bearish_engulfing"
    # Pinbar
    upper_wick = cur["high"] - max(cur["open"], cur["close"])
    lower_wick = min(cur["open"], cur["close"]) - cur["low"]
    if lower_wick > rng * 0.6:
        return "bullish_pinbar"
    if upper_wick > rng * 0.6:
        return "bearish_pinbar"
    return None
