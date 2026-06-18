"""
数据采集模块
============
从天天基金(公开API)获取基金净值数据
从新浪/雅虎获取市场指数数据
"""

import requests
import json
from datetime import datetime, timedelta
from config import FUNDS, INDICES


def _get_headers():
    """获取通用请求头"""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "http://fund.eastmoney.com/",
    }


def fetch_fund_nav_history(fund_code, days=30):
    """
    从天天基金API获取基金净值历史数据

    参数:
        fund_code: 基金代码
        days: 获取最近多少天的数据

    返回:
        list[dict] 或 None
        每项: {"date": "2026-06-17", "nav": 1.6520, "acc_nav": 1.6520, "daily_change": 0.25}
    """
    url = "http://api.fund.eastmoney.com/f10/lsjz"
    params = {
        "fundCode": fund_code,
        "pageIndex": 1,
        "pageSize": days,
        "callback": "",
    }

    try:
        resp = requests.get(url, params=params, headers=_get_headers(), timeout=15)
        data = resp.json()

        records = data.get("Data", {}).get("LSJZList", [])
        if not records:
            print(f"   ⚠️ {fund_code}: API返回数据为空")
            return None

        # 解析并过滤有效数据
        result = []
        for r in records:
            nav_str = r.get("DWJZ", "")
            change_str = r.get("JZZZL", "")

            # 跳过空净值（QDII基金在非更新日可能为空）
            if not nav_str:
                continue

            result.append({
                "date": r.get("FSRQ", ""),
                "nav": float(nav_str) if nav_str else 0,
                "acc_nav": float(r.get("LJJZ", nav_str)) if r.get("LJJZ") else float(nav_str),
                "daily_change": float(change_str) if change_str else 0.0,
            })

        if not result:
            print(f"   ⚠️ {fund_code}: 解析后无有效净值数据")
            return None

        # 按日期从小到大排列
        result.sort(key=lambda x: x["date"])
        print(f"   ✅ 获取到 {len(result)} 条净值记录 (最新: {result[-1]['date']})")
        return result

    except requests.exceptions.Timeout:
        print(f"   ❌ {fund_code}: 请求超时")
    except json.JSONDecodeError:
        print(f"   ❌ {fund_code}: 返回数据格式异常")
    except Exception as e:
        print(f"   ❌ {fund_code}: 获取失败 - {e}")

    return None


def extract_latest_from_history(history):
    """
    从净值历史记录中提取最新数据摘要
    （避免重复调用API）

    参数:
        history: fetch_fund_nav_history 的返回值

    返回:
        dict 或 None
    """
    if not history or len(history) < 2:
        return None

    latest = history[-1]
    prev = history[-2]
    week_data = history[-5:] if len(history) >= 5 else history
    navs = [d["nav"] for d in week_data if d["nav"] > 0]

    return {
        "date": latest["date"],
        "nav": latest["nav"],
        "acc_nav": latest["acc_nav"],
        "daily_change": latest["daily_change"],
        "prev_nav": prev["nav"],
        "week_high": max(navs) if navs else 0,
        "week_low": min(navs) if navs else 0,
    }


def fetch_latest_nav(fund_code):
    """
    获取基金最新净值（含日涨跌幅）
    直接调用 fetch_fund_nav_history 并从中提取摘要

    返回:
        dict 或 None
    """
    history = fetch_fund_nav_history(fund_code, days=20)
    return extract_latest_from_history(history)


def _parse_sina_hk_index(raw_text):
    """
    解析新浪财经港股指数数据

    示例:
        var hq_str_hkHSI="HSI,恒生指数,24145.190,24312.160,24163.250,23749.990,23924.811,-387.350,-1.593,..."
        字段: 英文名,中文名,当前价,昨收,开盘,最高,最低,涨跌额,涨跌幅,...
    """
    try:
        start = raw_text.index('"') + 1
        end = raw_text.rindex('"')
        parts = raw_text[start:end].split(",")
        if len(parts) < 10:
            return None
        current_price = float(parts[2])
        prev_close = float(parts[3])
        change_pct = float(parts[8]) if parts[8] else 0
        if current_price:
            return {
                "close": round(current_price, 2),
                "change": round(change_pct, 2),
            }
    except (ValueError, IndexError, ValueError):
        pass
    return None


