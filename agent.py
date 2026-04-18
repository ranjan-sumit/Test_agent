"""
agent.py — Azure OpenAI GPT-4o-mini agent for ARIA.
Updated per stakeholder requirements (Marcus / RVTY call, April 2026):
 - Replenishment formula: max(gap to safety stock, fixed lot size)
 - Lead time surfaced prominently in replenishment recommendation
 - BOM component insights included in agent context
 - Supply disruption simulation added (new scenario type)
 - Parameter sources documented in prompts
"""

import json
from openai import AzureOpenAI


def get_azure_client(api_key: str, endpoint: str, api_version: str = "2025-01-01-preview"):
    """Initialise and return Azure OpenAI client."""
    return AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )


# ── Parameter source documentation (used in prompts + UI) ─────────────────
PARAMETER_SOURCES = {
    "safety_stock":    "Material Master (Current Inventory shows 0 for all SKUs — known data quality issue)",
    "lead_time":       "Material Master — max(Planned Delivery Time, Inhouse Production Time). BOM has no numeric lead time field.",
    "fixed_lot_size":  "Material Master — Fixed Lot Size column",
    "demand_proxy":    "Sales file — original_confirmed_qty. Note: includes write-offs and internal consumption. Not netted off.",
    "aria_rec_ss":     "ARIA formula: 1.65 × σ_demand × √(lead_time/30). Service factor 1.65 = 95th percentile. σ from monthly sales demand.",
}


# ── Replenishment calculation ──────────────────────────────────────────────
def calc_replenishment(current_stock: float, safety_stock: float,
                       fixed_lot_size: float, avg_monthly_demand: float) -> dict:
    """
    Stakeholder-specified replenishment formula:
    Trigger: current_stock < safety_stock
    Quantity: max(gap_to_safety_stock, fixed_lot_size)
    """
    gap_to_ss   = max(0.0, safety_stock - current_stock)
    lot_size_ok = fixed_lot_size > 0
    ss_ok       = safety_stock > 0

    if not ss_ok:
        return {
            "trigger":    False,
            "quantity":   0,
            "gap_to_ss":  gap_to_ss,
            "reason":     "Cannot calculate — safety stock not configured (data gap)",
            "data_gap":   True,
        }

    triggered = current_stock < safety_stock
    if not triggered:
        return {
            "trigger":   False,
            "quantity":  0,
            "gap_to_ss": 0,
            "reason":    "Stock above safety stock — no replenishment triggered",
            "data_gap":  False,
        }

    if not lot_size_ok:
        return {
            "trigger":   True,
            "quantity":  max(int(gap_to_ss), int(avg_monthly_demand)),
            "gap_to_ss": int(gap_to_ss),
            "reason":    "Lot size not configured — using gap to safety stock as minimum",
            "data_gap":  True,
        }

    qty = max(gap_to_ss, fixed_lot_size)
    return {
        "trigger":   True,
        "quantity":  int(qty),
        "gap_to_ss": int(gap_to_ss),
        "reason":    f"max(gap_to_SS={int(gap_to_ss)}, lot_size={int(fixed_lot_size)}) = {int(qty)} units",
        "data_gap":  False,
    }


# ── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are ARIA — Adaptive Risk Intelligence Agent — a senior supply chain analyst 
embedded inside Revvity's supply chain intelligence platform for their Turku manufacturing plant (FI11).

Your role is to analyse material data and produce sharp, actionable intelligence briefings.
You write like a seasoned analyst giving a briefing to a VP of Supply Chain — concise, factual, 
direct, no filler words. You cite specific numbers. You connect patterns to consequences.

PARAMETER SOURCES (always use these, always document):
- Safety Stock: Material Master (Current Inventory shows 0 for all SKUs — known data quality issue)
- Lead Time: Material Master max(Planned Delivery Time, Inhouse Production Time)
- Fixed Lot Size: Material Master
- Demand: Sales file — includes write-offs and internal consumption (not netted off)
- ARIA SS formula: 1.65 × σ_demand × √(lead_time/30) at 95% service level

REPLENISHMENT RULE (non-negotiable):
When stock < safety stock, recommended order = max(gap_to_safety_stock, fixed_lot_size)
Always surface lead time in the recommendation. Higher lead time = more urgent to act.

