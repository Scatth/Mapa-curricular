from flask import Flask, request
import os
import json

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MARKET_FILE = os.path.join(DATA_DIR, "market_prices.json")


def load_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


@app.route("/update_market", methods=["POST"])
def update_market():
    payload = request.get_json(force=True, silent=True) or {}
    print("Market data received:", payload)

    market = load_json(MARKET_FILE)

    for item_name, values in payload.items():
        if not isinstance(values, dict):
            continue

        best_ask = values.get("best_ask")
        best_bid = values.get("best_bid")

        current = market.get(item_name, {})
        if not isinstance(current, dict):
            current = {}

        if isinstance(best_ask, (int, float)) and best_ask > 0:
            current["ask"] = best_ask
        if isinstance(best_bid, (int, float)) and best_bid > 0:
            current["bid"] = best_bid

        market[item_name] = current

    save_json(MARKET_FILE, market)
    return {"status": "ok", "items": len(payload)}


if __name__ == "__main__":
    print("Servidor de Market rodando em http://127.0.0.1:5000/update_market")
    app.run(host="127.0.0.1", port=5000)
