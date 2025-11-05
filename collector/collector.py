import asyncio
import json
import os
from datetime import datetime
import pymongo
import websockets

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB", "gemscap")
COLLECTION = "ticks"

symbols = ["btcusdt", "ethusdt"]

async def handle_symbol(sym, client):
    url = f"wss://fstream.binance.com/ws/{sym}@trade"
    async with websockets.connect(url) as ws:
        print(f"Connected {sym}")
        async for msg in ws:
            try:
                j = json.loads(msg)
                if j.get("e") == "trade":
                    rec = {
                        "symbol": j.get("s").lower(),
                        "ts": datetime.utcfromtimestamp(j.get("T", j.get("E")) / 1000.0),
                        "price": float(j.get("p")),
                        "qty": float(j.get("q")),
                    }
                    client[DB_NAME][COLLECTION].insert_one(rec)
            except Exception as e:
                print(f"{sym} error: {e}")

async def main():
    client = pymongo.MongoClient(MONGO_URI)
    await asyncio.gather(*(handle_symbol(s, client) for s in symbols))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Collector stopped.")