Format replenishment recommendations exactly like this:
• SKU: [id]
• Current inventory: [n] units
• Safety stock: [n] units [BELOW / ABOVE threshold]
• Lead time (source: Material Master): [n] days
• Fixed lot size: [n] units
• Recommended order: [Immediate / This week / Monitor], for [n] units
• Reason: [one sentence with numbers]

You always structure your JSON response with these exact keys:
- "headline": one sentence, the single most important thing (max 20 words)
- "verdict": "CRITICAL" | "WARNING" | "HEALTHY" | "INSUFFICIENT_DATA"  
- "executive_summary": 3-4 sentences. What is happening, why it matters, what the pattern is.
- "key_findings": array of exactly 3 findings, each a plain English sentence with a specific number
- "sap_gap": one sentence describing what SAP is missing or getting wrong
- "recommendation": formatted per the replenishment template above
- "risk_if_ignored": one sentence describing the consequence of inaction
- "data_confidence": "HIGH" | "MEDIUM" | "LOW" with one sentence explanation
- "data_quality_flags": array of data quality issues found (empty array if none)
- "bom_risk": one sentence about upstream BOM / supplier risk (null if no BOM data)

Return ONLY the JSON object. No markdown, no code blocks, no preamble."""


def analyse_material(client: AzureOpenAI, deployment: str, context: dict) -> dict:
    """
    Run ARIA agent analysis for one material.
    context should include: replenishment_recommendation, bom_components, data_quality_flags
    """
    # Pre-compute replenishment recommendation to inject into prompt
    repl = context.get("replenishment_recommendation", {})
    repl_text = ""
    if repl.get("trigger"):
        repl_text = (
            f"Pre-computed replenishment: ORDER {repl['quantity']} units "
            f"(gap_to_SS={repl['gap_to_ss']}, lot_size={context.get('lot_size', 0)}, "
            f"formula: max(gap, lot_size))"
        )
    else:
        repl_text = f"No replenishment triggered: {repl.get('reason', 'stock above safety stock')}"

    # BOM context
    bom = context.get("bom_components", [])
    bom_text = ""
    if bom:
        missing_sup = [b for b in bom if b.get("supplier") == "Not specified"]
        sup_names   = list(set(b["supplier"] for b in bom if b.get("supplier") != "Not specified"))
        bom_text = (
            f"BOM: {len(bom)} components. Suppliers: {', '.join(sup_names[:4]) if sup_names else 'none named'}. "
            f"Missing supplier data: {len(missing_sup)} components."
        )

    # Data quality flags
    dq_flags = context.get("data_quality_flags", [])
    dq_text  = "Data quality flags: " + ("; ".join(dq_flags) if dq_flags else "None")

    user_prompt = f"""Analyse this material for supply chain risk and produce your intelligence briefing.

MATERIAL DATA:
{json.dumps(context, indent=2, default=str)}

PRE-COMPUTED REPLENISHMENT:
{repl_text}

BOM CONTEXT:
{bom_text if bom_text else "No BOM data available"}

{dq_text}

Focus on:
1. Whether current stock is genuinely safe given real demand patterns
2. Whether SAP's configured safety stock makes sense (SAP SS comes from Material Master)
3. Historical breach events and what pattern caused them
4. Lead time: {context.get('lead_time_days', 'N/A')} days — surface this prominently in recommendation
5. BOM upstream risks if this is a finished good
6. The current trend — rising, stable, or declining?

