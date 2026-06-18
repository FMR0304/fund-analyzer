#!/usr/bin/env python3
"""
基金日报自动生成工具 - 主程序
================================
每天定时运行：采集数据 → AI分析 → 生成报告 → 推送微信

运行方式:
    python src/main.py          # 正常运行
    python src/main.py --no-push  # 仅生成报告，不推送
"""

import sys
import traceback
from datetime import datetime

from config import FUNDS
from data_fetcher import (
    fetch_fund_nav_history,
    extract_latest_from_history,
    fetch_market_indices,
    check_alert,
)
from analyzer import analyze_fund, analyze_market_overview
from reporter import generate_html_report, save_report
from notifier import send_daily_report, send_alert, send_error_report


def main():
    """主流程"""
    start_time = datetime.now()
    print("=" * 56)
    print(f"  🚀 基金日报生成工具 v1.0")
    print(f"  🕐 {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  📊 跟踪基金: {len(FUNDS)} 只")
    print("=" * 56)

    # 判断是否推送
    no_push = "--no-push" in sys.argv

    try:
        # ====== 第1步：获取市场指数 ======
        print("\n📡 [1/5] 获取市场指数行情...")
        market_data = fetch_market_indices()
        print(f"   ✅ 获取到 {len(market_data)} 个指数数据")

        # ====== 第2步：获取基金净值数据 ======
        print("\n📡 [2/5] 获取基金净值数据...")
        funds_data = []
        for fund in FUNDS:
            print(f"\n   📌 {fund['name']} ({fund['code']})")
            history = fetch_fund_nav_history(fund["code"], days=25)
            latest = extract_latest_from_history(history) if history else None

            item = {
                "name": fund["name"],
                "code": fund["code"],
                "history": history,
                "data": latest,
            }
            funds_data.append(item)

            if latest:
                print(f"      净值: {latest['nav']:.4f}")
                print(f"      日涨跌: {latest['daily_change']:+.2f}%")
                print(f"      净值日期: {latest['date']}")

                # 检查跌幅预警
                if check_alert(fund["name"], fund["code"], latest["daily_change"]):
                    print(f"      ⚠️ 触发跌幅预警 ({latest['daily_change']:.2f}%)")
                    if not no_push:
                        send_alert(
                            fund["name"],
                            fund["code"],
                            latest["daily_change"],
                            latest["nav"],
                        )
            else:
                print(f"      ⚠️ 暂无最新净值数据（QDII基金可能延迟更新）")

        # 检查是否有任何有效数据
        has_data = any(f.get("data") for f in funds_data)
        if not has_data:
            error_msg = "所有基金均无有效净值数据，可能API暂时不可用"
            print(f"\n   ❌ {error_msg}")
            if not no_push:
                send_error_report(error_msg)
            sys.exit(1)

        # ====== 第3步：AI 深度分析 ======
        print("\n🤖 [3/5] AI 深度分析中...")

        # 大盘分析
        print("   🧠 分析大盘风向...")
        try:
            market_overview = analyze_market_overview(funds_data, market_data)
            print(f"   ✅ 大盘分析完成")
        except Exception as e:
            market_overview = f"大盘分析暂不可用: {str(e)}"
            print(f"   ⚠️ 大盘分析异常: {e}")

        # 单基金分析
        fund_analyses = []
        for fund in funds_data:
            if fund["data"]:
                print(f"   🧠 分析 {fund['name']}...")
                try:
                    analysis = analyze_fund(
                        fund["name"], fund["code"], fund["data"], market_data
                    )
                    fund_analyses.append(analysis)
                    print(f"   ✅ 完成")
                except Exception as e:
                    fund_analyses.append(f"{fund['name']} 分析暂不可用")
                    print(f"   ⚠️ 分析异常: {e}")
            else:
                fund_analyses.append(f"{fund['name']}: 暂无最新数据，无法分析")

        # ====== 第4步：生成HTML报告 ======
        print("\n📄 [4/5] 生成可视化报告...")
        html = generate_html_report(funds_data, market_data, fund_analyses, market_overview)
        report_path = save_report(html)
        print(f"   ✅ 报告已生成: {report_path}")

        # ====== 第5步：推送到微信 ======
        print("\n📱 [5/5] 推送到微信...")
        if no_push:
            print("   ⏭️ --no-push 参数，跳过推送")
        else:
            title = f"📊 基金日报 {start_time.strftime('%m-%d')}"
            success = send_daily_report(html)
            if success:
                print("   ✅ 日报已推送到微信！")
            else:
                print("   ⚠️ 推送失败，请检查 PushPlus Token 配置")

        # 完成
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{'=' * 56}")
        print(f"  ✅ 基金日报生成完成！")
        print(f"  ⏱  耗时: {elapsed:.1f} 秒")
        print(f"  📁 报告: {report_path}")
        if not no_push:
            print(f"  📱 已推送至微信")
        print(f"{'=' * 56}")

        # 输出摘要
        print(f"\n📋 今日摘要:")
        for fund in funds_data:
            d = fund.get("data")
            if d:
                change = d.get("daily_change", 0)
                icon = "📈" if change and change > 0 else "📉" if change and change < 0 else "➡️"
                print(f"   {icon} {fund['name']}: {d.get('nav', 'N/A')} ({change:+.2f}%)")
            else:
                print(f"   ⏳ {fund['name']}: 数据更新中")

    except Exception as e:
        error_msg = f"运行异常: {str(e)}\n{traceback.format_exc()}"
        print(f"\n❌ {error_msg}")
        if not no_push:
            try:
                send_error_report(str(e))
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
