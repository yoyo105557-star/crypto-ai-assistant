import os
import time
import requests
from openai import OpenAI

HEADERS = {"User-Agent": "CryptoAIAssistant/1.0"}

def get_json(url, retries=3, timeout=15):
    for i in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            time.sleep(1 + i)
    return None

def to_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

def compact(x):
    if x is None:
        return "資料不足"
    if x >= 1_000_000_000_000:
        return f"${x/1_000_000_000_000:.2f}T"
    if x >= 1_000_000_000:
        return f"${x/1_000_000_000:.2f}B"
    if x >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    return f"${x:,.0f}"

def fmt(x, digits=2):
    if x is None:
        return "資料不足"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return str(x)

def binance_24h(symbol):
    data = get_json(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}")
    if not data:
        return {"ok": False, "symbol": symbol}
    return {
        "ok": True,
        "symbol": symbol,
        "price": to_float(data.get("lastPrice")),
        "change_24h": to_float(data.get("priceChangePercent")),
        "quote_volume": to_float(data.get("quoteVolume")),
    }

def binance_futures(symbol):
    funding = get_json(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1")
    oi = get_json(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}")
    funding_pct = None
    open_interest = None
    try:
        funding_pct = to_float(funding[0]["fundingRate"]) * 100
    except Exception:
        pass
    try:
        open_interest = to_float(oi["openInterest"])
    except Exception:
        pass
    return {
        "ok": funding_pct is not None or open_interest is not None,
        "symbol": symbol,
        "funding_pct": funding_pct,
        "open_interest": open_interest,
    }

def fear_greed():
    data = get_json("https://api.alternative.me/fng/?limit=1")
    try:
        x = data["data"][0]
        return {"ok": True, "value": int(x["value"]), "label": x["value_classification"]}
    except Exception:
        return {"ok": False, "value": None, "label": "資料不足"}

def coingecko_global():
    data = get_json("https://api.coingecko.com/api/v3/global")
    try:
        d = data["data"]
        return {
            "ok": True,
            "btc_d": to_float(d["market_cap_percentage"].get("btc")),
            "eth_d": to_float(d["market_cap_percentage"].get("eth")),
            "total_mcap": to_float(d["total_market_cap"].get("usd")),
            "total_volume": to_float(d["total_volume"].get("usd")),
            "market_change_24h": to_float(d.get("market_cap_change_percentage_24h_usd")),
        }
    except Exception:
        return {
            "ok": False,
            "btc_d": None,
            "eth_d": None,
            "total_mcap": None,
            "total_volume": None,
            "market_change_24h": None,
        }

def coingecko_categories():
    data = get_json("https://api.coingecko.com/api/v3/coins/categories")
    if not isinstance(data, list):
        return []
    aliases = {
        "Artificial Intelligence (AI)": "AI",
        "Real World Assets (RWA)": "RWA",
        "Decentralized Finance (DeFi)": "DeFi",
        "Meme": "MEME",
        "Gaming (GameFi)": "Gaming",
        "Layer 1 (L1)": "Layer1",
        "Layer 2 (L2)": "Layer2",
        "Decentralized Physical Infrastructure (DePIN)": "DePIN",
        "Infrastructure": "Infrastructure",
    }
    rows = []
    for x in data:
        name = x.get("name")
        if name in aliases:
            rows.append({
                "sector": aliases[name],
                "change_24h": to_float(x.get("market_cap_change_24h")),
                "market_cap": to_float(x.get("market_cap")),
                "volume_24h": to_float(x.get("volume_24h")),
            })
    return rows

def stablecoins():
    data = get_json("https://stablecoins.llama.fi/stablecoins?includePrices=true")
    if not data or "peggedAssets" not in data:
        return {"ok": False, "total": None}
    total = 0
    for item in data.get("peggedAssets", []):
        total += to_float(item.get("circulating", {}).get("peggedUSD")) or 0
    return {"ok": True, "total": total}

def fetch_all():
    return {
        "spot": [binance_24h(s) for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ETHBTC"]],
        "futures": [binance_futures(s) for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]],
        "fear": fear_greed(),
        "global": coingecko_global(),
        "categories": coingecko_categories(),
        "stablecoins": stablecoins(),
    }

def clamp(x):
    if x is None:
        return None
    return max(0, min(100, round(x)))

def avg(xs):
    xs = [x for x in xs if x is not None]
    return None if not xs else sum(xs) / len(xs)

def score_change(x):
    if x is None:
        return None
    if x >= 5:
        return 100
    if x >= 3:
        return 90
    if x >= 1:
        return 75
    if x >= 0:
        return 60
    if x >= -1:
        return 40
    if x >= -3:
        return 25
    return 10

def score_fear(v):
    if v is None:
        return None, None
    if 45 <= v <= 75:
        return 80, 30
    if v > 80:
        return 55, 75
    if v < 30:
        return 30, 75
    return 55, 50

def score_funding(x):
    if x is None:
        return None
    ax = abs(x)
    if ax <= 0.01:
        return 85
    if ax <= 0.03:
        return 65
    if ax <= 0.06:
        return 45
    return 20

def sector_score(row):
    momentum = score_change(row.get("change_24h"))
    vol = row.get("volume_24h")
    cap = row.get("market_cap")
    liquidity = 50
    if vol and cap:
        ratio = vol / cap
        if ratio > 0.2:
            liquidity = 90
        elif ratio > 0.08:
            liquidity = 75
        elif ratio > 0.03:
            liquidity = 60
        else:
            liquidity = 40
    return clamp((momentum or 50) * 0.7 + liquidity * 0.3)

def build_scores(data):
    spot = {x.get("symbol"): x for x in data["spot"] if x}
    btc = spot.get("BTCUSDT", {})
    sol = spot.get("SOLUSDT", {})
    ethbtc = spot.get("ETHBTC", {})
    g = data["global"]
    fear = data["fear"]

    btc_score = score_change(btc.get("change_24h"))
    sol_score = score_change(sol.get("change_24h"))
    ethbtc_score = score_change(ethbtc.get("change_24h"))
    market_change_score = score_change(g.get("market_change_24h"))
    fear_bull, fear_bear = score_fear(fear.get("value"))

    funding_score = avg([score_funding(x.get("funding_pct")) for x in data["futures"]])

    btc_d = g.get("btc_d")
    btc_d_alt_score = None
    if btc_d is not None:
        btc_d_alt_score = 100 if btc_d < 50 else 75 if btc_d < 55 else 45 if btc_d < 60 else 20

    sector_rows = []
    sector_scores = []
    for row in data["categories"]:
        s = sector_score(row)
        sector_scores.append(s)
        sector_rows.append({
            "sector": row["sector"],
            "score": s,
            "change_24h": row.get("change_24h"),
            "volume": compact(row.get("volume_24h")),
            "market_cap": compact(row.get("market_cap")),
        })
    sector_rows = sorted(sector_rows, key=lambda x: x["score"] or -1, reverse=True)
    sector_avg = avg(sector_scores)

    stable_score = 55 if data["stablecoins"].get("ok") else None

    bull = clamp(avg([btc_score, ethbtc_score, market_change_score, fear_bull, funding_score, sector_avg, stable_score]))
    bear = clamp(avg([
        100 - btc_score if btc_score is not None else None,
        100 - ethbtc_score if ethbtc_score is not None else None,
        fear_bear,
        100 - market_change_score if market_change_score is not None else None,
        100 - funding_score if funding_score is not None else None,
    ]))
    alt = clamp(avg([ethbtc_score, sol_score, btc_d_alt_score, market_change_score, sector_avg, stable_score]))
    market = clamp(avg([bull, 100 - bear if bear is not None else None, alt]))

    return {"market": market, "bull": bull, "bear": bear, "alt": alt, "funding": clamp(funding_score), "sectors": sector_rows}

def decision(scores):
    market = scores.get("market")
    bull = scores.get("bull") or 0
    bear = scores.get("bear") or 0
    if market is None:
        return "資料不足", "☆☆☆☆☆", "0%", "資料不足，不依賴系統分數交易。"
    if market >= 80 and bull > bear:
        return "Risk ON", "★★★★★", "2~3%", "偏多，等待回踩，不追價。"
    if market >= 60:
        return "震盪偏多", "★★★★☆", "1~2%", "只做 A+ 訊號。"
    if market >= 40:
        return "震盪", "★★★☆☆", "1%", "降低交易頻率。"
    return "Risk OFF", "★☆☆☆☆", "0~1%", "保護本金，不做多山寨。"

def build_report(data, scores, ai_comment=None):
    state, stars, risk, summary = decision(scores)
    spot = {x.get("symbol"): x for x in data["spot"] if x}
    btc = spot.get("BTCUSDT", {})
    eth = spot.get("ETHUSDT", {})
    sol = spot.get("SOLUSDT", {})
    ethbtc = spot.get("ETHBTC", {})
    fear = data["fear"]
    g = data["global"]

    best_sector = scores["sectors"][0]["sector"] if scores["sectors"] else "資料不足"
    sector_lines = []
    for i, s in enumerate(scores["sectors"][:5], 1):
        sector_lines.append(f"{i}. {s['sector']}｜{s['score']}｜24H {fmt(s['change_24h'])}%")

    funding_lines = []
    for f in data["futures"]:
        funding_lines.append(f"{f.get('symbol')}｜Funding {fmt(f.get('funding_pct'), 5)}%｜OI {fmt(f.get('open_interest'), 0)}")

    alt = scores.get("alt")
    if alt is None:
        alt_phase = "資料不足"
    elif alt >= 80:
        alt_phase = "全面山寨季 / 擴散期"
    elif alt >= 65:
        alt_phase = "山寨季初期擴散"
    elif alt >= 50:
        alt_phase = "山寨季準備階段"
    else:
        alt_phase = "山寨季尚未開始"

    return f"""📊 Crypto AI Assistant

市場總分：{scores.get('market')}/100
牛市分數：{scores.get('bull')}/100
熊市分數：{scores.get('bear')}/100
山寨季分數：{scores.get('alt')}/100
星級：{stars}

狀態：{state}
建議單筆風險：{risk}
結論：{summary}

━━━━━━━━━━━━━━
₿ 加密市場

BTC：{fmt(btc.get('price'))}｜24H {fmt(btc.get('change_24h'))}%
ETH：{fmt(eth.get('price'))}｜24H {fmt(eth.get('change_24h'))}%
SOL：{fmt(sol.get('price'))}｜24H {fmt(sol.get('change_24h'))}%
ETH/BTC：{fmt(ethbtc.get('price'), 6)}｜24H {fmt(ethbtc.get('change_24h'))}%

BTC.D：{fmt(g.get('btc_d'))}%
全市場24H：{fmt(g.get('market_change_24h'))}%
Fear & Greed：{fear.get('value')}｜{fear.get('label')}

━━━━━━━━━━━━━━
⚡ 合約市場

{chr(10).join(funding_lines)}

━━━━━━━━━━━━━━
🔥 板塊排行

{chr(10).join(sector_lines) if sector_lines else '資料不足'}

最強板塊：{best_sector}

━━━━━━━━━━━━━━
🚀 山寨季

{alt_phase}

━━━━━━━━━━━━━━
✅ 今日 Checklist

- 今天適合做多嗎？{"可以，但等回踩" if scores.get("market") and scores.get("market") >= 60 else "不建議"}
- 今天適合做空嗎？{"只做破結構" if scores.get("bull", 0) >= scores.get("bear", 0) else "可觀察反彈空"}
- 可以放大部位嗎？{"限制加倉" if scores.get("market") and scores.get("market") >= 80 else "不建議"}
- 禁止追價：是
- 禁止 FOMO 提高槓桿：是

━━━━━━━━━━━━━━
🧠 AI 補充

{ai_comment or "等待流動性掃蕩與成交量確認後再進場。"}

非投資建議。
"""

def ai_comment(raw_report):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "OpenAI API Key 未設定，僅輸出量化報告。"
    try:
        client = OpenAI(api_key=key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是加密貨幣交易助理。請用繁體中文給出120字內補充。不得保證獲利，不得鼓勵高槓桿。強調等待流動性掃蕩與成交量確認。"},
                {"role": "user", "content": raw_report},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI 分析失敗：{e}"

def send_telegram_message(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
    for chunk in chunks:
        r = requests.post(url, json={"chat_id": chat_id, "text": chunk})
        r.raise_for_status()

def main():
    data = fetch_all()
    scores = build_scores(data)
    draft = build_report(data, scores)
    comment = ai_comment(draft)
    final_report = build_report(data, scores, comment)
    send_telegram_message(final_report)
    print("Report sent.")

if __name__ == "__main__":
    main()