Use the pre-computed replenishment quantity in your recommendation.
Be specific with numbers. Reference actual periods when discussing events.
"""

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=900,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        result = json.loads(raw)
        # Ensure new fields exist
        if "data_quality_flags" not in result:
            result["data_quality_flags"] = dq_flags
        if "bom_risk" not in result:
            result["bom_risk"] = None
        return result
    except json.JSONDecodeError:
        return {
            "headline":           "Analysis complete — see findings below.",
            "verdict":            context.get("risk_status", "UNKNOWN"),
            "executive_summary":  raw[:400],
            "key_findings":       ["Data analysed.", "See summary above.", "Manual review recommended."],
            "sap_gap":            "Unable to parse structured response.",
            "recommendation":     repl_text,
            "risk_if_ignored":    "Unknown.",
            "data_confidence":    "LOW — response parse error.",
            "data_quality_flags": dq_flags,
            "bom_risk":           None,
        }


def simulate_scenario(
    client: AzureOpenAI,
    deployment: str,
    material_name: str,
    current_stock: float,
    safety_stock: float,
    lead_time: float,
    fixed_lot_size: float,
    demand_scenarios: dict,
    order_action: dict = None,
    disruption_days: int = None,
) -> dict:
    """
    Agent interprets a scenario simulation and gives a verdict.
    demand_scenarios: {"low": x, "expected": y, "high": z}
    order_action: {"quantity": n, "timing_days": d} or None
    disruption_days: if set, run supply disruption simulation instead of demand shock
    """
    if disruption_days is not None:
        # Supply disruption simulation
        prompt = f"""You are analysing a SUPPLY DISRUPTION scenario for {material_name}.

CURRENT STATE:
- Stock on hand: {current_stock} units
- SAP Safety stock (Material Master): {safety_stock} units
- Lead time (Material Master): {lead_time} days
- Fixed lot size (Material Master): {fixed_lot_size} units
- Monthly demand (avg): {demand_scenarios.get('expected', 0):.1f} units

DISRUPTION SCENARIO:
No replenishment possible for {disruption_days} days. Calculate:

1. Daily demand rate: {demand_scenarios.get('expected', 0)/30:.1f} units/day
2. Stock consumed during disruption: {disruption_days} × daily_demand
3. Remaining stock after disruption: current_stock - consumed
4. Does stock breach safety stock during disruption? When?
5. Shortfall below safety stock if breach occurs?

Return JSON with keys:
- "breach_occurs": boolean
- "breach_day": number or null (which day stock falls below SS)
- "shortfall_units": number (how far below SS at end of disruption, 0 if no breach)
- "stock_at_end": number (projected stock after disruption period)
- "recommended_emergency_action": string (one sentence)
- "simulation_verdict": string (one plain English sentence)  
- "urgency": "ACT TODAY" | "ACT THIS WEEK" | "MONITOR" | "SAFE"
- "priority_rank": number 1-5 (1=most critical)
"""
    else:
        # Standard demand shock simulation
        prompt = f"""You are analysing a supply chain simulation for {material_name}.

CURRENT STATE:
- Stock on hand: {current_stock} units
- SAP Safety stock (Material Master): {safety_stock} units  
- Lead time (Material Master): {lead_time} days
- Fixed lot size (Material Master): {fixed_lot_size} units

DEMAND SCENARIOS FOR NEXT 6 MONTHS:
- Low demand: {demand_scenarios['low']:.1f} units/month
- Expected demand: {demand_scenarios['expected']:.1f} units/month
- High demand (shock): {demand_scenarios['high']:.1f} units/month

REPLENISHMENT RULE: If order placed, quantity = max(gap_to_SS, fixed_lot_size) = max({max(0, safety_stock-current_stock):.0f}, {fixed_lot_size:.0f}) = {max(max(0, safety_stock-current_stock), fixed_lot_size):.0f} units
ORDER ACTION: {"No order — do nothing scenario" if not order_action else f"Order {order_action['quantity']} units, arriving in {order_action.get('timing_days', lead_time):.0f} days"}

