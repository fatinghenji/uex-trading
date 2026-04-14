# 🚀 UEX Trading Skill

> 星际公民 UEX 跑商路线优化工具 | Star Citizen trading route optimizer

[![GitHub stars](https://img.shields.io/github/stars/fatinghenji/uex-trading?style=flat-square)](https://github.com/fatinghenji/uex-trading/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)

一个基于 UEX API 的星际公民贸易路线优化工具。根据你的船只货仓容量和本金，自动计算最优的买卖路线，同时呈现 **ROI最大化** 和 **总利润最大化** 两种策略，帮你找到最适合当前资产的跑商方案。

---

## ✨ 功能特点

- 📊 **智能路线推荐** — 根据船只 SCU 容量筛选兼容路线
- 💰 **ROI 优化** — 适合小额本金快速周转
- 📈 **总利润优化** — 适合大船满仓跑长线
- ⚙️ **本金感知计算** — 输入本金，自动计算实际进货量和利润
- 🚢 **船只兼容判断** — 根据集装箱尺寸过滤不可用路线
- 🔍 **全球搜索** — 从任意空间站出发找最优路线

---

## 🛠 安装

### 依赖

```bash
pip install requests
```

### 配置 API Key

本工具使用 UEX API，需要设置环境变量：

```bash
# 获取你的 UEX API Key: https://api.uexcorp.space/
export UEX_API_KEY="你的API密钥"

# 运行前设置
export UEX_API_KEY="你的API密钥"
python scripts/uex_routes.py top
```

### 克隆仓库

```bash
git clone https://github.com/fatinghenji/uex-trading.git
cd uex-trading
```

---

## 📖 使用方法

### 查看全局最优路线

```bash
# 默认 10 条最优路线（无本金限制，按货仓容量计算）
python scripts/uex_routes.py top

# 查看 10 条，设置本金 100 万 aUEC
python scripts/uex_routes.py top 10 1000000

# 查看 20 条
python scripts/uex_routes.py top 20
```

### 从指定空间站查询路线

```bash
# 从 Everus 空间站出发，用 Hull B，本金 500 万
python scripts/uex_routes.py from "everus" "hull b" 5000000

# 从 ArcCorp 出发，用 Caterpillar，本金不限
python scripts/uex_routes.py from "arcCorp" "catar" 20000000
```

### 查询可用的贸易空间站

```bash
python scripts/uex_routes.py terminals
```

### 搜索货船

```bash
# 列出所有货船
python scripts/uex_routes.py ships

# 搜索包含 "hull" 的货船
python scripts/uex_routes.py ships hull
```

---

## 📊 输出示例

```
=== Hull B (512 SCU) 全球最佳贸易路线 ===
本金: 5,000,000 aUEC

--- Plan A: ROI最大化 ---
[1] 铝锭 (Rush路线)
    Stanton - Grim HEX → Stanton - Area18
    ROI: 892.1% | 总利润: 1,234,560 aUEC | 进货: 128 SCU | 距离: 0.8 AU
...

--- Plan B: 总利润最大化 ---
[1] 钛合金 (利润路线)
    Stanton - Port Olisar → Stanton - Orison
    总利润: 5,678,900 aUEC | ROI: 234.5% | 进货: 512 SCU | 距离: 1.2 AU
...
```

---

## 📁 项目结构

```
uex-trading/
├── SKILL.md                    # Hermes Agent Skill 定义
├── scripts/
│   └── uex_routes.py          # 命令行工具
└── README.md
```

---

## 🔑 API 说明

本工具使用 [UEX API](https://api.uexcorp.space/v2.1)，数据归 UEX 所有。

| 端点 | 说明 |
|------|------|
| `/commodities_routes/id_terminal_origin/{id}/` | 获取指定终端的贸易路线 |
| `/vehicles` | 获取船只数据（含 SCU 和集装箱尺寸）|
| `/terminals` | 获取所有贸易终端 |

---

## ⚠️ 重要概念

### 集装箱尺寸兼容性
船只的 `container_sizes` 必须与终端的 `container_sizes_origin/destination` **至少有一个重叠尺寸**，路线才可用。

### ROI vs 总利润
- **ROI 最大化**：适合小本金、想快速周转的玩家
- **总利润最大化**：适合大船（ Hull C/E 、Caterpillar 等）、本金充足的玩家

---

## 🤝 贡献

欢迎提交 Issue 和 PR！如果你有更好的路线算法或新功能的想法，请大胆提出来。

---

## 📜 License

MIT License — 详情见 [LICENSE](LICENSE) 文件。

---

*本工具仅供学习交流使用，数据来源于 UEX API，星际公民版权归 Cloud Imperium Games 所有。*
