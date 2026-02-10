"""
AfriPlan Electrical - Cost Optimization Functions
Smart Cost Optimizer and OR Optimization using PuLP
"""


def generate_quotation_options(bq_items: list, elec_req: dict, circuit_info: dict) -> list:
    """
    Generate 4 quotation options with different cost/quality strategies.
    Phase 5: Smart Cost Optimizer
    """
    base_material_cost = sum(item["total"] for item in bq_items if item["category"] != "Labour")
    base_labour_cost = sum(item["total"] for item in bq_items if item["category"] == "Labour")
    base_total = base_material_cost + base_labour_cost

    options = []

    # Option A: Budget - Cheapest suppliers, minimum markup
    budget_material = base_material_cost * 0.90  # 10% cheaper materials
    budget_labour = base_labour_cost * 0.95  # Slightly cheaper labour
    budget_cost = budget_material + budget_labour
    budget_markup = 0.12
    budget_selling = budget_cost * (1 + budget_markup)
    budget_profit = budget_selling - budget_cost
    options.append({
        "name": "A: Budget Friendly",
        "strategy": "Cheapest suppliers, basic quality",
        "material_cost": budget_material,
        "labour_cost": budget_labour,
        "base_cost": budget_cost,
        "markup_percent": budget_markup * 100,
        "selling_price": budget_selling,
        "profit": budget_profit,
        "profit_margin": (budget_profit / budget_selling * 100) if budget_selling > 0 else 0,
        "quality_score": 3,
        "lead_time": 7,
        "recommended": False,
        "color": "#3B82F6",  # Blue
    })

    # Option B: Best Value - Balanced cost/quality (RECOMMENDED)
    value_material = base_material_cost * 1.0  # Standard price
    value_labour = base_labour_cost * 1.0
    value_cost = value_material + value_labour
    value_markup = 0.18
    value_selling = value_cost * (1 + value_markup)
    value_profit = value_selling - value_cost
    options.append({
        "name": "B: Best Value",
        "strategy": "Balanced cost and quality",
        "material_cost": value_material,
        "labour_cost": value_labour,
        "base_cost": value_cost,
        "markup_percent": value_markup * 100,
        "selling_price": value_selling,
        "profit": value_profit,
        "profit_margin": (value_profit / value_selling * 100) if value_selling > 0 else 0,
        "quality_score": 4,
        "lead_time": 3,
        "recommended": True,
        "color": "#22C55E",  # Green
    })

    # Option C: Premium - Top quality brands
    premium_material = base_material_cost * 1.25  # 25% premium materials
    premium_labour = base_labour_cost * 1.15  # Experienced contractors
    premium_cost = premium_material + premium_labour
    premium_markup = 0.22
    premium_selling = premium_cost * (1 + premium_markup)
    premium_profit = premium_selling - premium_cost
    options.append({
        "name": "C: Premium Quality",
        "strategy": "Top-tier brands, master electricians",
        "material_cost": premium_material,
        "labour_cost": premium_labour,
        "base_cost": premium_cost,
        "markup_percent": premium_markup * 100,
        "selling_price": premium_selling,
        "profit": premium_profit,
        "profit_margin": (premium_profit / premium_selling * 100) if premium_selling > 0 else 0,
        "quality_score": 5,
        "lead_time": 5,
        "recommended": False,
        "color": "#A855F7",  # Purple
    })

    # Option D: Competitive - Lowest total to win job
    competitive_material = base_material_cost * 0.92
    competitive_labour = base_labour_cost * 0.90
    competitive_cost = competitive_material + competitive_labour
    competitive_markup = 0.10  # Lower margin
    competitive_selling = competitive_cost * (1 + competitive_markup)
    competitive_profit = competitive_selling - competitive_cost
    options.append({
        "name": "D: Competitive Bid",
        "strategy": "Win the job, volume pricing",
        "material_cost": competitive_material,
        "labour_cost": competitive_labour,
        "base_cost": competitive_cost,
        "markup_percent": competitive_markup * 100,
        "selling_price": competitive_selling,
        "profit": competitive_profit,
        "profit_margin": (competitive_profit / competitive_selling * 100) if competitive_selling > 0 else 0,
        "quality_score": 3.5,
        "lead_time": 5,
        "recommended": False,
        "color": "#F59E0B",  # Amber
    })

    return options


def optimize_quotation_or(bq_items: list, constraints: dict = None) -> dict:
    """
    Operations Research optimization using PuLP Integer Linear Programming.
    Finds mathematically optimal supplier selection.
    """
    try:
        from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus, value, PULP_CBC_CMD
    except ImportError:
        return {"status": "error", "message": "PuLP not installed"}

    constraints = constraints or {}
    min_quality = constraints.get("min_quality", 3)
    max_budget = constraints.get("max_budget", float('inf'))

    # Simulated supplier data for each item category
    suppliers = ["budget", "standard", "premium"]
    categories = list(set(item["category"] for item in bq_items))

    # Price multipliers per supplier
    price_mult = {"budget": 0.90, "standard": 1.0, "premium": 1.25}
    quality_scores = {"budget": 3, "standard": 4, "premium": 5}

    # Create optimization problem
    prob = LpProblem("Quotation_Optimizer", LpMinimize)

    # Decision variables: select supplier j for category i
    x = LpVariable.dicts("select",
                         ((cat, sup) for cat in categories for sup in suppliers),
                         cat='Binary')

    # Calculate base costs per category
    category_costs = {}
    for item in bq_items:
        cat = item["category"]
        if cat not in category_costs:
            category_costs[cat] = 0
        category_costs[cat] += item["total"]

    # Objective: Minimize total cost
    prob += lpSum(
        category_costs.get(cat, 0) * price_mult[sup] * x[cat, sup]
        for cat in categories for sup in suppliers
    ), "Total_Cost"

    # Constraint 1: One supplier per category
    for cat in categories:
        prob += lpSum(x[cat, sup] for sup in suppliers) == 1, f"One_Supplier_{cat.replace(' ', '_').replace('&', 'and')}"

    # Constraint 2: Minimum quality score
    total_items = len(categories)
    prob += lpSum(
        quality_scores[sup] * x[cat, sup]
        for cat in categories for sup in suppliers
    ) >= min_quality * total_items, "Min_Quality"

    # Constraint 3: Budget limit (if specified)
    if max_budget < float('inf'):
        prob += lpSum(
            category_costs.get(cat, 0) * price_mult[sup] * x[cat, sup]
            for cat in categories for sup in suppliers
        ) <= max_budget, "Budget_Limit"

    # Solve
    prob.solve(PULP_CBC_CMD(msg=0))

    # Extract solution
    if LpStatus[prob.status] == "Optimal":
        selection = {}
        for cat in categories:
            for sup in suppliers:
                if value(x[cat, sup]) == 1:
                    selection[cat] = {
                        "supplier": sup,
                        "original_cost": category_costs.get(cat, 0),
                        "optimized_cost": category_costs.get(cat, 0) * price_mult[sup],
                        "quality": quality_scores[sup]
                    }

        total_cost = sum(s["optimized_cost"] for s in selection.values())
        avg_quality = sum(s["quality"] for s in selection.values()) / len(selection) if selection else 0

        return {
            "status": "optimal",
            "selection": selection,
            "total_cost": round(total_cost, 2),
            "average_quality": round(avg_quality, 2),
            "solver_status": LpStatus[prob.status]
        }
    else:
        return {
            "status": "no_solution",
            "message": f"Solver status: {LpStatus[prob.status]}"
        }