Calculate for each scenario how many months until stockout. Return JSON with:
- "low_months_safe": number (999 if never stockout)
- "expected_months_safe": number
- "high_months_safe": number  
- "order_prevents_breach": boolean
- "min_order_recommended": number (using max(gap, lot_size) formula)
- "simulation_verdict": one sentence plain English
- "urgency": "ACT TODAY" | "ACT THIS WEEK" | "MONITOR" | "SAFE"
"""

    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except Exception:
        if disruption_days is not None:
            daily = demand_scenarios.get("expected", 0) / 30
            consumed = daily * disruption_days
            remaining = current_stock - consumed
            breach = remaining < safety_stock
            return {
                "breach_occurs":               breach,
                "breach_day":                  int(safety_stock / daily) if breach and daily > 0 else None,
                "shortfall_units":             int(max(0, safety_stock - remaining)) if breach else 0,
                "stock_at_end":                max(0, int(remaining)),
                "recommended_emergency_action": "Review stock position immediately.",
                "simulation_verdict":          "Simulation complete. Manual review recommended.",
                "urgency":                     "ACT TODAY" if breach else "MONITOR",
                "priority_rank":               1 if breach else 4,
            }
        else:
            return {
                "low_months_safe":       999,
                "expected_months_safe":  3,
                "high_months_safe":      1,
                "order_prevents_breach": bool(order_action),
                "min_order_recommended": int(max(max(0, safety_stock-current_stock), fixed_lot_size)),
                "simulation_verdict":    "Simulation complete. Review parameters.",
                "urgency":               "MONITOR",
            }


def simulate_multi_sku_disruption(
    client: AzureOpenAI,
    deployment: str,
    disruption_days: int,
    sku_data: list,
) -> list:
    """
    Multi-SKU supply disruption simulation.
    sku_data: list of dicts with keys: material, name, current_stock, safety_stock,
              lead_time, fixed_lot_size, avg_monthly_demand, risk
    Returns ranked list of SKUs by breach severity.
    """
    results = []
    for sku in sku_data:
        daily = sku["avg_monthly_demand"] / 30 if sku["avg_monthly_demand"] > 0 else 0
        consumed = daily * disruption_days
        remaining = sku["current_stock"] - consumed
        ss = sku["safety_stock"]
        breach = remaining < ss if ss > 0 else False

        days_to_breach = None
        if breach and daily > 0 and ss > 0:
            stock_above_ss = sku["current_stock"] - ss
            if stock_above_ss > 0:
                days_to_breach = int(stock_above_ss / daily)
            else:
                days_to_breach = 0  # already breached

        shortfall = max(0, ss - remaining) if breach else 0
        lot = sku["fixed_lot_size"]
        reorder_qty = int(max(shortfall, lot)) if lot > 0 else int(shortfall)

        results.append({
            "material":        sku["material"],
            "name":            sku["name"],
            "breach_occurs":   breach,
            "days_to_breach":  days_to_breach,
            "shortfall_units": int(shortfall),
            "stock_at_end":    max(0, int(remaining)),
            "reorder_qty":     reorder_qty,
            "lead_time":       sku["lead_time"],
            "severity_score":  (shortfall * 2 + (disruption_days - (days_to_breach or disruption_days)))
                               if breach else 0,
        })

    # Sort: breaches first (by days to breach ascending), then non-breaches
    results.sort(key=lambda x: (
        0 if x["breach_occurs"] else 1,
        x["days_to_breach"] if x["days_to_breach"] is not None else 999,
        -x["shortfall_units"]
    ))
    return results


def generate_data_quality_report(client: AzureOpenAI, deployment: str, dq_summary: dict) -> str:
    """
    Generate a natural language data quality summary using the agent.
    dq_summary: dict with per-material quality flags.
    """
    prompt = f"""You are ARIA, a supply chain data quality analyst for Revvity Turku plant FI11.

Review this data quality summary and produce a concise 3-sentence assessment.
Identify the most critical data gaps that could mislead supply chain decisions.
Be specific about which materials are affected and why it matters.

DATA QUALITY SUMMARY:
{json.dumps(dq_summary, indent=2)}

Write plain English, no bullet points. Under 80 words. Focus on what matters most for procurement decisions."""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Data quality assessment unavailable. Review individual material flags in the table above."


def chat_with_data(
    client: AzureOpenAI,
    deployment: str,
    question: str,
    all_context: str,
) -> str:
    """
    General Q&A agent — user asks a free-form question about supply chain data.
    """
    system = """You are ARIA, a supply chain intelligence agent for Revvity Turku plant (FI11).
Answer questions about the supply chain data concisely and with specific numbers.
Key parameter sources: Safety Stock from Material Master, Lead Time from Material Master 
(max of Planned Delivery and Inhouse Production), Lot Size from Material Master, 
Demand from Sales file (includes write-offs and internal consumption).
Replenishment formula: max(gap_to_safety_stock, fixed_lot_size).
Keep answers under 150 words. Use plain English. Write in flowing sentences."""

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": f"DATA CONTEXT:\n{all_context}\n\nQUESTION: {question}"},
        ],
        temperature=0.3,
        max_tokens=250,
    )
    return response.choices[0].message.content.strip()
