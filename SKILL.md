---
name: uex-trading
description: Star Citizen UEX trading route optimizer. Use when user asks about trading in Star Citizen, wants to find profitable trade routes, knows their location and wants buy/sell recommendations, or wants to find the most profitable commodities to trade. Triggers on: "星际公民交易", "UEX", "Star Citizen trading", "trade route", "most profitable trade", "买卖什么赚钱", "去哪里卖", "我在xxx" (Star Citizen context).
---

# UEX Trading Skill

## Overview

This skill interfaces with the UEX API (https://api.uexcorp.space/v2.1) to provide Star Citizen trading route analysis. It helps users find:
1. Best trade routes from their current location
2. Most profitable commodities overall

## API Base URL

`https://api.uexcorp.space/v2.1`

## Key Endpoints

- `GET /commodities/routes` - All trading routes with profit data
- `GET /commodities/ranking` - Commodity profitability rankings
- `GET /cities` - All cities/locations
- `GET /terminals` - All trading terminals

## Key Fields in Route Data

- `scu_origin`, `scu_destination` - stock at terminals
- `scu_reachable` - actual purchasable amount (limited by market stock)
- `container_sizes_origin`, `container_sizes_destination` - terminal's accepted container sizes
- `investment` - total purchase cost for all `scu_reachable` units
- `profit` - total profit for all `scu_reachable` units
- `distance` - distance in AU (Astronomical Units, ~149,597,870 km)
- `price_origin` - buy price per SCU
- `price_roi` - return on investment percentage

## Key Fields in Ship/Vehicle Data

- `scu` - cargo capacity
- `container_sizes` - supported container sizes (e.g., "1,2,4" means ship can carry 1, 2, 4 SCU containers)

## Container Size Compatibility (IMPORTANT)

A route is usable only if the ship's `container_sizes` has at least ONE overlapping size with the terminal's accepted sizes:
- If terminal accepts `"8,16,24,32"` but ship only has `"1,2,4,8,16"` → **incompatible** (no 24 or 32)
- If terminal accepts `"1,2,4,8,16,24,32"` (all sizes) → **compatible with any cargo ship**

The `scu_reachable` field already accounts for market stock.

## Capital-Based Profit Calculation

Given a starting capital `C`, the optimal purchase quantity is:
```
max_scu_by_capital = C / price_origin
usable_scu = min(ship_scu, scu_reachable, max_scu_by_capital)
investment_needed = usable_scu * price_origin
total_profit = usable_scu * (profit / scu_reachable)
actual_roi = (total_profit / investment_needed) * 100
```

## Distance vs Time

- `distance` is in AU (Astronomical Units)
- 1 AU ≈ 149,597,870 km (Earth-Sun distance)
- Distance does NOT directly equal travel time
- Quantum jump speed varies by ship and route
- Use distance as a rough proxy for route complexity
- Pyro routes require Stanton→Pyro quantum travel (no direct route from some locations)

## Workflow

### Step 0: Determine User's Context

When the user asks for trading routes, collect:
1. **Location** - current terminal/station (or "anywhere" for global search)
2. **Ship** - ship name or SCU capacity (required for cargo compatibility)
3. **Capital** - starting aUEC (required for capital-aware calculations)

If ship is unknown, look up via `GET /vehicles?is_cargo=1&per_page=200` and match by name.

### Finding Routes from a Location

1. Fetch routes from the specified terminal (or all terminals for global search)
2. Filter by container size compatibility with user's ship
3. Calculate profit using capital constraint: `usable_scu = min(ship_scu, scu_reachable, capital/price)`
4. Sort and present both ROI-optimized and Total-Profit-optimized recommendations

### Presenting Results

Always present TWO plans side by side:

**Plan A - ROI最大化** (Best ROI):
- Sorted by `price_roi` descending
- Best for limited capital or quick turns
- Shows: actual ROI %, total profit, recommended for capital < X aUEC

**Plan B - 总利润最大化** (Best Total Profit):
- Sorted by total_profit descending
- Best for large cargo ships with sufficient capital
- Shows: total profit, ROI %,进货量, recommended for capital >= investment_needed

### Finding Most Profitable Trades

1. Search across all terminals for routes compatible with user's ship
2. Apply capital constraint
3. Present top 5 for each optimization strategy (ROI and Total Profit)

## Output Format

For trade recommendations, always show BOTH optimization strategies:

**Plan A - ROI最大 (Best ROI)**:
```
🥇 [商品名称] (ROI路线)
   购买: [起点] - [价格] aUEC/SCU
   出售: [终点] - [价格] aUEC/SCU
   理论ROI: [ROI]%
   实际ROI: [actual_roi]% (受本金限制)
   本金需求: [investment_needed] aUEC
   进货量: [usable_scu] SCU
   总利润: [total_profit] aUEC
   距离: [distance] AU
   库存: [scu_reachable] SCU (可填满你的货仓/本金)
```

**Plan B - 总利润最大 (Best Total Profit)**:
```
💰 [商品名称] (利润路线)
   购买: [起点] - [价格] aUEC/SCU
   出售: [终点] - [价格] aUEC/SCU
   理论ROI: [ROI]%
   本金需求: [investment_needed] aUEC
   进货量: [usable_scu] SCU (满仓)
   总利润: [total_profit] aUEC
   距离: [distance] AU
   库存: [scu_reachable] SCU
```

Include this footer for context:
```
=== 你的船: [船名] ([SCU] SCU) | 本金: [capital] aUEC ===
```

## Notes

- UEX uses aUEC (Argo Unified Economic Credit) as currency
- SCU = Standard Cargo Unit
- Routes with high `price_roi` and adequate stock are best
- Check `scu_reachable` to ensure cargo can be transported
