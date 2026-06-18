"""
推送通知模块
============
通过 PushPlus 将报告和预警推送到微信
"""

import requests
from config import PUSHPLUS_TOKEN, PUSHPLUS_URL, ALERT_THRESHOLD


def send_notification(title, html_content, content_type="html"):
    """
    通过 PushPlus 发送微信推送

    参数:
        title: 推送标题（显示在微信消息中）
        html_content: HTML格式的内容
        content_type: 内容类型，默认 "html"

    返回:
        bool: 是否成功
    """
    if not PUSHPLUS_TOKEN:
        print("   ⚠️ 未配置 PUSHPLUS_TOKEN，跳过推送")
        return False

    payload = {
        "token": PUSHPLUS_TOKEN,
        "title": title,
        "content": html_content,
        "template": content_type,
    }

    try:
        resp = requests.post(PUSHPLUS_URL, json=payload, timeout=15)
        result = resp.json()

        if result.get("code") == 200:
            print(f"   ✅ 推送成功: {title}")
            return True
        else:
            msg = result.get("msg", "未知错误")
            print(f"   ❌ 推送失败: {msg}")
            return False

    except requests.exceptions.Timeout:
        print("   ❌ 推送超时，请检查网络")
    except requests.exceptions.ConnectionError:
        print("   ❌ 推送连接失败，请检查网络")
    except Exception as e:
        print(f"   ❌ 推送异常: {e}")

    return False


def send_daily_report(html_content):
    """
    发送每日基金日报

    参数:
        html_content: 完整的HTML报告内容
    """
    from datetime import datetime
    title = f"📊 基金日报 {datetime.now().strftime('%m-%d')}"
    return send_notification(title, html_content)


def send_alert(fund_name, fund_code, daily_change, nav=None):
    """
    发送跌幅预警（单日跌幅超过3%）

    参数:
        fund_name: 基金名称
        fund_code: 基金代码
        daily_change: 日涨跌幅（%）
        nav: 当前净值（可选）
    """
    if daily_change is None:
        return False

    if daily_change > ALERT_THRESHOLD:
        return False  # 未触发预警

    title = f"⚠️ 基金预警: {fund_name}"

    nav_text = f"当前净值: {nav:.4f}<br>" if nav else ""
    abs_change = abs(daily_change)

    html_content = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 500px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #DC2626, #991B1B); color: white; padding: 20px; border-radius: 12px; text-align: center;">
            <div style="font-size: 40px; margin-bottom: 10px;">⚠️</div>
            <h2 style="margin: 0; font-size: 18px;">基金跌幅预警</h2>
        </div>
        <div style="background: white; padding: 20px; border-radius: 12px; margin-top: -8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="font-size: 16px; font-weight: 600; margin-bottom: 12px;">{fund_name}</p>
            <p style="color: #6B7280; font-size: 14px;">{fund_code}</p>
            {nav_text}
            <div style="background: #FEF2F2; border-radius: 8px; padding: 12px; margin: 12px 0;">
                <p style="color: #DC2626; font-size: 13px; margin: 0;">
                    当日跌幅: <span style="font-size: 24px; font-weight: 700;">{abs_change:.2f}%</span>
                </p>
            </div>
            <p style="color: #DC2626; font-size: 13px; margin-top: 12px;">
                ⚠️ 已超过 {abs(ALERT_THRESHOLD):.0f}% 预警线，请关注市场变化
            </p>
            <hr style="border: none; border-top: 1px solid #E5E7EB; margin: 16px 0;">
            <p style="color: #9CA3AF; font-size: 11px; text-align: center;">
                基金有风险，投资需谨慎 · 自动预警<br>
                本提醒仅供参考，不构成操作建议
            </p>
        </div>
    </div>
    """

    return send_notification(title, html_content)


def send_error_report(error_msg):
    """
    发送运行异常通知

    参数:
        error_msg: 错误描述
    """
    title = "⚠️ 基金日报 - 运行异常"
    html_content = f"""
    <div style="font-family: sans-serif; padding: 10px;">
        <h3>⚠️ 基金日报生成异常</h3>
        <p style="color: #DC2626;">{error_msg}</p>
        <hr>
        <p style="color: #999; font-size: 12px;">将在下次定时任务时重试</p>
    </div>
    """
    return send_notification(title, html_content)


if __name__ == "__main__":
    """测试推送功能"""
    print("🔧 推送模块自测")
    print(f"Token: {PUSHPLUS_TOKEN[:4]}****{PUSHPLUS_TOKEN[-4:] if PUSHPLUS_TOKEN else ''}")

    if not PUSHPLUS_TOKEN:
        print("⚠️ 未设置PUSHPLUS_TOKEN，请在环境变量中配置")
        print("   export PUSHPLUS_TOKEN=your_token_here")
        exit(1)

    # 测试预警推送
    print("\n📌 测试预警推送...")
    send_alert("摩根标普500指数(QDII)A", "017641", -3.25, 1.5800)

    # 测试报告推送
    print("\n📌 测试日报推送...")
    test_html = """
    <h2>📊 基金日报 测试</h2>
    <p>这是一条测试消息</p>
    """
    send_daily_report(test_html)
