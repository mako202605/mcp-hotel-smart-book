# -*- coding: utf-8 -*-
"""酒店聪明订 MCP服务 - 多平台酒店比价+低价日历+订房决策建议"""
import os
import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta

from fastmcp import FastMCP

mcp = FastMCP("mcp-hotel-smart-book")

# ============ 配置 ============
PROXY_TOKEN = os.environ.get("PROXY_TOKEN", "tp_8k2mX9vQ4z")
FLIGGY_PROXY_URL = os.environ.get("FLIGGY_PROXY_URL", "https://1439498936-6sysdjjt99.ap-guangzhou.tencentscf.com")
TUNIU_PROXY_URL = os.environ.get("TUNIU_PROXY_URL", "https://1439498936-0junm3maxj.ap-guangzhou.tencentscf.com")
RG_PROXY_URL = os.environ.get("RG_PROXY_URL", "https://1439498936-460a7b6oqn.ap-guangzhou.tencentscf.com")
HOTEL_PROXY_URL = os.environ.get("HOTEL_PROXY_URL", "https://1439498936-4wdncmn2oj.ap-guangzhou.tencentscf.com")

HEADERS = {"Content-Type": "application/json", "X-Proxy-Token": PROXY_TOKEN}

# ============ 品牌词表 ============
HOTEL_BRANDS = [
    "华尔道夫", "半岛", "瑞吉", "宝格丽", "安缦", "文华东方", "四季", "丽思卡尔顿",
    "柏悦", "艾美", "康莱德", "费尔蒙", "悦榕庄", "六善", "阿丽拉",
    "万豪", "喜来登", "威斯汀", "JW万豪", "万丽", "凯悦", "君悦",
    "洲际", "皇冠假日", "英迪格", "希尔顿", "逸林", "嘉悦里",
    "香格里拉", "凯宾斯基", "索菲特", "丽笙", "朗廷",
    "诺富特", "美爵", "假日", "万怡", "福朋", "源宿",
    "全季", "亚朵", "亚·朵", "喆·啡", "喆啡", "希岸", "欢朋",
    "丽枫", "桔子", "水晶", "漫心", "花间堂", "开元",
    "如家", "汉庭", "锦江", "7天", "速8", "格林豪泰", "布丁",
    "尚客优", "城市便捷", "维也纳", "维也纳国际", "维也纳好眠",
    "怡莱", "海友", "宜必思",
    "途家", "斯维登", "城家", "雅诗阁", "盛捷", "馨乐庭",
]
BRAND_DOT_MAP = {"喆·啡": "喆啡", "亚·朵": "亚朵"}

# ============ 旺季/品牌档次/城市均价 ============
PEAK_DATES = {
    "春运": ("2026-01-25", "2026-02-22"), "清明": ("2026-04-03", "2026-04-06"),
    "五一": ("2026-05-01", "2026-05-05"), "端午": ("2026-05-30", "2026-06-01"),
    "暑假": ("2026-07-01", "2026-08-31"), "中秋": ("2026-09-25", "2026-09-27"),
    "国庆": ("2026-10-01", "2026-10-07"), "寒假": ("2026-01-15", "2026-02-22"),
}

BRAND_TIER = {
    "华尔道夫": "ultra_luxury", "半岛": "ultra_luxury", "瑞吉": "ultra_luxury",
    "宝格丽": "ultra_luxury", "安缦": "ultra_luxury", "文华东方": "ultra_luxury",
    "四季": "ultra_luxury", "丽思卡尔顿": "ultra_luxury", "柏悦": "ultra_luxury",
    "万豪": "luxury", "喜来登": "luxury", "威斯汀": "luxury", "JW万豪": "ultra_luxury",
    "万丽": "luxury", "凯悦": "luxury", "君悦": "ultra_luxury", "康莱德": "ultra_luxury",
    "洲际": "luxury", "皇冠假日": "upscale", "英迪格": "luxury",
    "希尔顿": "luxury", "逸林": "upscale", "香格里拉": "ultra_luxury",
    "索菲特": "luxury", "朗廷": "luxury",
    "诺富特": "upscale", "假日": "upscale", "万怡": "upscale",
    "福朋": "upscale", "全季": "midscale", "亚朵": "midscale",
    "喆啡": "midscale", "希岸": "midscale", "欢朋": "midscale",
    "丽枫": "midscale", "桔子": "midscale",
    "如家": "economy", "汉庭": "economy", "锦江": "economy",
    "7天": "economy", "速8": "economy", "海友": "economy",
}

