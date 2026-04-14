#!/usr/bin/env python3
"""
UEX Trading Route Fetcher
Fetches trading routes from UEX API for Star Citizen
Supports ship cargo capacity, container size filtering, and capital-based calculations
"""

import requests
import json
import sys
import io
import os
from typing import Optional, List, Dict, Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://api.uexcorp.space/v2.1"
API_KEY = os.environ.get("UEX_API_KEY", "")
if not API_KEY:
    raise RuntimeError("请设置环境变量 UEX_API_KEY 才能使用本工具")
HEADERS = {"secret_key": API_KEY}


def get_terminals():
    """Fetch all trading terminals"""
    url = f"{BASE_URL}/terminals"
    params = {"is_available": 1, "has_trade_terminal": 1}
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


def get_cities():
    """Fetch all cities/locations"""
    url = f"{BASE_URL}/cities"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


def get_ships(is_cargo: int = 1, per_page: int = 200) -> List[Dict]:
    """Fetch ships/vehicles. Filter by is_cargo=1 for cargo ships."""
    url = f"{BASE_URL}/vehicles"
    params = {"is_cargo": is_cargo, "per_page": per_page}
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


def get_routes_from_terminal(
    terminal_id: int, limit: int = 50, sort_by: str = "price_roi"
):
    """Fetch trading routes from a specific terminal"""
    url = f"{BASE_URL}/commodities_routes/id_terminal_origin/{terminal_id}/"
    params = {"order_by": sort_by, "order_dir": "DESC", "per_page": limit}
    response = requests.get(url, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


def get_top_routes(limit: int = 50, sort_by: str = "price_roi"):
    """Fetch top routes from all terminals"""
    terminals = get_terminals()
    all_routes = []

    for terminal in terminals[:10]:
        try:
            routes = get_routes_from_terminal(
                terminal["id"], limit=limit, sort_by=sort_by
            )
            all_routes.extend(routes)
        except:
            continue

    all_routes.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=True)
    return all_routes[:limit]


def get_terminal_by_name(name: str, terminals: list):
    """Find a terminal by name (partial match)"""
    name_lower = name.lower()
    for t in terminals:
        if (
            name_lower in t.get("name", "").lower()
            or name_lower in t.get("nickname", "").lower()
            or name_lower in t.get("displayname", "").lower()
        ):
            return t
    return None


def get_city_by_name(name: str, cities: list):
    """Find a city by name"""
    name_lower = name.lower()
    for c in cities:
        if name_lower in c.get("name", "").lower():
            return c
    return None


def get_ship_by_name(name: str, ships: list):
    """Find a ship by name (partial match)"""
    name_lower = name.lower()
    for s in ships:
        if (
            name_lower in s.get("name", "").lower()
            or name_lower in s.get("name_full", "").lower()
            or name_lower in s.get("slug", "").lower()
        ):
            return s
    return None


def parse_container_sizes(container_str: str) -> set:
    """Parse container sizes string like '1,2,4,8' into a set of ints"""
    if not container_str:
        return set()
    return set(int(x) for x in container_str.split(",") if x.strip())


def check_container_compatibility(ship_containers: str, terminal_containers: str) -> bool:
    """
    Check if ship can handle terminal's container requirements.
    Must have at least one overlapping container size.
    """
    ship_sizes = parse_container_sizes(ship_containers)
    terminal_sizes = parse_container_sizes(terminal_containers)

    if not terminal_sizes:
        return True
    if not ship_sizes:
        return True

    return bool(ship_sizes & terminal_sizes)


def calculate_profit(route: dict, ship_scu: int, capital: float = None) -> dict:
    """
    Calculate profit based on ship's cargo capacity and capital constraint.
    
    Returns dict with:
    - usable_scu: actual SCU that can be transported
    - profit_per_scu: profit per SCU from the route
    - total_profit: total profit for usable_scu
    - investment_needed: capital required
    - actual_roi: ROI percentage considering capital constraint
    - constrained_by: 'none', 'capital', 'ship', or 'stock'
    """
    scu_reachable = route.get("scu_reachable", 0)
    profit_total = route.get("profit", 0)
    price_origin = route.get("price_origin", 0)

    if scu_reachable <= 0 or profit_total <= 0:
        return {
            "usable_scu": 0,
            "profit_per_scu": 0,
            "total_profit": 0,
            "investment_needed": 0,
            "actual_roi": 0,
            "constrained_by": "stock"
        }

    profit_per_scu = profit_total / scu_reachable

    # Apply constraints in order: ship, stock, capital
    if capital is not None and capital > 0:
        max_by_capital = int(capital / price_origin) if price_origin > 0 else ship_scu
        usable_scu = min(ship_scu, scu_reachable, max_by_capital)
    else:
        usable_scu = min(ship_scu, scu_reachable)

    investment_needed = usable_scu * price_origin
    total_profit = usable_scu * profit_per_scu
    actual_roi = (total_profit / investment_needed * 100) if investment_needed > 0 else 0

    # Determine what constrained the route
    if usable_scu == 0:
        constrained_by = "stock"
    elif capital and max_by_capital < min(ship_scu, scu_reachable):
        constrained_by = "capital"
    elif usable_scu < ship_scu and usable_scu < scu_reachable:
        constrained_by = "capital"  # Capital was the binding constraint
    elif scu_reachable < ship_scu:
        constrained_by = "stock"
    else:
        constrained_by = "none"

    return {
        "usable_scu": usable_scu,
        "profit_per_scu": profit_per_scu,
        "total_profit": total_profit,
        "investment_needed": investment_needed,
        "actual_roi": actual_roi,
        "constrained_by": constrained_by
    }


