"""
报告生成模块
============
生成可视化 HTML 基金日报
"""

import json
from datetime import datetime
from config import FUNDS


def _build_chart_data(history):
    """从净值历史数据中提取图表数据"""
    if not history or len(history) < 3:
        return None
    return {
        "dates": json.dumps([d["date"][5:] for d in history]),  # "MM-DD" 格式
        "navs": json.dumps([d["nav"] for d in history]),
    }


def _change_class(value):
    """根据涨跌幅返回CSS样式类"""
    if value is None:
        return "flat"
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def _change_icon(value):
    """涨跌幅图标"""
    if value is None:
        return "➡️"
    if value > 0:
        return "📈"
    if value < 0:
        return "📉"
    return "➡️"


def _format_change(value):
    """格式化涨跌幅"""
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _safe_val(value, default="N/A"):
    """安全取值"""
    if value is None:
        return default
    return str(value)


def generate_html_report(funds_data, market_data, fund_analyses, market_overview):
    """
    生成完整的HTML日报

    参数:
        funds_data: list, 基金数据 [{name, code, data, history}]
        market_data: dict, 市场指数数据
        fund_analyses: list[str], AI对每只基金的分析
        market_overview: str, 市场整体分析

    返回:
        str: 完整HTML内容
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")

    # ---- 市场指数区块 ----
    market_html = ""
    for name, data in market_data.items():
        if isinstance(data, dict) and "change" in data:
            change = data.get("change", 0)
            cls = _change_class(change)
            close_val = data.get("close", "N/A")
            market_html += f"""
            <div class="index-item">
                <span class="index-name">{name}</span>
                <span class="index-value">{close_val}</span>
                <span class="index-change {cls}">{_format_change(change)}</span>
            </div>"""

    # ---- 基金卡片区块 ----
    fund_cards = ""
    charts_js = ""
    chart_index = 0

    for fund in funds_data:
        d = fund.get("data")
        code = fund["code"]
        name = fund["name"]

        # 无数据时的占位
        if not d:
            fund_cards += f"""
            <div class="fund-card">
                <div class="fund-header"><h3>{name}</h3><span class="fund-code">{code}</span></div>
                <p class="no-data">暂无最新净值数据（QDII基金净值更新可能延迟1-2天）</p>
            </div>"""
            continue

        change = d.get("daily_change", 0)
        cls = _change_class(change)
        icon = _change_icon(change)

        # 跌幅预警标签
        alert_badge = ""
        if change is not None and change <= -3:
            alert_badge = '<span class="alert-badge">⚠️ 跌幅超3%</span>'

        # 涨跌方向箭头(用于净值比较)
        prev_nav = d.get("prev_nav")
        nav_trend = ""
        if prev_nav and d.get("nav"):
            if d["nav"] > prev_nav:
                nav_trend = "↑"
            elif d["nav"] < prev_nav:
                nav_trend = "↓"

        fund_cards += f"""
        <div class="fund-card">
            <div class="fund-header">
                <div><h3>{name}</h3><span class="fund-code">{code}</span></div>
                {alert_badge}
            </div>
            <div class="fund-info-grid">
                <div class="fund-metric">
                    <span class="metric-label">最新净值</span>
                    <span class="metric-value">{_safe_val(d.get('nav'))} {nav_trend}</span>
                </div>
                <div class="fund-metric">
                    <span class="metric-label">日涨跌幅</span>
                    <span class="metric-value {cls}">{icon} {_format_change(change)}</span>
                </div>
                <div class="fund-metric">
                    <span class="metric-label">净值日期</span>
                    <span class="metric-value date-label">{_safe_val(d.get('date'))}</span>
                </div>
                <div class="fund-metric">
                    <span class="metric-label">近5日最高</span>
                    <span class="metric-value">{_safe_val(d.get('week_high'))}</span>
                </div>
                <div class="fund-metric">
                    <span class="metric-label">近5日最低</span>
                    <span class="metric-value">{_safe_val(d.get('week_low'))}</span>
                </div>
                <div class="fund-metric">
                    <span class="metric-label">累计净值</span>
                    <span class="metric-value">{_safe_val(d.get('acc_nav'))}</span>
                </div>
            </div>
            <canvas id="chart-{chart_index}" class="fund-chart"></canvas>
        </div>"""

        # 图表数据
        chart_data = _build_chart_data(fund.get("history"))
        if chart_data:
            charts_js += f"""
    new Chart(document.getElementById('chart-{chart_index}').getContext('2d'), {{
        type: 'line',
        data: {{
            labels: {chart_data['dates']},
            datasets: [{{
                label: '单位净值',
                data: {chart_data['navs']},
                borderColor: '#4F46E5',
                backgroundColor: 'rgba(79, 70, 229, 0.08)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                pointBackgroundColor: '#4F46E5',
                borderWidth: 2,
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{
                x: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 10 }} }} }},
                y: {{ grid: {{ color: 'rgba(0,0,0,0.05)' }}, ticks: {{ font: {{ size: 10 }} }} }}
            }}
        }}
    }});"""
            chart_index += 1

    # ---- AI分析区块 ----
    analysis_html = ""
    for i, fund in enumerate(funds_data):
        analysis = fund_analyses[i] if i < len(fund_analyses) else ""
        if analysis:
            # 将分析文本中的【标题】转为HTML高亮
            formatted = analysis.replace("\n", "<br>")
            import re
            formatted = re.sub(r"【(.+?)】", r'<span class="analysis-tag">【\1】</span>', formatted)
            analysis_html += f"""
            <div class="analysis-card">
                <h3 class="analysis-title">🔍 {fund['name']}</h3>
                <div class="analysis-body">{formatted}</div>
            </div>"""

    # ---- 大盘分析区块 ----
    overview_html = ""
    if market_overview:
        formatted = market_overview.replace("\n", "<br>")
        import re
        formatted = re.sub(r"【(.+?)】", r'<span class="analysis-tag">【\1】</span>', formatted)
        overview_html = f"""
        <div class="overview-card">
            <h3 class="analysis-title">🌤️ 大盘风向</h3>
            <div class="analysis-body">{formatted}</div>
        </div>"""

    # ============ 完整HTML ============
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基金日报 - {today}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
            background: #f0f2f5;
            color: #1f2937;
        }}
        .container {{ max-width: 820px; margin: 0 auto; padding: 16px; }}

        /* 头部 */
        .header {{
            background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
            color: white;
            padding: 28px 24px;
            border-radius: 16px;
            margin-bottom: 20px;
        }}
        .header h1 {{ font-size: 26px; font-weight: 700; margin-bottom: 4px; }}
        .header .subtitle {{ opacity: 0.85; font-size: 14px; }}
        .header .badge-row {{ margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap; }}
        .badge {{
            background: rgba(255,255,255,0.2); border-radius: 20px;
            padding: 3px 12px; font-size: 12px; display: inline-block;
        }}

        /* 通用卡片 */
        .card {{
            background: white; border-radius: 14px; padding: 20px;
            margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .section-title {{
            font-size: 17px; font-weight: 600; margin: 20px 0 12px;
            color: #374151; padding-left: 12px;
            border-left: 3px solid #4F46E5;
        }}

        /* 市场指数 */
        .market-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }}
        .index-item {{
            background: #f8fafc; border-radius: 10px; padding: 12px 16px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .index-name {{ font-weight: 500; font-size: 14px; color: #374151; }}
        .index-value {{ color: #6B7280; font-size: 14px; }}
        .index-change {{ font-weight: 700; font-size: 15px; }}

        /* 基金卡片 */
        .fund-card {{ background: white; border-radius: 14px; padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }}
        .fund-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }}
        .fund-header h3 {{ font-size: 16px; font-weight: 600; }}
        .fund-code {{ color: #9CA3AF; font-size: 12px; }}
        .fund-info-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 14px; }}
        .fund-metric {{ text-align: center; }}
        .metric-label {{ display: block; font-size: 11px; color: #9CA3AF; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 20px; font-weight: 700; }}
        .metric-value.date-label {{ font-size: 14px; font-weight: 500; color: #6B7280; }}
        .fund-chart {{ width: 100% !important; height: 180px !important; }}
        .alert-badge {{
            background: #FEF2F2; color: #DC2626; padding: 4px 12px;
            border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap;
        }}
        .no-data {{ color: #9CA3AF; text-align: center; padding: 20px; font-size: 14px; }}

        /* 颜色 */
        .up {{ color: #DC2626; }}   /* 红色涨（中国惯例） */
        .down {{ color: #059669; }} /* 绿色跌 */
        .flat {{ color: #6B7280; }}

        /* AI分析 */
        .analysis-card, .overview-card {{
            background: white; border-radius: 14px; padding: 20px;
            margin-bottom: 14px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        }}
        .analysis-title {{ font-size: 15px; font-weight: 600; margin-bottom: 12px; color: #374151; }}
        .analysis-body {{ line-height: 1.9; color: #374151; font-size: 14px; }}
        .analysis-tag {{ color: #4F46E5; font-weight: 600; }}

        /* 底部 */
        .footer {{
            text-align: center; color: #9CA3AF; font-size: 11px;
            margin-top: 30px; padding: 20px; line-height: 1.8;
        }}

        /* 移动端适配 */
        @media (max-width: 480px) {{
            .fund-info-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .market-grid {{ grid-template-columns: 1fr; }}
            .header h1 {{ font-size: 22px; }}
        }}
    </style>
</head>
<body>
    <div class="container">

        <!-- 头部 -->
        <div class="header">
            <h1>📊 基金日报</h1>
            <div class="subtitle">{now} · 数据来源: 天天基金</div>
            <div class="badge-row">
                <span class="badge">🤖 AI辅助分析</span>
                <span class="badge">📱 推送到微信</span>
            </div>
        </div>

        <!-- 市场指数 -->
        <h2 class="section-title">📈 市场指数</h2>
        <div class="card">
            <div class="market-grid">
                {market_html}
            </div>
        </div>

        <!-- 基金表现 -->
        <h2 class="section-title">💰 基金表现</h2>
        {fund_cards}

        <!-- 大盘风向标 (AI) -->
        {overview_html}

        <!-- AI深度分析 -->
        <h2 class="section-title">🔍 AI 深度分析</h2>
        {analysis_html}

        <!-- 底部 -->
        <div class="footer">
            <p>本报告由 AI 辅助生成，仅供参考，不构成投资建议。</p>
            <p>基金有风险，投资需谨慎。过往业绩不代表未来表现。</p>
            <p style="margin-top:8px;">
                <a href="https://github.com/FMR0304/fund-analyzer" style="color:#4F46E5;text-decoration:none;">
                    ⚡ 自动生成
                </a>
                · {now}
            </p>
        </div>

    </div>

    <script>
    {charts_js}
    </script>
</body>
</html>"""

    return html