TIER_MULTIPLIER = {"ultra_luxury": 3.0, "luxury": 2.0, "upscale": 1.2, "midscale": 0.7, "economy": 0.4}

CITY_HOTEL_REF = {
    "上海": (250, 450, 900), "北京": (230, 420, 850), "广州": (200, 380, 700),
    "深圳": (220, 400, 750), "杭州": (200, 380, 750), "成都": (180, 330, 650),
    "重庆": (170, 300, 600), "南京": (190, 350, 680), "武汉": (170, 310, 600),
    "西安": (180, 330, 650), "长沙": (170, 300, 580), "厦门": (200, 380, 780),
    "三亚": (300, 550, 1200), "昆明": (180, 330, 650), "青岛": (190, 350, 700),
    "大连": (190, 350, 680), "苏州": (190, 350, 700), "天津": (180, 330, 630),
    "郑州": (160, 300, 580), "哈尔滨": (170, 310, 600),
}


# ============ 工具函数 ============
def normalize_brand(name):
    for dot_brand, no_dot in BRAND_DOT_MAP.items():
        name = name.replace(dot_brand, no_dot)
    return name


def extract_brand(name):
    name = normalize_brand(name.strip())
    sorted_brands = sorted(HOTEL_BRANDS, key=len, reverse=True)
    for brand in sorted_brands:
        if normalize_brand(brand) in name:
            return normalize_brand(brand)
    return ""


def hotel_name_similarity(name1, name2):
    name1 = normalize_brand(name1.strip())
    name2 = normalize_brand(name2.strip())
    if name1 == name2:
        return 1.0
    brand1, brand2 = extract_brand(name1), extract_brand(name2)
    brand_match = 1.0 if brand1 and brand2 and brand1 == brand2 else (0.8 if brand1 and brand2 and (brand1 in brand2 or brand2 in brand1) else (0.5 if not brand1 and not brand2 else 0.0))
    rest1 = name1.replace(brand1, "").strip() if brand1 else name1
    rest2 = name2.replace(brand2, "").strip() if brand2 else name2
    char_sim = len(set(rest1) & set(rest2)) / len(set(rest1) | set(rest2)) if rest1 and rest2 and (set(rest1) | set(rest2)) else 0.0
    return brand_match * 0.6 + char_sim * 0.4