def format_route_roi(route: dict, ship: dict, capital: float) -> str:
    """Format a route for ROI-optimized display"""
    commodity = route.get("commodity_name", "Unknown")
    origin_sys = route.get("origin_star_system_name", "")
    origin_term = route.get("origin_terminal_name", "")
    dest_sys = route.get("destination_star_system_name", "")
    dest_term = route.get("destination_terminal_name", "")
    price_origin = route.get("price_origin", 0)
    price_dest = route.get("price_destination", 0)
    roi = route.get("price_roi", 0)
    scu_reachable = route.get("scu_reachable", 0)
    distance = route.get("distance", 0)

    ship_name = ship.get("name_full", ship.get("name", "Unknown"))
    ship_scu = ship.get("scu", 0)

    calc = calculate_profit(route, ship_scu, capital)

    constraint_note = ""
    if calc["constrained_by"] == "capital":
        constraint_note = " (本金限制)"
    elif calc["constrained_by"] == "stock":
        constraint_note = " (库存不足)"
    elif calc["constrained_by"] == "ship":
        constraint_note = " (货仓限制)"

    return f"""🥇 {commodity} (ROI路线)
   购买: {origin_sys} - {origin_term} ({price_origin:,} aUEC/SCU)
   出售: {dest_sys} - {dest_term} ({price_dest:,} aUEC/SCU)
   理论ROI: {roi:.1f}% | 实际ROI: {calc['actual_roi']:.1f}%{constraint_note}
   本金需求: {calc['investment_needed']:,.0f} aUEC
   进货量: {calc['usable_scu']:,} SCU
   总利润: {calc['total_profit']:,.0f} aUEC
   距离: {distance} AU | 库存: {scu_reachable:,} SCU"""


def format_route_profit(route: dict, ship: dict, capital: float) -> str:
    """Format a route for Total-Profit-optimized display"""
    commodity = route.get("commodity_name", "Unknown")
    origin_sys = route.get("origin_star_system_name", "")
    origin_term = route.get("origin_terminal_name", "")
    dest_sys = route.get("destination_star_system_name", "")
    dest_term = route.get("destination_terminal_name", "")
    price_origin = route.get("price_origin", 0)
    price_dest = route.get("price_destination", 0)
    roi = route.get("price_roi", 0)
    scu_reachable = route.get("scu_reachable", 0)
    distance = route.get("distance", 0)

    ship_name = ship.get("name_full", ship.get("name", "Unknown"))
    ship_scu = ship.get("scu", 0)

    calc = calculate_profit(route, ship_scu, capital)

    fill_note = "满仓" if calc["usable_scu"] >= ship_scu else f"{calc['usable_scu']:,}/{ship_scu}"

    return f"""💰 {commodity} (利润路线)
   购买: {origin_sys} - {origin_term} ({price_origin:,} aUEC/SCU)
   出售: {dest_sys} - {dest_term} ({price_dest:,} aUEC/SCU)
   理论ROI: {roi:.1f}% | 本金需求: {calc['investment_needed']:,.0f} aUEC
   进货量: {fill_note} SCU
   总利润: {calc['total_profit']:,.0f} aUEC
   距离: {distance} AU | 库存: {scu_reachable:,} SCU"""


