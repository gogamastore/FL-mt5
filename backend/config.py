"""Konfigurasi bot. Ubah nilai di sini atau lewat API /settings."""
from pydantic import BaseModel


class BotSettings(BaseModel):
    # Simbol yang ditradingkan (sesuaikan dengan nama simbol broker Anda)
    symbols: list[str] = ["XAUUSD", "EURUSD", "GBPUSD", "BTCUSD"]

    # Timeframe
    trend_timeframes: list[str] = ["H1", "M30"]   # penentu arah
    entry_timeframe: str = "M5"                  # timeframe eksekusi

    # Confluence + multi-entry berbasis skor (mirip scalping):
    # n = 1 + (score - min_score)//swing_score_step, maks max_entries per simbol.
    min_score: int = 50          # skor minimum entry & basis 1 entry (0-100)
    swing_score_step: int = 5    # tiap kenaikan skor sebesar ini → +1 entry

    # Risk management
    risk_percent: float = 0.5    # % equity per ENTRY swing (tiap entry pakai penuh)
    atr_period: int = 14
    sl_atr_mult: float = 1.5     # SL = 1.5 x ATR
    tp_atr_mult: float = 2.5     # TP = 2.5 x ATR
    trailing_enabled: bool = True
    trail_start_atr: float = 1.0  # mulai trailing setelah profit 1 x ATR
    trail_dist_atr: float = 1.0   # jarak trailing 1 x ATR

    # Proteksi
    max_entries: int = 6         # maks entry swing per simbol dalam SATU keputusan
    max_open_positions: int = 6  # maks total posisi swing bersamaan (semua simbol)
    max_daily_drawdown_pct: float = 10.0
    magic_number: int = 202607

    # Mode scalping — MANDIRI: saat aktif, mode utama (swing) mati total.
    # Murni support/resisten + momentum (RSI). Tanpa filter berita, tanpa multi-timeframe.
    scalp_enabled: bool = False
    scalp_timeframe: str = "M5"        # M1 atau M5
    scalp_risk_percent: float = 0.5    # % equity per entry scalp (tiap entry pakai penuh)
    scalp_rsi_low: float = 35.0
    scalp_rsi_high: float = 65.0
    scalp_min_rr: float = 1.0
    # Multi-entry berbasis kekuatan skor: n = 1 + (score - base)//step, maks scalp_max_entries.
    scalp_base_score: int = 50         # skor minimum entry & basis 1 entry (0-100)
    scalp_score_step: int = 5          # tiap kenaikan skor sebesar ini → +1 entry
    scalp_max_entries: int = 6         # maks entry dalam SATU keputusan
    scalp_max_per_symbol: int = 6      # maks posisi scalp bersamaan per simbol (plafon kapasitas)
    scalp_max_hold_min: int = 60       # tutup paksa setelah X menit
    # Penyaring kualitas scalping (0 = nonaktif)
    scalp_max_efficiency: float = 0.5   # regime filter: skip jika ER >= ini (pasar trending)
    scalp_max_spread_ratio: float = 0.25  # skip jika spread > ratio × jarak TP
    scalp_cooldown_min: int = 15        # jeda entry di simbol setelah scalp rugi (menit)

    # Filter berita
    news_filter_enabled: bool = True
    news_buffer_minutes: int = 30

    # Interval loop (detik)
    loop_interval: int = 15


class ServerConfig:
    HOST = "0.0.0.0"
    PORT = 8000
    API_KEY = "CN9-5UB1TBJMD5wM_WR5dNiPr_Gbq9CXz6dt8Pa1spg"  # wajib diganti!

    # Login MT5 (kosongkan untuk memakai terminal yang sudah login)
    MT5_LOGIN: int | None = None
    MT5_PASSWORD: str | None = None
    MT5_SERVER: str | None = None
    MT5_PATH: str | None = None  # path terminal64.exe jika perlu


settings = BotSettings()