def is_peak_season(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        for name, (start, end) in PEAK_DATES.items():
            if datetime.strptime(start, "%Y-%m-%d") <= d <= datetime.strptime(end, "%Y-%m-%d"):
                return True, name
    except ValueError:
        pass
    return False, None


def is_weekend(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").weekday() in (4, 5)
    except ValueError:
        return False


def match_hotel_cross_platform(target_name, candidates, threshold=0.35):
    matched = []
    for cand in candidates:
        cand_name = cand.get("name") or cand.get("hotelName") or ""
        score = hotel_name_similarity(target_name, cand_name)
        if score >= threshold:
            matched.append((score, cand))
    matched.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matched]


def book_or_wait(price, city, check_in, check_out, all_prices=None, cancel_policy="", hotel_name=""):
    reasons = []
    signal_scores = []
    tier, brand = (BRAND_TIER.get(extract_brand(hotel_name)), extract_brand(hotel_name)) if hotel_name else (None, "")
    percentile = None

    try:
        checkin_dt = datetime.strptime(check_in, "%Y-%m-%d")
        days_left = (checkin_dt - datetime.now()).days
        is_peak, peak_name = is_peak_season(check_in)
        weekend = is_weekend(check_in)

        if is_peak:
            reasons.append(f"入住日处于{peak_name}旺季，建议尽早预订")
            signal_scores.append(4)
        elif weekend:
            reasons.append("入住日是周末，景区酒店周末更贵")
            signal_scores.append(1)

        if days_left < 1:
            reasons.append("今天入住！立刻预订")
            signal_scores.append(5)
        elif days_left <= 3:
            reasons.append(f"距入住仅{days_left}天，建议尽快预订")
            signal_scores.append(3)
        elif days_left < 7:
            reasons.append(f"距入住{days_left}天，旺季建议立即预订")
            signal_scores.append(1 if not is_peak else 3)
        elif days_left < 14:
            reasons.append(f"距入住{days_left}天，可以对比几天")
            signal_scores.append(0)
        elif days_left < 30:
            reasons.append(f"距入住{days_left}天，可设提醒观望")
            signal_scores.append(-1)
        else:
            reasons.append(f"距入住{days_left}天，建议入住前2-3周再查")
            signal_scores.append(-2)
    except ValueError:
        days_left = None
        is_peak, weekend = False, False

    city_ref = CITY_HOTEL_REF.get(city)
    if city_ref:
        low, mid, high = city_ref
        if tier and tier in TIER_MULTIPLIER:
            mult = TIER_MULTIPLIER[tier]
            tier_low, tier_mid, tier_high = int(low * mult), int(mid * mult), int(high * mult)
        else:
            tier_low, tier_mid, tier_high = low, mid, high
        if tier_high > tier_low:
            percentile = max(0, min(1, (price - tier_low) / (tier_high - tier_low)))
        if percentile is not None:
            if percentile <= 0.25:
                reasons.append(f"当前价¥{price}处于低价区间，明显划算")
                signal_scores.append(3)
            elif percentile < 0.5:
                reasons.append(f"当前价¥{price}低于均价，价格合理")
                signal_scores.append(2)
            elif percentile < 0.75:
                reasons.append(f"当前价¥{price}接近均价，中等水平")
                signal_scores.append(0)
            else:
                reasons.append(f"当前价¥{price}高于均价，偏贵")
                signal_scores.append(-2)

    if all_prices and len(all_prices) > 1:
        max_p, min_p = max(all_prices), min(all_prices)
        if max_p > min_p and max_p > 0:
            spread = (max_p - min_p) / max_p
            if spread > 0.15:
                reasons.append(f"平台价差{int(spread*100)}%，最低价平台优先")
                signal_scores.append(2)
            elif spread < 0.05:
                reasons.append("各平台价格接近，选顺手的订")
                signal_scores.append(0)

    if cancel_policy:
        if "免费取消" in cancel_policy or "免费" in cancel_policy or "限时取消" in cancel_policy:
            reasons.append("取消政策灵活，可以先订再盯")
            signal_scores.append(1)
        elif "不可取消" in cancel_policy or "不退" in cancel_policy:
            reasons.append("不可取消，下单前确认")
            signal_scores.append(-1)

    avg_score = sum(signal_scores) / len(signal_scores) if signal_scores else 0
    if avg_score >= 2:
        signal = "🟢 建议预订"
    elif avg_score >= 0:
        signal = "🟡 可以观望"
    else:
        signal = "🔴 建议等待"

    return {"signal": signal, "score": round(avg_score, 1), "reasons": reasons}


def http_post(url, payload, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_fliggy(city, check_in, check_out, keyword=None):
    try:
        payload = {"type": "hotel_search", "source": "fliggy", "params": {"cityName": city, "checkInDate": check_in, "checkOutDate": check_out, "keyWords": keyword or "", "adultCount": 2}}
        resp = http_post(FLIGGY_PROXY_URL, payload)
        data = resp.get("data", {})
        hotels = data.get("itemList", []) or data.get("hotelList", [])
        results = []
        for h in hotels:
            price = h.get("price", 0)
            if isinstance(price, str):
                price = re.sub(r'[¥￥,\s]', '', price)
                try: price = float(price)
                except: price = 0
            results.append({"name": h.get("name", ""), "price": price if isinstance(price, (int, float)) else 0, "star": h.get("star", ""), "score": h.get("score", ""), "url": h.get("detailUrl", ""), "source": "飞猪"})
        return {"source": "飞猪", "results": results, "error": None}
    except Exception as e:
        return {"source": "飞猪", "results": [], "error": str(e)}


def search_tuniu(city, check_in, check_out, keyword=None):
    try:
        payload = {"type": "tuniu_hotel_search", "params": {"cityName": city, "checkIn": check_in, "checkOut": check_out, "keyword": keyword or city, "adultNum": 2, "roomNum": 1}}
        resp = http_post(TUNIU_PROXY_URL, payload)
        data = resp.get("data", {})
        hotels = data.get("hotels", []) or data.get("hotelList", [])
        results = []
        for h in hotels:
            price = h.get("lowestPrice", h.get("price", 0))
            if isinstance(price, str):
                try: price = float(price)
                except: price = 0
            results.append({"name": h.get("hotelName", h.get("name", "")), "price": price if isinstance(price, (int, float)) else 0, "star": h.get("starName", h.get("star", "")), "score": h.get("commentScore", ""), "source": "途牛"})
        return {"source": "途牛", "results": results, "error": None}
    except Exception as e:
        return {"source": "途牛", "results": [], "error": str(e)}


def compare_fliggy(hotel_name, city, check_in, check_out, adults=2):
    try:
        resp = http_post(FLIGGY_PROXY_URL, {"type": "hotel_search", "source": "fliggy", "params": {"cityName": city, "checkInDate": check_in, "checkOutDate": check_out, "keyWords": hotel_name, "adultCount": adults}})
        data = resp.get("data", {})
        hotels = data.get("itemList", []) or data.get("hotelList", [])
        for h in hotels:
            h_name = h.get("name", "")
            sim = hotel_name_similarity(hotel_name, h_name)
            if sim < 0.3:
                continue
            price = h.get("price", 0)
            if isinstance(price, str):
                price = re.sub(r'[¥￥,\s]', '', price)
                try: price = float(price)
                except: price = 0
            return {"source": "飞猪", "matched": True, "name": h_name, "price": price, "star": h.get("star", ""), "url": h.get("detailUrl", ""), "error": None}
        return {"source": "飞猪", "matched": False, "price": None, "url": None, "error": "未找到匹配酒店"}
    except Exception as e:
        return {"source": "飞猪", "matched": False, "price": None, "url": None, "error": str(e)}


def compare_rg(hotel_name, city, check_in, check_out, adults=2, rooms=1):
    try:
        resp = http_post(HOTEL_PROXY_URL, {"type": "hotel_detail", "source": "rg_detail", "params": {"name": hotel_name, "city": city, "check_in": check_in, "check_out": check_out, "adults": adults, "rooms": rooms}})
        data = resp.get("data", {})
        if data and data.get("success") is not False:
            room_plans = data.get("roomRatePlans", [])
            lowest_price = 0
            cancel_policy = ""
            if room_plans:
                priced_plans = [p for p in room_plans if p.get("totalPrice") and isinstance(p["totalPrice"], (int, float)) and p["totalPrice"] > 0]
                if priced_plans:
                    best_plan = min(priced_plans, key=lambda p: p["totalPrice"])
                    lowest_price = best_plan["totalPrice"]
                    cancel_policies = best_plan.get("cancellationPolicies", [])
                    if cancel_policies:
                        cancel_policy = "; ".join(c.get("description", f"从{c.get('fromDate','')}取消扣款{c.get('amount','')}元") for c in cancel_policies)
            elif data.get("totalPrice"):
                lowest_price = data["totalPrice"]
            return {"source": "RG", "matched": True, "name": data.get("name", hotel_name), "price": lowest_price, "star": data.get("starRating", ""), "url": data.get("bookingUrl", ""), "cancel_policy": cancel_policy, "error": None}
        return {"source": "RG", "matched": False, "price": None, "url": None, "error": "查询失败"}
    except Exception as e:
        return {"source": "RG", "matched": False, "price": None, "url": None, "error": str(e)}


def compare_tuniu(hotel_name, city, check_in, check_out, adults=2, rooms=1):
    try:
        resp = http_post(TUNIU_PROXY_URL, {"type": "tuniu_hotel_detail", "params": {"hotelName": hotel_name, "cityName": city, "checkIn": check_in, "checkOut": check_out}})
        data = resp.get("data", {})
        if data and data.get("hotelName"):
            room_types = data.get("roomTypes", [])
            lowest_price = 0
            cancel_policy = ""
            for rt in room_types:
                for rp in rt.get("ratePlans", []):
                    p = rp.get("rmbPrices") or rp.get("price", 0)
                    if isinstance(p, str):
                        p = re.sub(r'[¥￥,\s]', '', p)
                        try: p = float(p)
                        except: p = 0
                    if p > 0 and (lowest_price == 0 or p < lowest_price):
                        lowest_price = p
                        cancel_policy = rp.get("cancelText", "") or rp.get("cancelDesc", "")
            return {"source": "途牛", "matched": True, "name": data.get("hotelName", hotel_name), "price": lowest_price, "star": data.get("starName", ""), "score": data.get("commentScore", ""), "cancel_policy": cancel_policy, "error": None}
        brand = extract_brand(hotel_name)
        search_keywords = [brand] if brand and brand != hotel_name else []
        for keyword in search_keywords:
            resp = http_post(TUNIU_PROXY_URL, {"type": "tuniu_hotel_search", "params": {"cityName": city, "checkIn": check_in, "checkOut": check_out, "keyword": keyword, "adultNum": adults, "roomNum": rooms}})
            data = resp.get("data", {})
            hotels = data.get("hotels", []) or data.get("hotelList", [])
            matched = match_hotel_cross_platform(hotel_name, hotels)
            if matched:
                best = matched[0]
                price = best.get("lowestPrice", best.get("price", 0))
                if isinstance(price, str):
                    try: price = float(price)
                    except: price = 0
                return {"source": "途牛", "matched": True, "name": best.get("hotelName", ""), "price": price, "error": None}
        return {"source": "途牛", "matched": False, "price": None, "url": None, "error": "未找到匹配酒店"}
    except Exception as e:
        return {"source": "途牛", "matched": False, "price": None, "url": None, "error": str(e)}


def compare_tc(hotel_name, city, check_in, check_out, adults=2):
    try:
        query = f"{city}{hotel_name}酒店{check_in}至{check_out}入住价格"
        resp = http_post(HOTEL_PROXY_URL, {"type": "deeptrip_search", "source": "tongcheng", "params": {"q": query}})
        data = resp.get("data", {})
        text = data.get("text", "")
        prices = re.findall(r'[¥￥](\d+(?:[,.]\d+)?)', text)
        price = 0
        if prices:
            try: price = float(prices[0].replace(",", ""))
            except: price = 0
        links = data.get("产品跳转链接", {})
        url = ""
        for name, link_obj in links.items():
            if hotel_name[:4] in name:
                url = link_obj.get("手机链接", link_obj.get("PC链接", "")) if isinstance(link_obj, dict) else str(link_obj)
                break
        if price > 0:
            return {"source": "同程", "matched": True, "name": hotel_name, "price": price, "url": url, "error": None}
        return {"source": "同程", "matched": False, "price": None, "url": url, "error": "未提取到价格"}
    except Exception as e:
        return {"source": "同程", "matched": False, "price": None, "url": None, "error": str(e)}


# ============ MCP 工具 ============
@mcp.tool()
def search(city: str, check_in: str, check_out: str, keyword: str = "") -> str:
    """搜索城市酒店列表，合并飞猪和途牛结果并去重，附带订房建议。

    Args:
        city: 城市名，如：上海、北京
        check_in: 入住日期，格式YYYY-MM-DD
        check_out: 离店日期，格式YYYY-MM-DD
        keyword: 搜索关键词/地标，如：外滩、迪士尼
    """
    fliggy_result = search_fliggy(city, check_in, check_out, keyword or None)
    tuniu_result = search_tuniu(city, check_in, check_out, keyword or None)

    hotels, seen = [], []
    for src in [tuniu_result, fliggy_result]:
        for h in src.get("results", []):
            h_name = h.get("name", "")
            if not any(hotel_name_similarity(h_name, s) > 0.7 for s in seen):
                hotels.append(h)
                seen.append(h_name)

    hotels.sort(key=lambda x: x.get("price", 999999) if isinstance(x.get("price"), (int, float)) and x.get("price", 0) > 0 else 999999)

    lowest = next((h for h in hotels if isinstance(h.get("price"), (int, float)) and h["price"] > 0), None)
    advice = None
    if lowest:
        all_prices = [h["price"] for h in hotels if isinstance(h.get("price"), (int, float)) and h["price"] > 0]
        advice = book_or_wait(lowest["price"], city, check_in, check_out, all_prices, lowest.get("cancel_policy", ""), lowest.get("name", ""))

    return json.dumps({
        "success": True, "city": city, "check_in": check_in, "check_out": check_out,
        "count": len(hotels), "hotels": hotels[:20],
        "lowest_price": lowest["price"] if lowest else None,
        "lowest_hotel": lowest["name"] if lowest else None,
        "lowest_url": lowest.get("url", "") if lowest else "",
        "advice": advice,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def calendar(city: str, keyword: str = "", start_date: str = "", nights: int = 1, days: int = 14) -> str:
    """酒店低价日历，扫描多入住日期的酒店价格。

    Args:
        city: 城市名
        keyword: 搜索关键词/地标
        start_date: 起始入住日期，格式YYYY-MM-DD
        nights: 住几晚，默认1
        days: 扫描天数，最多30，默认14
    """
    days = min(days, 30)
    kw = keyword or city
    cal = []
    for i in range(days):
        try:
            d = datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)
            ci = d.strftime("%Y-%m-%d")
            co = (d + timedelta(days=nights)).strftime("%Y-%m-%d")
        except ValueError:
            continue
        result = search_fliggy(city, ci, co, keyword=kw)
        hotels = result.get("results", [])
        if hotels:
            prices = [h["price"] for h in hotels if isinstance(h.get("price"), (int, float)) and h["price"] > 0]
            lowest = min(prices) if prices else None
            best = next((h for h in hotels if isinstance(h.get("price"), (int, float)) and h["price"] == lowest), None)
            cal.append({"date": ci, "weekday": ["周一","周二","周三","周四","周五","周六","周日"][d.weekday()], "lowest_price": lowest, "cheapest_hotel": best["name"] if best else None, "url": best.get("url", "") if best else ""})
        else:
            cal.append({"date": ci, "weekday": ["周一","周二","周三","周四","周五","周六","周日"][d.weekday()], "lowest_price": None})
        time.sleep(0.3)

    priced_days = [d for d in cal if d.get("lowest_price")]
    if priced_days:
        min_price = min(d["lowest_price"] for d in priced_days)
        avg_price = sum(d["lowest_price"] for d in priced_days) / len(priced_days)
        for d in cal:
            p = d.get("lowest_price")
            d["tag"] = "🟢 低价" if p and p <= min_price * 1.05 else ("🟡 适中" if p and p <= avg_price else ("🔴 偏贵" if p else "— 无数据"))
        cheapest = min(priced_days, key=lambda x: x["lowest_price"])
        advice = book_or_wait(cheapest["lowest_price"], city, cheapest["date"], (datetime.strptime(cheapest["date"], "%Y-%m-%d") + timedelta(days=nights)).strftime("%Y-%m-%d"), [d["lowest_price"] for d in priced_days], "", cheapest.get("cheapest_hotel", ""))
    else:
        min_price = avg_price = None
        advice = None
        cheapest = None

    return json.dumps({
        "success": True, "city": city, "start_date": start_date, "nights": nights, "days": days,
        "calendar": cal, "min_price": min_price, "avg_price": int(avg_price) if avg_price else None,
        "cheapest_date": cheapest["date"] if cheapest else None, "advice": advice,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def advisor(hotel: str, city: str, check_in: str, check_out: str) -> str:
    """指定酒店多平台精确比价+订房决策建议。

    Args:
        hotel: 酒店名称，如：上海外滩华尔道夫
        city: 城市名
        check_in: 入住日期，格式YYYY-MM-DD
        check_out: 离店日期，格式YYYY-MM-DD
    """
    results = [
        compare_fliggy(hotel, city, check_in, check_out),
        compare_rg(hotel, city, check_in, check_out),
        compare_tuniu(hotel, city, check_in, check_out),
        compare_tc(hotel, city, check_in, check_out),
    ]

    priced = [r for r in results if r.get("matched") and r.get("price") and isinstance(r["price"], (int, float)) and r["price"] > 0]
    commission_order = {"RG": 0, "飞猪": 1, "途牛": 2, "同程": 3}
    priced.sort(key=lambda x: (x["price"], commission_order.get(x.get("source", ""), 9)))
    all_sorted = priced + [r for r in results if r not in priced]

    advice = None
    if priced:
        all_prices = [r["price"] for r in priced]
        cancel = priced[0].get("cancel_policy", "")
        advice = book_or_wait(priced[0]["price"], city, check_in, check_out, all_prices, cancel, hotel)

    return json.dumps({
        "success": True, "hotel_name": hotel, "city": city, "check_in": check_in, "check_out": check_out,
        "platforms": all_sorted,
        "lowest_price": priced[0]["price"] if priced else None,
        "lowest_platform": priced[0]["source"] if priced else None,
        "lowest_url": priced[0].get("url") if priced else None,
        "advice": advice,
    }, ensure_ascii=False, indent=2)


def main():
    """酒店聪明订 MCP服务入口"""
    mcp.run()


if __name__ == "__main__":
    main()
