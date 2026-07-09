"""FastAPI server: REST + WebSocket untuk aplikasi Flutter.
Jalankan di Windows yang sama dengan terminal MT5:
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000
"""
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from bot_engine import BotEngine
from config import BotSettings, ServerConfig, settings

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("asyncio").setLevel(logging.ERROR)

app = FastAPI(title="MT5 Trading Bot API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])  # untuk build web Flutter

engine = BotEngine(settings)


def check_key(x_api_key: str = Header(default="")):
    if x_api_key != ServerConfig.API_KEY:
        raise HTTPException(status_code=401, detail="API key salah")


@app.on_event("startup")
async def startup():
    asyncio.create_task(engine.run())


# ---------- REST ----------
@app.get("/status", dependencies=[Depends(check_key)])
def status():
    return {"running": engine.running, "mt5_connected": engine.mt5.connected,
            "account": engine.mt5.account_info(), "symbols": engine.s.symbols}


@app.post("/bot/start", dependencies=[Depends(check_key)])
def bot_start():
    if not engine.start():
        raise HTTPException(500, "Gagal terhubung ke terminal MT5")
    return {"running": True}


@app.post("/bot/stop", dependencies=[Depends(check_key)])
def bot_stop():
    engine.stop()
    return {"running": False}


@app.get("/positions", dependencies=[Depends(check_key)])
def positions():
    return engine.mt5.open_positions(engine.s.magic_number)


@app.post("/positions/{ticket}/close", dependencies=[Depends(check_key)])
def close_position(ticket: int):
    result = engine.executor.close_position(ticket)
    if not result["ok"]:
        raise HTTPException(400, result["error"])
    return result


@app.get("/history", dependencies=[Depends(check_key)])
def history(date_from: str | None = None, date_to: str | None = None):
    """Riwayat posisi tertutup bot. Format tanggal: YYYY-MM-DD. Default 7 hari terakhir."""
    try:
        f = datetime.fromisoformat(date_from) if date_from else datetime.now() - timedelta(days=7)
        t = (datetime.fromisoformat(date_to) + timedelta(days=1)) if date_to \
            else datetime.now() + timedelta(days=1)
    except ValueError:
        raise HTTPException(400, "Format tanggal salah, pakai YYYY-MM-DD")
    return engine.mt5.trade_history(f, t, engine.s.magic_number)


@app.get("/signals", dependencies=[Depends(check_key)])
def signals(limit: int = 50):
    return engine.signals[-limit:][::-1]


@app.get("/settings", dependencies=[Depends(check_key)])
def get_settings():
    return engine.s.model_dump()


@app.put("/settings", dependencies=[Depends(check_key)])
def update_settings(new: BotSettings):
    engine.s = new
    engine.risk.s = new
    return engine.s.model_dump()


# ---------- WebSocket ----------
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    if ws.query_params.get("key") != ServerConfig.API_KEY:
        await ws.close(code=4401)
        return
    await ws.accept()
    q = engine.subscribe()
    try:
        while True:
            msg = await q.get()
            await ws.send_json(msg)
    except Exception:
        pass
    finally:
        engine.unsubscribe(q)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=ServerConfig.HOST, port=ServerConfig.PORT)
