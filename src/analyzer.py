"""
AI分析模块
===========
调用 DeepSeek API 对基金数据进行智能分析
"""

import json
import requests
from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL, DEEPSEEK_MODEL


def _call_deepseek(system_prompt, user_prompt, max_tokens=1200):
    """
    调用 DeepSeek API

    参数:
        system_prompt: 系统角色设定
        user_prompt: 用户问题/数据
        max_tokens: 最大输出token数

    返回:
        str: AI回复文本
    """
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未配置 DeepSeek API Key，请在 GitHub Secrets 中添加 DEEPSEEK_API_KEY"

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "⚠️ AI分析请求超时，请稍后重试"
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        if status == 401:
            return "⚠️ DeepSeek API Key 无效，请检查密钥是否正确"
        elif status == 429:
            return "⚠️ API调用频率超限，请稍后重试"
        else:
            return f"⚠️ API请求失败 (HTTP {status})"
    except Exception as e:
        return f"⚠️ AI分析异常: {str(e)}"


def analyze_fund(fund_name, fund_code, fund_data, market_data):
    """
    对单只基金进行AI分析

    参数:
        fund_name: 基金名称
        fund_code: 基金代码
        fund_data: 基金最新数据 (dict, 含nav/daily_change等)
        market_data: 市场指数数据 (dict)

    返回:
        str: 分析文本
    """
    nav = fund_data.get("nav", "N/A")
    daily_change = fund_data.get("daily_change", "N/A")
    date = fund_data.get("date", "N/A")
    week_high = fund_data.get("week_high", "N/A")
    week_low = fund_data.get("week_low", "N/A")

    # 格式化市场数据
    market_str = "\n".join([
        f"- {name}: {data.get('close', 'N/A')} (涨跌: {data.get('change', 'N/A'):+.2f}%)"
        for name, data in market_data.items()
        if isinstance(data, dict) and "change" in data
    ])

    system_prompt = (
        "你是一位专业的公募基金分析师，具有10年以上证券投资分析经验。"
        "你的分析风格：简洁专业、数据支撑、客观理性。"
        "回答要结构清晰，用中文，每部分用【】标注标题。"
        "注意：基金过往表现不代表未来收益，请在分析末尾提示风险。"
    )

    user_prompt = f"""请对以下基金进行今日分析：

## 基金信息
- 名称：{fund_name}（{fund_code}）
- 最新净值日期：{date}
- 最新单位净值：{nav}
- 日涨跌幅：{daily_change}%
- 近5日最高：{week_high}
- 近5日最低：{week_low}

## 今日市场环境
{market_str if market_str else "暂无市场数据"}

请输出以下内容（200-350字）：
【今日表现】简述该基金今日走势及原因分析
【趋势判断】基于近期走势的短期趋势判断
【持仓建议】给出明确的建议：持有/加仓/减仓/观望，并说明核心理由
【风险提示】当前需要关注的风险点"""

    return _call_deepseek(system_prompt, user_prompt)


def analyze_market_overview(funds_data, market_data):
    """
    分析整体市场风向和组合建议

    参数:
        funds_data: list of dict, 每项含name/code/data
        market_data: dict, 市场指数数据

    返回:
        str: 市场分析文本
    """
    fund_lines = []
    for fund in funds_data:
        d = fund.get("data")
        if d:
            fund_lines.append(
                f"- {fund['name']}: 净值{d.get('nav', 'N/A')}, "
                f"日涨跌{d.get('daily_change', 'N/A'):+.2f}%"
            )

    market_lines = [
        f"- {name}: {data.get('close', 'N/A')} ({data.get('change', 'N/A'):+.2f}%)"
        for name, data in market_data.items()
        if isinstance(data, dict) and "change" in data
    ]

    system_prompt = (
        "你是一位专业的资产配置分析师，擅长宏观经济分析和组合管理。"
        "风格简洁专业，用中文回答。分析时注意平衡风险和收益。"
    )

    user_prompt = f"""请分析今日整体市场和给出组合建议：

## 基金组合表现
{"".join(fund_lines)}

## 市场指数表现
{"".join(market_lines) if market_lines else "暂无市场数据"}

请输出（200-300字）：
【大盘风向】今日整体市场环境解读
【组合评价】对当前持有的全球科技+标普500组合的适配性评价
【操作策略】未来1-2周适合的操作策略建议"""

    return _call_deepseek(system_prompt, user_prompt)


if __name__ == "__main__":
    """测试AI分析功能"""
    print("=" * 50)
    print("🔧 AI分析模块自测")
    print("=" * 50)

    test_fund_data = {
        "date": "2026-06-17",
        "nav": 1.6520,
        "daily_change": 0.85,
        "week_high": 1.67,
        "week_low": 1.62,
    }
    test_market = {
        "沪深300": {"close": 3850.23, "change": 0.65},
        "恒生指数": {"close": 18500.42, "change": -0.32},
    }

    print("\n📌 单基金分析测试")
    result = analyze_fund("摩根标普500指数(QDII)A", "017641", test_fund_data, test_market)
    print(result)

    print("\n📌 市场分析测试")
    overview = analyze_market_overview(
        [{"name": "摩根标普500", "code": "017641", "data": test_fund_data}],
        test_market,
    )
    print(overview)
