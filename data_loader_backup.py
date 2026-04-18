"""
data_loader.py — Central data loading and preparation for ARIA.
All datasets are loaded once, cleaned, and cached via st.cache_data.
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DATA_FILES = {
    "sales":    "/mnt/user-data/uploads/Sales_HistoricalData_Structured.xlsx",
    "inv_lt":   "/mnt/user-data/uploads/Inventory_Extract_and_Lead_Time.xlsx",
    "bom":      "/mnt/user-data/uploads/Fi11_BOM_MResult_v2.xlsx",
    "mat_master": "/mnt/user-data/uploads/Material_master_data_with_planning_parameters__Turku___Boston_.xlsx",
    "curr_inv": "/mnt/user-data/uploads/Current_Inventory___planning_parameters__Turku_and_Boston_.xlsx",
}

MATERIAL_LABELS = {
    "1244-104":  "DELFIA Enhancement Solution",
    "1244-106":  "DELFIA Assay Buffer",
    "13804314":  "Europium Solution 200ml",
    "13807866":  "Anti-AFP AF5/A2 Antibody",
    "13808190":  "Microplate Deep Well (LSD)",
    "3014-0010": "DELFIA Wash Concentrate",
    "3515-0010": "SARS-CoV-2 Plus Kit",
}

RISK_COLORS = {
    "CRITICAL":          "#EF4444",
    "WARNING":           "#F59E0B",
    "HEALTHY":           "#10B981",
    "INSUFFICIENT_DATA": "#6B7280",
}

def load_all():
    """Load and clean all datasets. Returns a dict of DataFrames."""
    # ── Sales ──────────────────────────────────────────────────
    df_sales = pd.read_excel(DATA_FILES["sales"], sheet_name="Export")
    df_sales = df_sales.dropna(subset=["material"])
    df_sales = df_sales[~df_sales["material"].astype(str).str.contains("Applied", na=False)]
    df_sales["ym"] = df_sales["calendar_year_period"].apply(
        lambda x: str(int(x))[:6] if pd.notna(x) else None
    )
    df_sales["calendar_date"] = pd.to_datetime(df_sales["calendar_date"], errors="coerce")

    # ── Inventory + Lead Time ───────────────────────────────────
    df_lt = pd.read_excel(DATA_FILES["inv_lt"])
    df_lt = df_lt.dropna(subset=["Material"])
    df_lt = df_lt[df_lt["Fiscal Period"].astype(str).str.match(r"^\d{6}$")]
    df_lt = df_lt.sort_values("Fiscal Period")

    # ── BOM ────────────────────────────────────────────────────
    df_bom = pd.read_excel(DATA_FILES["bom"])

    # ── Material Master ─────────────────────────────────────────
    df_mm = pd.read_excel(DATA_FILES["mat_master"])
    df_mm = df_mm.dropna(subset=["Material"])

    # ── Current Inventory ───────────────────────────────────────
    df_inv = pd.read_excel(DATA_FILES["curr_inv"])
    df_inv = df_inv.dropna(subset=["Material"])
    df_inv = df_inv[~df_inv["Material"].astype(str).str.contains("Applied", na=False)]

    return {
        "sales": df_sales,
        "inv_lt": df_lt,
        "bom": df_bom,
        "mat_master": df_mm,
        "curr_inv": df_inv,
    }


def build_material_summary(data: dict) -> pd.DataFrame:
    """Build master summary table for Command Center."""
    df_lt   = data["inv_lt"]
    df_mm   = data["mat_master"]
    df_sales = data["sales"]

    monthly_demand = (
        df_sales.groupby(["material", "ym"])["original_confirmed_qty"]
        .sum()
        .reset_index()
    )
    monthly_demand.columns = ["material", "period", "demand"]

    rows = []
    for mat in df_lt["Material"].unique():
        lt_sub  = df_lt[df_lt.Material == mat].sort_values("Fiscal Period")
        mm_row  = df_mm[df_mm.Material == mat]
        dem_sub = monthly_demand[monthly_demand.material == mat]

        current_stock  = float(lt_sub["Gross Stock"].iloc[-1]) if len(lt_sub) > 0 else 0
        latest_period  = lt_sub["Fiscal Period"].iloc[-1] if len(lt_sub) > 0 else "N/A"
        mat_name       = MATERIAL_LABELS.get(mat, lt_sub["Material Name"].iloc[0] if len(lt_sub) > 0 else mat)
        ss             = float(mm_row["Safety Stock"].values[0]) if len(mm_row) > 0 else 0
        lead_time      = float(mm_row["Lead Time"].values[0]) if len(mm_row) > 0 else 0
        inhouse_time   = float(mm_row["Inhouse production time"].values[0]) if len(mm_row) > 0 else 0
        temp_cond      = mm_row["Temp. Conditions"].values[0] if len(mm_row) > 0 else ""
        storage_cond   = mm_row["Storage Conditions"].values[0] if len(mm_row) > 0 else ""
        abcde          = mm_row["ABCDE Category"].values[0] if len(mm_row) > 0 else ""
        lot_size       = float(mm_row["Fixed Lot Size"].values[0]) if len(mm_row) > 0 else 0

        nonzero_dem    = dem_sub[dem_sub.demand > 0]
        avg_demand     = float(nonzero_dem.demand.mean()) if len(nonzero_dem) > 0 else 0
        std_demand     = float(nonzero_dem.demand.std()) if len(nonzero_dem) > 1 else 0
        total_periods  = len(lt_sub)
        zero_periods   = int((lt_sub["Gross Stock"] == 0).sum())

        # Days of cover
        daily_demand   = avg_demand / 30.0 if avg_demand > 0 else 0
        days_cover     = current_stock / daily_demand if daily_demand > 0 else 999

        # Recommended safety stock (service factor 1.65 = 95%)
        effective_lt   = max(lead_time, inhouse_time, 1)
        rec_ss         = round(1.65 * std_demand * np.sqrt(effective_lt / 30), 0) if std_demand > 0 else ss

        # Breach count (historical)
        breach_count   = int((lt_sub["Gross Stock"] < max(ss, 1)).sum()) if ss > 0 else 0

        # Trend (last 4 periods)
        if len(lt_sub) >= 4:
            recent = lt_sub["Gross Stock"].tail(4).values
            trend_delta = float(recent[-1] - recent[0])
            trend_label = "Declining" if trend_delta < -20 else ("Rising" if trend_delta > 20 else "Stable")
        else:
            trend_delta = 0
            trend_label = "Stable"

        # Risk classification
        if zero_periods > 15 or len(nonzero_dem) < 3:
            risk = "INSUFFICIENT_DATA"
        elif mat == "3515-0010":
            risk = "INSUFFICIENT_DATA"
        elif current_stock < ss or days_cover < 10:
            risk = "CRITICAL"
        elif current_stock < ss * 1.5 or days_cover < 30:
            risk = "WARNING"
        else:
            risk = "HEALTHY"

        rows.append({
            "material":              mat,
            "name":                  mat_name,
            "current_stock":         current_stock,
            "safety_stock":          ss,
            "rec_safety_stock":      rec_ss,
            "lead_time":             effective_lt,
            "avg_monthly_demand":    round(avg_demand, 1),
            "std_demand":            round(std_demand, 1),
            "days_cover":            round(days_cover, 1),
            "risk":                  risk,
            "trend":                 trend_label,
            "trend_delta":           trend_delta,
            "zero_periods":          zero_periods,
            "total_periods":         total_periods,
            "breach_count":          breach_count,
            "nonzero_demand_months": len(nonzero_dem),
            "temp_cond":             str(temp_cond),
            "storage_cond":          str(storage_cond),
            "abcde":                 str(abcde),
            "lot_size":              lot_size,
            "latest_period":         latest_period,
        })

    return pd.DataFrame(rows)


def get_stock_history(data: dict, material: str) -> pd.DataFrame:
    """Return monthly stock history for one material."""
    df = data["inv_lt"][data["inv_lt"].Material == material].copy()
    df = df.sort_values("Fiscal Period")
    df["period_dt"] = pd.to_datetime(df["Fiscal Period"], format="%Y%m")
    return df[["Fiscal Period", "period_dt", "Gross Stock", "Safety Stock",
               "Plan DelivTime", "Inhouse Production"]].reset_index(drop=True)


def get_demand_history(data: dict, material: str) -> pd.DataFrame:
    """Return monthly demand history for one material."""
    df = data["sales"].copy()
    df = df[df.material == material]
    monthly = df.groupby("ym")["original_confirmed_qty"].sum().reset_index()
    monthly.columns = ["period", "demand"]
    monthly = monthly[monthly.period.notna()].sort_values("period")
    monthly["period_dt"] = pd.to_datetime(monthly["period"], format="%Y%m")
    return monthly.reset_index(drop=True)


def get_bom_components(data: dict, material: str) -> pd.DataFrame:
    """Return BOM components for a finished good."""
    return data["bom"][data["bom"]["Origin Material"] == material].copy()


def get_material_context(data: dict, material: str, summary_df: pd.DataFrame) -> dict:
    """
    Package all relevant data for one material into a structured context dict.
    Used by the Azure OpenAI agent call.
    """
    stock_hist  = get_stock_history(data, material)
    demand_hist = get_demand_history(data, material)
    bom         = get_bom_components(data, material)
    mat_row     = summary_df[summary_df.material == material]

    if len(mat_row) == 0:
        return {}

    row = mat_row.iloc[0]

    # Breach events
    mm_row = data["mat_master"][data["mat_master"].Material == material]
    ss = row["safety_stock"]
    breach_periods = stock_hist[stock_hist["Gross Stock"] < max(ss, 1)]["Fiscal Period"].tolist() if ss > 0 else []

    # BOM summary
    bom_summary = []
    for _, b in bom.iterrows():
        bom_summary.append({
            "component": b["Material"],
            "description": b["Material Description"],
            "level": b["Level"],
            "qty": b["Comp. Qty (CUn)"],
            "unit": b["Component unit"],
            "supplier": b["Supplier Name(Vendor)"] if pd.notna(b["Supplier Name(Vendor)"]) else "Not specified",
            "std_price": b["Standard Price"] if pd.notna(b["Standard Price"]) else "N/A",
        })

    # Demand stats
    nonzero = demand_hist[demand_hist.demand > 0]
    demand_stats = {
        "avg_monthly": round(float(nonzero.demand.mean()), 1) if len(nonzero) > 0 else 0,
        "max_monthly": round(float(nonzero.demand.max()), 1) if len(nonzero) > 0 else 0,
        "min_monthly": round(float(nonzero.demand.min()), 1) if len(nonzero) > 0 else 0,
        "std_monthly": round(float(nonzero.demand.std()), 1) if len(nonzero) > 1 else 0,
        "nonzero_months": len(nonzero),
        "total_months": len(demand_hist),
        "recent_trend": demand_hist["demand"].tail(6).tolist(),
    }

    # Spike events (> 2x average)
    avg = demand_stats["avg_monthly"]
    spikes = demand_hist[demand_hist.demand > avg * 2][["period", "demand"]].to_dict("records") if avg > 0 else []

    # Stock trend last 6 months
    stock_recent = stock_hist.tail(6)[["Fiscal Period", "Gross Stock"]].to_dict("records")

    return {
        "material_id":       material,
        "material_name":     row["name"],
        "current_stock":     row["current_stock"],
        "safety_stock_sap":  row["safety_stock"],
        "rec_safety_stock":  row["rec_safety_stock"],
        "lead_time_days":    row["lead_time"],
        "lot_size":          row["lot_size"],
        "risk_status":       row["risk"],
        "trend":             row["trend"],
        "days_cover":        row["days_cover"],
        "temp_conditions":   row["temp_cond"],
        "abcde_category":    row["abcde"],
        "breach_periods":    breach_periods,
        "demand_stats":      demand_stats,
        "spike_events":      spikes,
        "stock_recent_6m":   stock_recent,
        "bom_components":    bom_summary,
        "total_bom_components": len(bom_summary),
    }
