"""Filter kalender ekonomi via Forex Factory (ff_calendar_thisweek.json).
Blok entry jika ada berita high-impact dalam ±buffer menit untuk mata uang terkait."""
import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

log = logging.getLogger("news")
FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

_cache: dict = {"events": [], "fetched": 0.0}
CACHE_TTL = 3600  # detik


def _fetch_events() -> list[dict]:
    now = time.time()
    if now - _cache["fetched"] < CACHE_TTL and _cache["events"]:
        return _cache["events"]
    try:
        resp = httpx.get(FF_URL, timeout=10)
        resp.raise_for_status()
        _cache["events"] = resp.json()
        _cache["fetched"] = now
    except Exception as e:  # jaringan gagal → jangan blok trading, hanya log
        log.warning("Gagal ambil kalender berita: %s", e)
    return _cache["events"]


def _currencies_of(symbol: str) -> set[str]:
    s = symbol.upper()
    known = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF", "CNY"}
    found = {c for c in known if c in s}
    if "XAU" in s or "BTC" in s or "ETH" in s:
        found.add("USD")
    return found or {"USD"}


def is_safe_to_trade(symbol: str, buffer_minutes: int = 30) -> bool:
    """False jika ada berita high-impact ±buffer untuk mata uang simbol ini."""
    events = _fetch_events()
    if not events:
        return True
    now = datetime.now(timezone.utc)
    window = timedelta(minutes=buffer_minutes)
    currencies = _currencies_of(symbol)
    for ev in events:
        if str(ev.get("impact", "")).lower() != "high":
            continue
        if ev.get("country", "").upper() not in currencies:
            continue
        try:
            ev_time = datetime.fromisoformat(ev["date"])
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)
        except (KeyError, ValueError):
            continue
        if abs(ev_time - now) <= window:
            log.info("Berita high-impact %s (%s) dekat — blok %s",
                     ev.get("title"), ev.get("country"), symbol)
            return False
    return True