def _parse_sina_us_index(raw_text):
    """
    解析新浪财经美股指数数据（备用，可能因时段返回空）
    """
    try:
        start = raw_text.index('"') + 1
        end = raw_text.rindex('"')
        content = raw_text[start:end]
        if not content:
            return None
        parts = content.split(",")
        if len(parts) < 6:
            return None
        # 美股格式: "名称,今开,昨收,当前价,最高,最低,..."
        current_price = float(parts[3]) if parts[3] else 0
        prev_close = float(parts[2]) if parts[2] else 0
        if current_price and prev_close:
            change = (current_price - prev_close) / prev_close * 100
            return {
                "close": round(current_price, 2),
                "change": round(change, 2),
            }
    except (ValueError, IndexError):
        pass
    return None


def fetch_market_indices():
    """
    获取主要市场指数的最新行情

    使用东方财富API（A股）+ 新浪财经API（港股/全球）

    返回:
        dict: {"指数名称": {"close": xxx, "change": xx%, "date": "..."}}
    """
    indices = {}

    # ----- A股指数：沪深300（从东方财富获取） -----
    try:
        url = "http://push2.eastmoney.com/api/qt/ulist.np/get"
        params = {
            "fltt": 2,
            "fields": "f2,f3,f4,f12,f14",
            "secids": "1.000300",
        }
        resp = requests.get(url, params=params, headers=_get_headers(), timeout=10)
        data = resp.json()
        if data.get("data") and data["data"].get("diff"):
            item = data["data"]["diff"][0]
            close_val = item.get("f2", 0)
            change_val = item.get("f3", 0)
            if close_val:
                indices["沪深300"] = {
                    "close": close_val,
                    "change": change_val if change_val else 0,
                }
                print(f"   ✅ 沪深300: {close_val} ({change_val:+.2f}%)")
    except Exception as e:
        print(f"   ⚠️ 沪深300获取失败: {e}")

    # ----- 港股指数：恒生指数（从新浪财经获取） -----
    try:
        url = "http://hq.sinajs.cn/list=hkHSI"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "gbk"
        idx_data = _parse_sina_hk_index(resp.text)
        if idx_data:
            indices["恒生指数"] = idx_data
            print(f"   ✅ 恒生指数: {idx_data['close']} ({idx_data['change']:+.2f}%)")
    except Exception as e:
        print(f"   ⚠️ 恒生指数获取失败: {e}")

    # ----- 美股指数：标普500 -----
    # 先尝试新浪财经（美盘时段有数据）
    try:
        url = "http://hq.sinajs.cn/list=gb_%5EGSPC"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn",
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "gbk"
        idx_data = _parse_sina_us_index(resp.text)
        if idx_data:
            indices["标普500"] = idx_data
            print(f"   ✅ 标普500: {idx_data['close']} ({idx_data['change']:+.2f}%)")
    except Exception as e:
        print(f"   ⚠️ 标普500新浪接口失败: {e}")

    # 如果新浪没有数据，尝试用 yfinance（需要安装 yfinance 包）
    if "标普500" not in indices:
        try:
            import yfinance as yf
            spx = yf.Ticker("^GSPC")
            hist = spx.history(period="5d")
            if hist is not None and len(hist) >= 2:
                latest = hist.iloc[-1]
                prev = hist.iloc[-2]
                change = (float(latest["Close"]) - float(prev["Close"])) / float(prev["Close"]) * 100
                indices["标普500"] = {
                    "close": round(float(latest["Close"]), 2),
                    "change": round(change, 2),
                }
                print(f"   ✅ 标普500(yfinance): {indices['标普500']['close']} ({indices['标普500']['change']:+.2f}%)")
        except Exception as e:
            print(f"   ⚠️ 标普500(yfinance)获取失败: {e}")

    return indices


def check_alert(fund_name, fund_code, daily_change):
    """
    检查是否需要发送跌幅预警

    返回:
        bool: 是否触发预警
    """
    if daily_change is None:
        return False
    return daily_change <= -3.0


if __name__ == "__main__":
    """测试数据采集功能"""
    print("=" * 50)
    print("🔧 数据采集模块自测")
    print("=" * 50)

    for fund in FUNDS:
        print(f"\n📌 {fund['name']} ({fund['code']})")
        latest = fetch_latest_nav(fund["code"])
        if latest:
            print(f"   最新净值: {latest['nav']:.4f} (日期: {latest['date']})")
            print(f"   日涨跌: {latest['daily_change']:+.2f}%")
            print(f"   近5日最高: {latest['week_high']:.4f}")
            print(f"   近5日最低: {latest['week_low']:.4f}")
        else:
            print("   ❌ 获取失败")

    print("\n📌 市场指数")
    indices = fetch_market_indices()
    for name, data in indices.items():
        print(f"   {name}: {data}")
