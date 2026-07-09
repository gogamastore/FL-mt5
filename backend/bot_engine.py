"""Loop utama bot: strategi swing (confluence) + mode scalping saat pasar ranging."""
import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from config import BotSettings
from mt5_connector import MT5Connector
from risk_manager import RiskManager
from strategy import multi_timeframe, news_filter, scalping
from strategy.indicators import enrich
from trade_executor import TradeExecutor

log = logging.getLogger("engine")


class BotEngine:
    def __init__(self, settings: BotSettings):
        self.s = settings
        self.mt5 = MT5Connector()
        self.risk = RiskManager(self.mt5, settings)
        self.executor = TradeExecutor(settings.magic_number)
        self.running = False
        self.signals: list[dict] = []
        self.subscribers: set[asyncio.Queue] = set()
        self._last_bar: dict[tuple, object] = {}    # (symbol, tf) -> waktu bar
        self._bias: dict[str, str | None] = {}      # arah trend besar per simbol
        self._scalp_cooldown: dict[str, float] = {}  # symbol -> epoch boleh entry lagi
        self._known_scalp_tickets: dict[int, str] = {}  # ticket -> symbol (deteksi close)
        self._day = date.today()

    # ---------- pub/sub ----------
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subscribers.discard(q)

    def _publish(self, event: str, data: dict):
        msg = {"event": event, "data": data,
               "ts": datetime.now(timezone.utc).isoformat()}
        for q in list(self.subscribers):
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass

    # ---------- kontrol ----------
    def start(self) -> bool:
        if not self.mt5.connected and not self.mt5.connect():
            return False
        self.running = True
        return True

    def stop(self):
        self.running = False

    # ---------- loop ----------
    async def run(self):
        while True:
            if self.running:
                try:
                    await asyncio.to_thread(self._cycle)
                except Exception:
                    log.exception("Error pada siklus bot")
                self._publish("account", self.mt5.account_info())
            await asyncio.sleep(self.s.loop_interval)

    def _new_bar(self, symbol: str, tf: str, bar_time) -> bool:
        key = (symbol, tf)
        if self._last_bar.get(key) == bar_time:
            return False
        self._last_bar[key] = bar_time
        return True

    def _cycle(self):
        if date.today() != self._day:
            self._day = date.today()
            self.risk.reset_day()
        if not self.risk.check_daily_drawdown():
            return

        all_pos = self.mt5.open_positions(self.s.magic_number)
        scalp_pos = [p for p in all_pos if p.get("comment", "").startswith("scalp")]
        swing_pos = [p for p in all_pos if not p.get("comment", "").startswith("scalp")]

        self._close_expired_scalps(scalp_pos)

        # Mode scalping MANDIRI: saat aktif, mode utama (swing) mati total.
        if self.s.scalp_enabled:
            self._update_scalp_cooldowns(scalp_pos)
            for symbol in self.s.symbols:
                self._scalp_logic(symbol, scalp_pos)
            return

        # Mode utama (swing/confluence multi-TF) + trailing stop.
        atr_map: dict[str, float] = {}
        for symbol in self.s.symbols:
            self._swing_logic(symbol, swing_pos, atr_map)

        for upd in self.risk.trailing_updates(atr_map):
            if self.executor.modify_sltp(upd["ticket"], upd["symbol"], upd["sl"], upd["tp"]):
                self._publish("trailing", upd)

    # ---------- strategi swing (confluence multi-TF) ----------
    def _swing_logic(self, symbol: str, swing_pos: list, atr_map: dict):
        entry_df = self.mt5.get_rates(symbol, self.s.entry_timeframe)
        if entry_df is None or len(entry_df) < 210:
            return
        entry_df = enrich(entry_df, self.s.atr_period)
        atr_map[symbol] = float(entry_df["atr"].iloc[-1])

        if not self._new_bar(symbol, self.s.entry_timeframe, entry_df["time"].iloc[-1]):
            return

        trend_dfs = {}
        for tf in self.s.trend_timeframes:
            df = self.mt5.get_rates(symbol, tf)
            if df is None or len(df) < 210:
                return
            trend_dfs[tf] = enrich(df, self.s.atr_period)

        news_ok = (not self.s.news_filter_enabled or
                   news_filter.is_safe_to_trade(symbol, self.s.news_buffer_minutes))

        sig = multi_timeframe.evaluate(symbol, trend_dfs, entry_df, news_ok)
        self._bias[symbol] = sig.direction  # None = trend tidak selaras (ranging)

        sig_dict = sig.to_dict()
        sig_dict["mode"] = "swing"
        sig_dict["executed"] = False

        can_enter = (symbol not in {p["symbol"] for p in swing_pos}
                     and len(swing_pos) < self.s.max_open_positions)
        if sig.direction and sig.score >= self.s.min_score and can_enter:
            plan = self.risk.build_plan(symbol, sig.direction, sig.atr)
            if plan and plan.volume > 0:
                result = self.executor.open_market(
                    symbol, sig.direction, plan.volume, plan.sl, plan.tp,
                    comment=f"swing s{sig.score}")
                if result["ok"]:
                    sig_dict["executed"] = True
                    self._publish("trade_opened", {
                        "symbol": symbol, "direction": sig.direction, "mode": "swing",
                        "volume": plan.volume, "sl": plan.sl, "tp": plan.tp,
                        "score": sig.score, "reasons": sig.reasons,
                    })
        self._record_signal(sig_dict)

    # ---------- mode scalping (mandiri: support/resisten + momentum) ----------
    def _scalp_logic(self, symbol: str, scalp_pos: list):
        # Murni timeframe scalping — tanpa multi-TF, tanpa filter berita.
        # Cooldown: jeda setelah scalp rugi di simbol ini.
        now = self.mt5.server_time(symbol)
        if now and self._scalp_cooldown.get(symbol, 0) > now:
            return

        df = self.mt5.get_rates(symbol, self.s.scalp_timeframe)
        if df is None or len(df) < 80:
            return
        df = enrich(df, self.s.atr_period)
        if not self._new_bar(symbol, self.s.scalp_timeframe, df["time"].iloc[-1]):
            return

        # Spread saat ini (ask - bid) untuk penyaring biaya.
        price = self.mt5.current_price(symbol)
        spread = (price[1] - price[0]) if price else 0.0

        sig = scalping.evaluate(
            symbol, df, self.s.scalp_rsi_low, self.s.scalp_rsi_high,
            self.s.scalp_min_rr, spread=spread,
            max_spread_ratio=self.s.scalp_max_spread_ratio,
            max_efficiency=self.s.scalp_max_efficiency)
        if sig is None or sig.score < self.s.scalp_base_score:
            if sig is not None:
                self._record_signal({**sig.to_dict(), "executed": False,
                                     "planned_entries": 0, "executed_entries": 0})
            return

        # Jumlah entry dari kekuatan skor: n = 1 + (score - base)//step, dibatasi plafon.
        n = 1 + (sig.score - self.s.scalp_base_score) // max(self.s.scalp_score_step, 1)
        count = sum(1 for p in scalp_pos if p["symbol"] == symbol)
        capacity = self.s.scalp_max_per_symbol - count
        n = max(0, min(n, self.s.scalp_max_entries, capacity))

        sig_dict = sig.to_dict()
        sig_dict["planned_entries"] = n

        executed = 0
        for k in range(n):
            plan = self.risk.build_plan_levels(symbol, sig.direction, sig.sl, sig.tp,
                                               self.s.scalp_risk_percent)
            if not plan or plan.volume <= 0:
                break
            # Cek margin masih cukup sebelum tiap entry.
            acc = self.mt5.account_info()
            need = self.mt5.order_margin(symbol, sig.direction, plan.volume)
            if not acc or need is None or acc.get("free_margin", 0) < need:
                log.info("Scalp %s: margin tak cukup, entry ke-%d/%d dibatalkan",
                         symbol, k + 1, n)
                break
            result = self.executor.open_market(
                symbol, sig.direction, plan.volume, plan.sl, plan.tp,
                comment=f"scalp {count + k + 1}/{count + n}")
            if not result["ok"]:
                break
            executed += 1
            self._publish("trade_opened", {
                "symbol": symbol, "direction": sig.direction, "mode": "scalping",
                "volume": plan.volume, "sl": plan.sl, "tp": plan.tp,
                "score": sig.score, "reasons": sig.reasons,
            })

        sig_dict["executed"] = executed > 0
        sig_dict["executed_entries"] = executed
        self._record_signal(sig_dict)

    def _update_scalp_cooldowns(self, scalp_pos: list):
        """Deteksi posisi scalp yang baru tertutup RUGI → pasang cooldown di simbolnya,
        supaya bot tidak entry berulang saat level justru sedang jebol."""
        if self.s.scalp_cooldown_min <= 0:
            self._known_scalp_tickets = {p["ticket"]: p["symbol"] for p in scalp_pos}
            return
        current = {p["ticket"] for p in scalp_pos}
        disappeared = set(self._known_scalp_tickets) - current
        if disappeared:
            now = datetime.now()
            hist = self.mt5.trade_history(now - timedelta(days=1),
                                          now + timedelta(days=1), self.s.magic_number)
            for h in hist:
                if h["position_id"] in disappeared and h.get("profit", 0) < 0:
                    sym = h["symbol"]
                    srv = self.mt5.server_time(sym)
                    if srv:
                        self._scalp_cooldown[sym] = srv + self.s.scalp_cooldown_min * 60
                        log.info("Scalp %s rugi — cooldown %d menit", sym,
                                 self.s.scalp_cooldown_min)
        self._known_scalp_tickets = {p["ticket"]: p["symbol"] for p in scalp_pos}

    def _close_expired_scalps(self, scalp_pos: list):
        """Tutup paksa posisi scalp yang melewati batas waktu (durasi singkat)."""
        max_sec = self.s.scalp_max_hold_min * 60
        for p in scalp_pos:
            now = self.mt5.server_time(p["symbol"])
            if now and now - p["time"] >= max_sec:
                result = self.executor.close_position(p["ticket"])
                if result["ok"]:
                    log.info("Scalp %s #%s ditutup: lewat %d menit",
                             p["symbol"], p["ticket"], self.s.scalp_max_hold_min)
                    self._publish("trade_closed", {
                        "symbol": p["symbol"], "ticket": p["ticket"],
                        "reason": f"batas waktu scalp {self.s.scalp_max_hold_min} menit",
                        "profit": p["profit"],
                    })

    def _record_signal(self, sig: dict):
        sig["time"] = datetime.now(timezone.utc).isoformat()
        self.signals.append(sig)
        self.signals = self.signals[-200:]
        self._publish("signal", sig)