def save_report(html_content, report_name=None):
    """
    保存HTML报告到output目录

    参数:
        html_content: HTML字符串
        report_name: 文件名（不含路径），默认为 report_YYYYMMDD.html

    返回:
        str: 保存的文件路径
    """
    from pathlib import Path
    from config import OUTPUT_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not report_name:
        report_name = f"report_{datetime.now().strftime('%Y%m%d')}.html"

    # 保存日期版本
    dated_path = OUTPUT_DIR / report_name
    with open(dated_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"   📄 报告已保存: {dated_path}")

    # 同时覆盖 latest.html（方便GitHub Pages展示最新报告）
    latest_path = OUTPUT_DIR / "latest.html"
    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(dated_path)


if __name__ == "__main__":
    """测试报告生成"""
    print("🔧 报告生成模块自测")

    test_funds = [
        {
            "name": "摩根标普500指数(QDII)人民币A",
            "code": "017641",
            "data": {
                "date": "2026-06-17",
                "nav": 1.6520,
                "acc_nav": 1.6520,
                "daily_change": 0.85,
                "prev_nav": 1.6380,
                "week_high": 1.67,
                "week_low": 1.62,
            },
            "history": [
                {"date": "2026-06-11", "nav": 1.6200, "acc_nav": 1.6200, "daily_change": 0.1},
                {"date": "2026-06-12", "nav": 1.6350, "acc_nav": 1.6350, "daily_change": 0.93},
                {"date": "2026-06-13", "nav": 1.6380, "acc_nav": 1.6380, "daily_change": 0.18},
                {"date": "2026-06-16", "nav": 1.6380, "acc_nav": 1.6380, "daily_change": 0.0},
                {"date": "2026-06-17", "nav": 1.6520, "acc_nav": 1.6520, "daily_change": 0.85},
            ],
        },
        {
            "name": "富国全球科技互联网股票(QDII)C",
            "code": "022184",
            "data": {
                "date": "2026-06-16",
                "nav": 1.1240,
                "acc_nav": 1.1240,
                "daily_change": -1.24,
                "prev_nav": 1.1380,
                "week_high": 1.15,
                "week_low": 1.11,
            },
            "history": [
                {"date": "2026-06-10", "nav": 1.1300, "acc_nav": 1.1300, "daily_change": -0.5},
                {"date": "2026-06-11", "nav": 1.1280, "acc_nav": 1.1280, "daily_change": -0.18},
                {"date": "2026-06-12", "nav": 1.1380, "acc_nav": 1.1380, "daily_change": 0.89},
                {"date": "2026-06-13", "nav": 1.1380, "acc_nav": 1.1380, "daily_change": 0.0},
                {"date": "2026-06-16", "nav": 1.1240, "acc_nav": 1.1240, "daily_change": -1.24},
            ],
        },
    ]

    test_market = {
        "沪深300": {"close": 3850.23, "change": 0.65},
        "恒生指数": {"close": 18500.42, "change": -0.32},
        "标普500": {"close": 5482.15, "change": 0.28},
    }

    test_analyses = [
        "【今日表现】标普500指数近期持续走强，今日上涨0.85%，受益于科技板块带动。\n【趋势判断】短期维持震荡上行格局，美联储政策预期为市场提供支撑。\n【持仓建议】继续持有。美股基本面稳健，中长期配置价值显著。\n【风险提示】关注通胀数据和美联储利率决议对市场的影响。",
        "【今日表现】受美股科技股回调影响，该基金今日下跌1.24%。\n【趋势判断】短期可能继续震荡调整，但AI和科技长期趋势不变。\n【持仓建议】观望为宜，可在回调至低位时考虑分批加仓。\n【风险提示】全球科技监管风险及估值回调压力。",
    ]

    test_overview = (
        "【大盘风向】今日A股震荡偏强，港股小幅回调，美股维持强势。\n"
        "【组合评价】当前全球科技+标普500的组合整体布局于海外优质资产，"
        "风格偏成长，与A股相关性低，具备分散配置价值。\n"
        "【操作策略】建议维持现有仓位，若市场出现明显回调可适度加仓。"
    )

    html = generate_html_report(test_funds, test_market, test_analyses, test_overview)
    saved = save_report(html)
    print(f"   ✅ 测试报告已生成: {saved}")
