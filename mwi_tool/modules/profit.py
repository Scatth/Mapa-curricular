def get_price(item_name, kind, base_prices, market_prices):
    """
    kind: 'ask' para custo, 'bid' para venda.
    base_prices: dict simples { 'Cedar Log': 50, ... }
    market_prices: { 'Cedar Log': {'ask': 21, 'bid': 19}, ... }
    """
    entry = market_prices.get(item_name)

    if isinstance(entry, dict):
        if kind == "ask":
            return entry.get("ask", base_prices.get(item_name, 0))
        else:
            return entry.get("bid", base_prices.get(item_name, 0))

    return base_prices.get(item_name, 0)


def compute_profit(recipe, base_prices, market_prices, speed_bonus):
    base = recipe["base_time"]
    eff = base / (1 + speed_bonus / 100)

    cost = 0.0
    for i in recipe["inputs"]:
        p = get_price(i["item"], "ask", base_prices, market_prices)
        cost += i["qty"] * p

    sell_price = get_price(recipe["name"], "bid", base_prices, market_prices)
    revenue = sell_price * recipe["output_qty"]

    profit = revenue - cost
    cph = 3600 / eff if eff else 0
    return {"eff": eff, "cost": cost, "profit": profit, "cph": cph, "pph": profit * cph}
