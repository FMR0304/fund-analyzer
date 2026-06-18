# 📊 基金日报自动分析工具

> 一个完全免费的基金自动化分析工具，每天自动采集数据 → AI分析 → 生成日报 → 推送到微信

## ✨ 功能特点

| 功能 | 说明 |
|------|------|
| 🤖 **AI 智能分析** | 接入 DeepSeek V4 Pro，每日生成专业基金评语 |
| 📱 **微信推送** | 通过 PushPlus 每日推送报告到微信 |
| ⚠️ **跌幅预警** | 单日跌幅超 3% 即时推送预警通知 |
| 📈 **PC 网页版** | 部署到 GitHub Pages，手机电脑都能看 |
| 🔄 **全自动运行** | GitHub Actions 定时任务，无需服务器 |
| 💰 **完全免费** | 所有服务均有免费额度，零成本运行 |

## 🏗️ 技术架构

```
天天基金API  ──┐
DeepSeek API  ──┤──→  Python脚本  ──→  HTML报告  ──→  GitHub Pages (PC端)
PushPlus      ──┘                              └──→  微信推送 (手机端)
```

## 📋 支持跟踪的基金

当前配置跟踪以下 **2只基金**：

| 代码 | 名称 | 类型 |
|:---:|:----|:----|
| 022184 | 富国全球科技互联网股票(QDII)C | QDII-全球科技股 |
| 017641 | 摩根标普500指数(QDII)人民币A | QDII-标普500指数 |

> 可以随时在 `src/config.py` 的 `FUNDS` 列表中增减基金

---

## 🚀 快速部署指南（全程约10分钟）

### 准备工作（5分钟）

注册两个免费服务，获取密钥：

#### 1️⃣ PushPlus（微信推送）
1. 访问 [https://www.pushplus.plus/](https://www.pushplus.plus/)
2. 微信扫码登录
3. 进入「个人中心」→ 复制你的 **Token**
   > 格式是一串32位字符，如 `8899798c96084067828db5fcd3849f52`

#### 2️⃣ DeepSeek（AI分析）
1. 访问 [https://platform.deepseek.com/](https://platform.deepseek.com/)
2. 注册账号并登录
3. 进入「API Keys」→ 创建新的 API Key 并复制
   > 格式以 `sk-` 开头，如 `sk-19aa78467b7a4abfb9a17df4214faeeb`

---

### 部署到 GitHub（5分钟）

#### 第1步：创建 GitHub 仓库

1. 打开 [GitHub](https://github.com) 并登录
2. 点击右上角 **+** → **New repository**
3. 仓库名填写 `fund-analyzer`
4. 选择 **Public**（公开）
5. 点击 **Create repository**

#### 第2步：上传代码

**方法一：通过网页上传（推荐新手）**

```bash
# 在项目目录打开终端，运行以下命令
cd fund-analyzer
git init
git add .
git commit -m "🎉 首次提交：基金日报自动分析工具"
git branch -M main
git remote add origin https://github.com/你的用户名/fund-analyzer.git
git push -u origin main
```

> 如果你不会用 Git，也可以直接把 `fund-analyzer` 文件夹里的所有文件拖到 GitHub 网页上上传

#### 第3步：配置密钥（GitHub Secrets）

1. 在 GitHub 仓库页面，点击 **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加以下两个密钥：

| Name | Value | 说明 |
|------|-------|------|
| `PUSHPLUS_TOKEN` | `8899798c96084067828db5fcd3849f52` | 你从PushPlus复制的Token |
| `DEEPSEEK_API_KEY` | `sk-19aa78467b7a4abfb9a17df4214faeeb` | 你从DeepSeek复制的API Key |

#### 第4步：启用 GitHub Pages

1. 仓库页面点击 **Settings** → **Pages**
2. 在 **Source** 选择 **GitHub Actions**
3. 设置完成，以后每份报告都会自动部署到网页

#### 第5步：手动运行测试

1. 点击顶部 **Actions** 标签
2. 在左侧找到 **📊 基金日报**
3. 点击 **Run workflow** → **Run workflow**（绿色按钮）
4. 等待几分钟，运行完成后：
   - ✅ **微信收到** 基金日报推送
   - ✅ **GitHub Pages** 可查看网页版报告

> 以后的工作日每天 **20:30（北京时间）** 自动运行，无需任何操作

---

## 📱 使用效果

### 微信推送效果
每天收盘后，微信自动收到：
- 📊 **基金日报**：完整报告，含净值数据、走势图、AI分析
- ⚠️ **跌幅预警**：单日跌幅超3%立即通知

### PC网页版
通过 GitHub Pages 访问，展示：
- 可视化净值走势图（Chart.js）
- 基金表现卡片
- AI深度分析文字

---

## 🔧 自定义配置

### 添加/修改基金

编辑 `src/config.py` 中的 `FUNDS` 列表：

```python
FUNDS = [
    {"code": "022184", "name": "富国全球科技互联网股票(QDII)C"},
    {"code": "017641", "name": "摩根标普500指数(QDII)人民币A"},
    # 在这里添加更多基金，格式：
    # {"code": "基金代码", "name": "基金名称"},
]
```

### 修改预警阈值

在 `src/config.py` 中修改：

```python
ALERT_THRESHOLD = -3.0  # 改为 -5.0 则跌幅超5%才预警
```

### 修改运行时间

编辑 `.github/workflows/daily_report.yml` 中的 cron 表达式：

```yaml
- cron: '30 12 * * 1-5'  # 12:30 UTC = 20:30 CST
```
- 第一个数字是分钟（0-59）
- 第二个是小时（0-23，UTC时间）
- `1-5` 表示周一至周五

> ⏰ 中国时间 = UTC + 8小时，例如要北京时间 21:00 运行，则 UTC 13:00 → `0 13 * * 1-5`

---

## ❓ 常见问题

### Q: 报告显示"暂无最新净值数据"？
- QDII基金（投资港美股）净值更新比A股晚1-2天
- 这是正常现象，耐心等待即可

### Q: 如何查看运行日志？
- GitHub 仓库 → **Actions** → 点击最新一次运行 → 查看详细日志

### Q: AI分析不准怎么办？
- AI分析仅供参考，不构成投资建议
- 可以修改 `src/analyzer.py` 中的提示词（prompt）来调整分析风格

### Q: 推送没收到？
- 检查 PushPlus Token 是否正确配置
- 检查是否关注了 PushPlus 公众号
- 查看 Actions 运行日志中是否有报错

---

## ⚠️ 免责声明

- 本工具仅供学习研究使用
- 所有数据来自公开免费API
- AI 分析内容仅供参考，**不构成任何投资建议**
- 基金有风险，投资需谨慎

---

## 📝 项目结构

```
fund-analyzer/
├── .github/workflows/
│   └── daily_report.yml    # 自动运行配置
├── src/
│   ├── config.py           # 配置文件（基金列表/密钥/参数）
│   ├── data_fetcher.py     # 数据采集模块
│   ├── analyzer.py         # AI分析模块（DeepSeek）
│   ├── reporter.py         # HTML报告生成模块
│   ├── notifier.py         # 微信推送模块（PushPlus）
│   └── main.py             # 主程序入口
├── output/                 # 生成报告存放目录
├── .env.example            # 环境变量模板
├── requirements.txt        # Python依赖
└── README.md               # 本文件
```

---

*Made with ❤️ · 自动生成，永不缺席*