def search_routes_for_ship(
    ship: dict,
    capital: float = None,
    location: str = None,
    min_scu: int = 0,
    sort_by: str = "total_profit"
) -> List[Dict]:
    """
    Search routes across all terminals for a specific ship.
    Returns filtered and calculated route results.
    """
    terminals = get_terminals()
    ship_containers = ship.get("container_sizes", "")
    ship_scu = ship.get("scu", 0)

    results = []
    processed = 0

    for t in terminals:
        tid = t['id']
        tname = t.get('displayname') or t.get('name', '')

        # If location specified, skip non-matching terminals
        if location and location.lower() not in tname.lower():
            continue

        try:
            url = f"{BASE_URL}/commodities_routes/id_terminal_origin/{tid}/"
            params = {"order_by": "profit", "order_dir": "DESC", "per_page": 100}
            r = requests.get(url, params=params, headers=HEADERS, timeout=30)
            routes = r.json().get("data", [])
        except:
            continue

        for route in routes:
            cs_orig = route.get("container_sizes_origin", "")
            cs_dest = route.get("container_sizes_destination", "")

            if not check_container_compatibility(ship_containers, cs_orig):
                continue
            if not check_container_compatibility(ship_containers, cs_dest):
                continue

            scu_reach = route.get("scu_reachable", 0)
            if scu_reach < min_scu:
                continue

            profit_total = route.get("profit", 0)
            if profit_total <= 0:
                continue

            calc = calculate_profit(route, ship_scu, capital)
            if calc["usable_scu"] == 0:
                continue

            route_result = {
                "route": route,
                "calc": calc,
                "terminal_name": tname
            }
            results.append(route_result)

        processed += 1

    # Sort results
    if sort_by == "roi":
        results.sort(key=lambda x: x["calc"]["actual_roi"], reverse=True)
    else:
        results.sort(key=lambda x: x["calc"]["total_profit"], reverse=True)

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python uex_routes.py <command> [args]")
        print("Commands:")
        print("  top [n] [capital]      - Show top routes (default: 10)")
        print("  from <location> <ship> [capital] - Routes from location for ship")
        print("  ships [query]          - Search cargo ships")
        print("  terminals             - List trading terminals")
        print("")
        print("Examples:")
        print("  python uex_routes.py top 10 500000")
        print("  python uex_routes.py from 'everus' 'hull b' 1000000")
        sys.exit(1)

    command = sys.argv[1].lower()

    try:
        if command == "top":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
            capital = float(sys.argv[3]) if len(sys.argv) > 3 else None

            terminals = get_terminals()
            all_results = []

            for t in terminals[:15]:  # Sample key terminals
                tid = t['id']
                tname = t.get('displayname') or t.get('name', '')
                ship_containers = "1,2,4,6,8,12,16,32"  # Default cargo containers
                ship_scu = 512  # Default

                try:
                    url = f"{BASE_URL}/commodities_routes/id_terminal_origin/{tid}/"
                    params = {"order_by": "profit", "order_dir": "DESC", "per_page": 100}
                    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
                    routes = r.json().get("data", [])
                except:
                    continue

                for route in routes:
                    cs_orig = route.get("container_sizes_origin", "")
                    cs_dest = route.get("container_sizes_destination", "")

                    if not check_container_compatibility(ship_containers, cs_orig):
                        continue
                    if not check_container_compatibility(ship_containers, cs_dest):
                        continue

                    scu_reach = route.get("scu_reachable", 0)
                    if scu_reach < 50:
                        continue

                    calc = calculate_profit(route, ship_scu, capital)
                    if calc["usable_scu"] == 0:
                        continue

                    all_results.append({
                        "route": route,
                        "calc": calc
                    })

            # Sort by total_profit for Plan B
            by_profit = sorted(all_results, key=lambda x: x["calc"]["total_profit"], reverse=True)[:limit]
            # Sort by ROI for Plan A
            by_roi = sorted(all_results, key=lambda x: x["calc"]["actual_roi"], reverse=True)[:limit]

            print(f"\n=== Hull B (512 SCU) 全球最佳贸易路线 ===")
            if capital:
                print(f"本金: {capital:,.0f} aUEC\n")
            else:
                print("(未设置本金，按货仓容量计算)\n")

            print("--- Plan A: ROI最大化 ---")
            for i, r in enumerate(by_roi[:5], 1):
                route = r["route"]
                calc = r["calc"]
                print(f"[{i}] {route['commodity_name']}")
                print(f"    {route['origin_star_system_name']} - {route['origin_terminal_name']} → {route['destination_star_system_name']} - {route['destination_terminal_name']}")
                print(f"    ROI: {calc['actual_roi']:.1f}% | 总利润: {calc['total_profit']:,.0f} aUEC | 进货: {calc['usable_scu']:,} SCU | 距离: {route['distance']} AU")
                print()

            print("--- Plan B: 总利润最大化 ---")
            for i, r in enumerate(by_profit[:5], 1):
                route = r["route"]
                calc = r["calc"]
                print(f"[{i}] {route['commodity_name']}")
                print(f"    {route['origin_star_system_name']} - {route['origin_terminal_name']} → {route['destination_star_system_name']} - {route['destination_terminal_name']}")
                print(f"    总利润: {calc['total_profit']:,.0f} aUEC | ROI: {calc['actual_roi']:.1f}% | 进货: {calc['usable_scu']:,} SCU | 距离: {route['distance']} AU")
                print()

        elif command == "from":
            if len(sys.argv) < 3:
                print("Error: from requires a location argument")
                sys.exit(1)

            location = sys.argv[2]
            ship_query = sys.argv[3] if len(sys.argv) > 3 else "hull b"
            capital = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None

            terminals = get_terminals()
            cities = get_cities()
            ships = get_ships()

            terminal = get_terminal_by_name(location, terminals)
            if not terminal:
                city = get_city_by_name(location, cities)
                if city:
                    print(f"City found: {city['name']} in {city['star_system_name']}")
                    print("Note: Please specify a terminal/station name")
                else:
                    print(f"Terminal not found: {location}")
                sys.exit(1)

            ship = get_ship_by_name(ship_query, ships)
            if not ship:
                print(f"Ship not found: {ship_query}")
                sys.exit(1)

            ship_name = ship.get("name_full", ship.get("name", "Unknown"))
            ship_scu = ship.get("scu", 0)
            ship_containers = ship.get("container_sizes", "")

            routes = get_routes_from_terminal(terminal["id"], limit=100, sort_by="profit")

            results = []
            for route in routes:
                cs_orig = route.get("container_sizes_origin", "")
                cs_dest = route.get("container_sizes_destination", "")

                if not check_container_compatibility(ship_containers, cs_orig):
                    continue
                if not check_container_compatibility(ship_containers, cs_dest):
                    continue

                scu_reach = route.get("scu_reachable", 0)
                if scu_reach < 10:
                    continue

                calc = calculate_profit(route, ship_scu, capital)
                if calc["usable_scu"] == 0:
                    continue

                results.append({"route": route, "calc": calc})

            # Sort for both plans
            by_profit = sorted(results, key=lambda x: x["calc"]["total_profit"], reverse=True)
            by_roi = sorted(results, key=lambda x: x["calc"]["actual_roi"], reverse=True)

            term_name = terminal.get("displayname", terminal.get("name"))
            print(f"\n=== {term_name} 贸易路线 ===")
            print(f"船: {ship_name} ({ship_scu} SCU)")
            if capital:
                print(f"本金: {capital:,.0f} aUEC\n")
            else:
                print("(未设置本金，按货仓容量计算)\n")

            print("--- Plan A: ROI最大化 ---")
            for i, r in enumerate(by_roi[:5], 1):
                route = r["route"]
                calc = r["calc"]
                origin = route["origin_terminal_name"]
                dest = route["destination_terminal_name"]
                print(f"[{i}] {route['commodity_name']}")
                print(f"    购买: {origin} ({route['price_origin']:,} aUEC/SCU)")
                print(f"    出售: {dest} ({route['price_destination']:,} aUEC/SCU)")
                print(f"    ROI: {calc['actual_roi']:.1f}% | 总利润: {calc['total_profit']:,.0f} aUEC | 进货: {calc['usable_scu']:,} SCU")
                print()

            print("--- Plan B: 总利润最大化 ---")
            for i, r in enumerate(by_profit[:5], 1):
                route = r["route"]
                calc = r["calc"]
                origin = route["origin_terminal_name"]
                dest = route["destination_terminal_name"]
                print(f"[{i}] {route['commodity_name']}")
                print(f"    购买: {origin} ({route['price_origin']:,} aUEC/SCU)")
                print(f"    出售: {dest} ({route['price_destination']:,} aUEC/SCU)")
                print(f"    总利润: {calc['total_profit']:,.0f} aUEC | ROI: {calc['actual_roi']:.1f}% | 进货: {calc['usable_scu']:,} SCU")
                print()

        elif command == "terminals":
            terminals = get_terminals()
            print(f"\n=== Available Trading Terminals ({len(terminals)}) ===\n")
            for t in terminals[:30]:
                print(f"  - {t.get('displayname', t.get('name'))} ({t.get('nickname')}) - {t.get('star_system_name')}")

        elif command == "ships":
            query = sys.argv[2].lower() if len(sys.argv) > 2 else None
            ships = get_ships(is_cargo=1)
            if query:
                ships = [s for s in ships if query in s.get("name", "").lower()
                        or query in s.get("name_full", "").lower()
                        or query in s.get("slug", "").lower()]
            print(f"\n=== Cargo Ships ({len(ships)}) ===\n")
            for s in ships[:30]:
                print(f"  {s.get('name_full', s.get('name')):40} SCU:{s.get('scu', 0):6} containers:{s.get('container_sizes', 'N/A')}")

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except requests.RequestException as e:
        print(f"API Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
