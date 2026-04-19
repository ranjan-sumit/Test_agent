"""
ARIA Supply Intelligence · MResult — Complete Rebuild
All feedback applied:
- Sidebar: logo + API key only, no insights
- Metrics: Total / Critical / Insufficient Data / Healthy (no Under Watch)
- Days cover consistent (SIH-based) across all views
- New CEILING replenishment formula
- AgGrid fixed column widths
- Stockout chart shows product names (stacked by material)
- Intelligence Feed: rich event descriptions
- Stock trajectory: merged single chart with month filter
- Demand Patterns: replaced with sparkline insight (not duplicate of home page)
- Material Intelligence: analyse button only on click, not auto
- BOM: E=Inhouse(Revvity), F=External, Fixed Qty X handled
- Agentic intelligence: Monte Carlo, supplier email draft, supplier consolidation
- Risk Radar: LLM chart interpretation
- Scenario Engine: definitions + LLM insight per simulation
- Supply Network: BOM map with visible text, supplier map, risk cards
- Main panel: more space from sidebar
"""

import os, base64, math
import streamlit as st
import networkx as nx
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

from data_loader import (
    load_all, build_material_summary, get_stock_history, get_demand_history,
    get_bom_components, get_material_context, get_supplier_consolidation,
    RISK_COLORS, SUPPLIER_LOCATIONS, PLANT_LOCATION,   # removed MATERIAL_LABELS
)
from agent import (
    get_azure_client, analyse_material, simulate_scenario,
    simulate_multi_sku_disruption, chat_with_data, run_monte_carlo,
    draft_supplier_email, interpret_chart,
)

AZURE_ENDPOINT   = "https://bu24-demo.openai.azure.com/"
AZURE_DEPLOYMENT = "gpt-4o-mini"
AZURE_API_VER    = "2025-01-01-preview"

st.set_page_config(page_title="ARIA · MResult", page_icon="◈",
                   layout="wide", initial_sidebar_state="expanded")

def _img_b64(path):
    try:
        with open(path,"rb") as f: return base64.b64encode(f.read()).decode()
    except: return ""

_logo_b64 = _img_b64(os.path.join(os.path.dirname(__file__), "image.jpeg"))
ORANGE = "#F47B25"

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
:root{
  --bg:#F5F7FB;--sf:#FFFFFF;--s2:#F8FAFE;--s3:#F0F4F9;--s4:#E9EFF5;
  --or:#F47B25;--olt:#FF9F50;--odk:#C45D0A;
  --og:rgba(244,123,37,0.12);--ob:rgba(244,123,37,0.07);--obr:rgba(244,123,37,0.25);
  --bl:#E2E8F0;--t:#1E293B;--t2:#475569;--t3:#94A3B8;
  --gr:#22C55E;--gbg:rgba(34,197,94,0.10);
  --am:#F59E0B;--abg:rgba(245,158,11,0.10);
  --rd:#EF4444;--rbg:rgba(239,68,68,0.08);
  --r:12px;--rl:16px;
  --fn:'Inter',system-ui,sans-serif;
  --tr:0.2s cubic-bezier(0.4,0,0.2,1);
  --sh:0 1px 3px rgba(0,0,0,0.04);--shm:0 6px 14px -4px rgba(0,0,0,0.10);
}
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:var(--fn);color:var(--t);}
.stApp{background:var(--bg);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0!important;}

/* SIDEBAR */
section[data-testid="stSidebar"]{background:var(--sf)!important;border-right:1px solid var(--bl)!important;overflow:hidden!important;min-width:220px!important;max-width:220px!important;}
section[data-testid="stSidebar"]>div{padding:0!important;overflow:hidden!important;}
section[data-testid="stSidebar"]::-webkit-scrollbar{display:none!important;}
section[data-testid="stSidebar"] *{color:var(--t2)!important;}
section[data-testid="stSidebar"] .stTextInput>div>div{background:rgba(244,123,37,0.04)!important;border:1px solid var(--obr)!important;border-radius:9px!important;font-size:12px!important;color:var(--t3)!important;}

/* MAIN panel gap from sidebar */
.main .block-container{margin-left:24px!important;margin-right:16px!important;}

/* SHIMMER */
.accent-bar{height:3px;background:linear-gradient(90deg,var(--odk),var(--or),var(--olt),var(--or));background-size:200%;animation:shimmer 3s linear infinite;width:100%;}
@keyframes shimmer{0%{background-position:200%}100%{background-position:-200%}}
@keyframes pdot{0%{box-shadow:0 0 0 0 rgba(34,197,94,0.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
.ldot{width:7px;height:7px;border-radius:50%;background:var(--gr);animation:pdot 2s infinite;display:inline-block;}

/* TOPBAR */
.topbar{height:52px;background:var(--sf);border-bottom:1px solid var(--bl);display:flex;align-items:center;padding:0 20px;gap:12px;}
.tt{font-size:14px;font-weight:700;color:var(--t);}
.tt span{color:var(--t3);font-weight:400;}
.tbadge{background:var(--ob);border:1px solid var(--obr);color:var(--or);font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;}

/* STAT CARDS */
.sc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:14px 16px;display:flex;align-items:center;gap:12px;box-shadow:var(--sh);transition:all var(--tr);}
.sc:hover{transform:translateY(-1px);box-shadow:var(--shm);}
.si{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.si svg{width:18px;height:18px;}
.sio{background:var(--ob);border:1px solid var(--obr);}
.sir{background:var(--rbg);border:1px solid rgba(239,68,68,0.2);}
.sia{background:var(--abg);border:1px solid rgba(245,158,11,0.2);}
.sig{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);}
.six{background:rgba(100,116,139,0.08);border:1px solid rgba(100,116,139,0.15);}
.sv{font-size:24px;font-weight:900;color:var(--t);letter-spacing:-1px;line-height:1;}
.sl{font-size:10px;color:var(--t2);margin-top:3px;}
.sdt{font-size:10px;padding:2px 7px;border-radius:20px;font-weight:600;margin-left:auto;white-space:nowrap;}
.sdu{background:var(--gbg);color:var(--gr);}
.sdw{background:var(--abg);color:var(--am);}
.sdc{background:var(--rbg);color:var(--rd);}

/* BADGES */
.sb{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;}
.sbc{background:var(--rbg);color:var(--rd);border:1px solid rgba(239,68,68,0.2);}
.sbw{background:var(--abg);color:var(--am);border:1px solid rgba(245,158,11,0.2);}
.sbh{background:var(--gbg);color:var(--gr);border:1px solid rgba(34,197,94,0.2);}
.sbn{background:rgba(100,116,139,0.08);color:var(--t2);border:1px solid var(--bl);}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
.dot-r{background:var(--rd);}.dot-a{background:var(--am);}.dot-g{background:var(--gr);animation:pdot 2s infinite;}.dot-n{background:var(--t3);}

/* FEED */
.fc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);overflow:hidden;box-shadow:var(--sh);}
.fh{padding:10px 14px;border-bottom:1px solid var(--bl);display:flex;align-items:center;justify-content:space-between;}
.fht{font-size:12px;font-weight:700;color:var(--t);}
.flv{background:var(--gbg);border-radius:20px;padding:2px 7px;font-size:9px;color:var(--gr);display:flex;align-items:center;gap:4px;}
.fi{display:flex;gap:9px;padding:9px 14px;border-bottom:1px solid var(--bl);transition:background var(--tr);}
.fi:last-child{border-bottom:none;}.fi:hover{background:var(--s2);}
.fi-dc{display:flex;flex-direction:column;align-items:center;padding-top:4px;}
.fi-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.fi-line{width:1px;flex:1;background:var(--bl);min-height:12px;margin-top:3px;}
.fi-msg{font-size:11px;font-weight:500;color:var(--t);line-height:1.45;}
.fi-msg span{color:var(--or);font-weight:700;}
.fi-sub{font-size:10px;color:var(--t3);margin-top:2px;line-height:1.35;}
.fi-tag{font-size:8px;padding:2px 5px;border-radius:4px;margin-top:2px;display:inline-block;font-weight:700;}
.ftc{background:var(--rbg);color:var(--rd);}.ftw{background:var(--abg);color:var(--am);}
.fto{background:var(--gbg);color:var(--gr);}.fti{background:var(--ob);color:var(--or);}

/* INTEL */
.ic{background:var(--sf);border:1px solid var(--obr);border-radius:var(--rl);padding:18px 20px;margin:12px 0;box-shadow:0 0 0 3px var(--og);position:relative;}
.il{position:absolute;top:-10px;left:14px;background:var(--or);color:#fff;font-size:9px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:2px 10px;border-radius:20px;}
.ih{font-size:15px;font-weight:800;color:var(--t);margin-bottom:8px;line-height:1.4;}
.ib{font-size:12px;color:var(--t2);line-height:1.8;}
.iff{display:flex;gap:8px;align-items:flex-start;margin:6px 0;font-size:11px;color:var(--t2);}
.ifd{width:5px;height:5px;border-radius:50%;background:var(--or);margin-top:5px;flex-shrink:0;}

/* BOX */
.sap-box{background:var(--abg);border:1px solid rgba(245,158,11,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#78350f;}
.sap-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#92400e;margin-bottom:4px;text-transform:uppercase;}
.rec-box{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;}
.rec-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#166534;margin-bottom:4px;text-transform:uppercase;}
.flag-box{background:var(--s2);border:1px dashed rgba(0,0,0,0.10);border-radius:var(--rl);padding:24px;text-align:center;color:var(--t3);font-size:13px;}
.chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:var(--s3);border:1px solid var(--bl);font-size:10px;color:var(--t2);font-weight:500;}
.note-box{background:rgba(244,123,37,0.04);border-left:3px solid var(--or);border-radius:0 8px 8px 0;padding:7px 11px;font-size:10px;color:var(--t2);margin:6px 0;}
.sdv{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--bl);}
.pfooter{text-align:center;margin-top:24px;padding:12px 0 4px;border-top:1px solid var(--bl);font-size:11px;color:var(--t3);}
.pfooter strong{color:var(--or);}
.mc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:16px 18px;box-shadow:var(--sh);}
.mc:hover{border-color:var(--obr);transform:translateY(-1px);box-shadow:var(--shm);}

/* PRIORITY ROW */
.prow{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--r);margin-bottom:6px;border:1px solid var(--bl);background:var(--sf);transition:all var(--tr);}
.prow:hover{box-shadow:var(--sh);border-color:var(--obr);}

/* BUTTONS */
.stButton>button{background:var(--or);color:#fff;border:none;border-radius:var(--r);font-family:var(--fn);font-size:13px;font-weight:700;padding:8px 16px;transition:all var(--tr);box-shadow:0 2px 8px rgba(244,123,37,0.2);}
.stButton>button:hover{background:var(--odk);border:none;transform:translateY(-1px);}

/* INPUTS */
.stSelectbox>div>div,.stTextInput>div>div{background:var(--s2)!important;border:1px solid var(--bl)!important;border-radius:var(--r)!important;font-size:13px!important;color:var(--t)!important;}

/* NAV */
.nav-link{color:var(--t2)!important;background:transparent!important;border-radius:9px!important;font-size:12px!important;font-weight:500!important;}
.nav-link:hover{background:var(--s3)!important;color:var(--t)!important;}
.nav-link-selected{background:var(--ob)!important;color:var(--or)!important;border:1px solid var(--obr)!important;font-weight:600!important;}
.nav-link .icon{color:inherit!important;}

/* AGGRID */
.ag-root-wrapper{border:1px solid var(--bl)!important;border-radius:var(--rl)!important;overflow:hidden;box-shadow:var(--sh);}
.ag-header{background:#F8FAFE!important;border-bottom:1px solid var(--bl)!important;}
.ag-header-cell-label{font-size:10px!important;font-weight:700!important;color:#475569!important;text-transform:uppercase;}
.ag-row-even{background:#FFFFFF!important;}.ag-row-odd{background:#F8FAFE!important;}
.ag-row:hover{background:rgba(244,123,37,0.03)!important;}
.ag-cell{display:flex;align-items:center;border-right:1px solid #F0F4F9!important;}

/* SCROLLBAR */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:2px;}

/* Sidebar logo size */
section[data-testid="stSidebar"] img {
    max-height: 80px !important;
    width: auto !important;
    margin: 10px auto;
}
button[kind="header"] {
    visibility: visible !important;
}
/* Tooltip style */
[data-tooltip] {
    position: relative;
    cursor: help;
    border-bottom: 1px dotted #94A3B8;
}
[data-tooltip]:before {
    content: attr(data-tooltip);
    position: absolute;
    bottom: 100%;
    left: 0;
    background: #1E293B;
    color: white;
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 10px;
    white-space: nowrap;
    display: none;
    z-index: 1000;
}
[data-tooltip]:hover:before {
    display: block;
}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def ct(fig, h=280, margin=None):
    m = margin or dict(l=8,r=8,t=28,b=8)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", height=h, margin=m,
        font=dict(family="Inter",color="#94A3B8",size=11),
        xaxis=dict(gridcolor="#F0F4F9",zerolinecolor="#F0F4F9",tickfont_color="#94A3B8",showline=False),
        yaxis=dict(gridcolor="#F0F4F9",zerolinecolor="#F0F4F9",tickfont_color="#94A3B8",showline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)",font_color="#94A3B8",font_size=10,orientation="h",y=1.1),
        hoverlabel=dict(bgcolor="#FFFFFF",font_color="#1E293B",bordercolor="#E2E8F0",font_size=11),
    )
    return fig

def fmt_p(p): 
    try: return pd.to_datetime(str(p),format="%Y%m").strftime("%b '%y")
    except: return str(p)

def sbadge(risk):
    m={"CRITICAL":("sbc","dot-r","⛔ Critical"),"WARNING":("sbw","dot-a","⚠ Warning"),
       "HEALTHY":("sbh","dot-g","✓ Healthy"),"INSUFFICIENT_DATA":("sbn","dot-n","◌ No Data")}
    sc,dc,lb=m.get(risk,("sbn","dot-n",risk))
    return '<span class="sb '+sc+'"><span class="dot '+dc+'"></span>'+lb+'</span>'

def sec(t): st.markdown('<div class="sdv">'+t+'</div>',unsafe_allow_html=True)
def note(t): st.markdown('<div class="note-box">'+t+'</div>',unsafe_allow_html=True)

def plot_bom_tree(bom_df, root_name, risk_color):
    """Create a networkx tree graph for BOM propagation."""
    G = nx.DiGraph()
    G.add_node(root_name, color=risk_color)
    for _, row in bom_df.iterrows():
        comp = str(row["Material Description"])[:25] if pd.notna(row["Material Description"]) else str(row["Material"])
        sup = row.get("Supplier Display", "—")
        G.add_edge(root_name, comp)
        if sup not in ["Revvity Inhouse", "—"]:
            sup_label = sup[:20]
            G.add_edge(comp, sup_label)
    pos = nx.spring_layout(G, k=2, seed=42, iterations=50)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    node_x, node_y, node_text, node_color = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x); node_y.append(y)
        node_text.append(node)
        node_color.append(G.nodes[node].get("color", "#3B82F6"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#E2E8F0"), hoverinfo="none"))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode="markers+text", text=node_text, textposition="bottom center",
                             marker=dict(size=25, color=node_color, line=dict(width=2, color="white")),
                             textfont=dict(size=10, color="#1E293B"), hoverinfo="text"))
    fig.update_layout(showlegend=False, height=500, xaxis=dict(visible=False), yaxis=dict(visible=False),
                      margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor="white")
    return fig

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in [("data",None),("summary",None),("azure_client",None),
             ("agent_cache",{}),("sim_ran",False),("data_error",""),
             ("dis_ran",False),("cc_insight",None),("last_analysed_mat",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ── Auto-load ──────────────────────────────────────────────────────────────────
if st.session_state.data is None and not st.session_state.data_error:
    try:
        st.session_state.data    = load_all()
        st.session_state.summary = build_material_summary(st.session_state.data)
    except Exception as e:
        st.session_state.data_error = str(e)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — logo + API key only
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    if _logo_b64:
        st.markdown(
            "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
            "display:flex;align-items:center;justify-content:center;'>"
            "<img src='data:image/jpeg;base64,"+_logo_b64+"' "
            "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
            "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
            "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
            unsafe_allow_html=True)

    ai_on = st.session_state.azure_client is not None
    dot = "#22C55E" if ai_on else "#CBD5E1"
    lbl = "AI Agent Online" if ai_on else "AI Agent Offline"
    st.markdown(
        "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
        "display:flex;align-items:center;gap:6px;'>"
        "<div style='width:6px;height:6px;border-radius:50%;background:"+dot+";flex-shrink:0;"
        +("animation:pdot 2s infinite;" if ai_on else "")+"'></div>"
        "<span style='font-size:10px;color:"+dot+";font-weight:600;'>"+lbl+"</span>"
        "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
        "</div>",unsafe_allow_html=True)

    st.markdown(
        "<div style='padding:8px 12px 4px;'>"
        "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
        "</div>",unsafe_allow_html=True)
    azure_key = st.text_input("k","",type="password",placeholder="Azure OpenAI key…",
                               label_visibility="collapsed",key="az_key")
    if azure_key and not st.session_state.azure_client:
        try: st.session_state.azure_client = get_azure_client(azure_key,AZURE_ENDPOINT,AZURE_API_VER)
        except: pass

    st.markdown(
        "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
        "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
        unsafe_allow_html=True)

# ── Guard ──────────────────────────────────────────────────────────────────────
if st.session_state.data_error:
    st.error("Data load failed: "+st.session_state.data_error); st.stop()
if st.session_state.data is None:
    st.info("Loading data…"); st.stop()

data    = st.session_state.data
summary = st.session_state.summary

# ========== FIX: Build MATERIAL_LABELS from summary (no import needed) ==========
MATERIAL_LABELS = {row['material']: row['name'] for _, row in summary.iterrows()}
# =================================================================================

# ── Topbar ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="accent-bar"></div>',unsafe_allow_html=True)
st.markdown(
    "<div class='topbar'>"
    "<div class='tt'>Supply Intelligence <span>/ FI11 Turku · Apr 2026</span></div>"
    "<div class='tbadge'>◈ Live</div>"
    "<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
    "<span class='ldot'></span>"
    "<span style='font-size:10px;color:var(--t3);'>Real-time</span>"
    "<div style='width:28px;height:28px;border-radius:7px;"
    "background:linear-gradient(135deg,var(--odk),var(--or));"
    "display:flex;align-items:center;justify-content:center;"
    "font-size:11px;font-weight:800;color:#fff;'>AI</div>"
    "</div></div>",unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────────────
selected = option_menu(
    menu_title=None,
    options=["Command Center","Material Intelligence","Risk Radar","Scenario Engine","Supply Network"],
    icons=["grid","search","broadcast","lightning","diagram-3"],
    orientation="horizontal",
    styles={
        "container":{"padding":"5px 20px","background-color":"#FFFFFF","border-bottom":"1px solid #E2E8F0"},
        "nav-link":{"font-family":"Inter","font-size":"12px","font-weight":"500","color":"#475569",
                    "padding":"6px 12px","border-radius":"9px","margin":"0 2px","--hover-color":"#F0F4F9"},
        "nav-link-selected":{"background-color":"rgba(244,123,37,0.07)","color":"#F47B25",
                              "border":"1px solid rgba(244,123,37,0.25)","font-weight":"600"},
        "icon":{"font-size":"12px"},
    },
)

st.markdown('<div style="padding:16px 20px;">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════
if selected == "Command Center":

    # ── 4 KPIs: Total / Critical / Insufficient Data / Healthy ────────────────
    total   = len(summary)
    crit_n  = int((summary.risk=="CRITICAL").sum())
    insuf_n = int((summary.risk=="INSUFFICIENT_DATA").sum())
    ok_n    = int((summary.risk=="HEALTHY").sum())

    SVG = {
        "tot": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
        "crit":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
        "ok":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
    }
    def kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
        dh = ('<span class="sdt '+dc+'">'+dlt+'</span>') if dlt else ""
        with col:
            st.markdown("<div class='sc'><div class='si "+si+"'>"+svg+"</div>"
                        "<div style='flex:1;'><div class='sv' style='color:"+vc+";'>"+str(val)+"</div>"
                        "<div class='sl'>"+lbl+"</div></div>"+dh+"</div>",unsafe_allow_html=True)

    k1,k2,k3,k4 = st.columns(4)
    kpi(k1,SVG["tot"], "sio", total,   "#1E293B","Total Materials")
    kpi(k2,SVG["crit"],"sir", crit_n,  "#EF4444","Critical Alerts",
        "⛔ Action required" if crit_n>0 else "✓ None","sdc" if crit_n>0 else "sdu")
    kpi(k3,SVG["insuf"],"six",insuf_n, "#94A3B8","Insufficient Data",
        str(insuf_n)+" SKUs","sdw" if insuf_n>0 else "sdu")
    kpi(k4,SVG["ok"],  "sig", ok_n,    "#22C55E","Healthy","↑ Operating","sdu")

    # ── MAIN ROW ──────────────────────────────────────────────────────────────
    st.markdown("<div style='height:14px;'></div>",unsafe_allow_html=True)
    board_col, feed_col = st.columns([3,2], gap="medium")

    # ── LEFT: Material Health Board (AgGrid fixed widths) ─────────────────────
    with board_col:
        st.markdown(
            "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
            "Material Health Board"
            "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Click to inspect</span>"
            "</div>",unsafe_allow_html=True)

        grid_rows=[]
        for _,row in summary.iterrows():
            sh2=get_stock_history(data,row["material"]); dh2=get_demand_history(data,row["material"])
            nz=dh2[dh2.demand>0]; avg=float(nz.demand.mean()) if len(nz)>0 else 0
            ss=row["safety_stock"]; br=sh2[sh2["Gross Stock"]<max(ss,1)] if ss>0 else pd.DataFrame()
            lb=fmt_p(br["Fiscal Period"].iloc[-1]) if len(br)>0 else "—"
            spark=sh2["Gross Stock"].tail(8).tolist()
            dc=row["days_cover"]
            grid_rows.append({
                "Risk":row["risk"],"Material":row["name"],
                "Stock":int(row["sih"]),"SAP SS":int(ss),"ARIA SS":int(row["rec_safety_stock"]),
                "Days Cover":int(dc) if dc<999 else 0,
                "Demand/mo":round(avg,0),"Trend":row["trend"],
                "Breaches":int(row["breach_count"]),"Last Breach":lb,
                "Order Now":int(row["repl_quantity"]),
                "Spark":(",".join([str(round(v)) for v in spark])),
            })
        df_grid=pd.DataFrame(grid_rows)

        # JsCode renderers
        status_r=JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
        spark_r=JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
        cover_r=JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
        order_r=JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
        row_style=JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

        gb=GridOptionsBuilder.from_dataframe(df_grid)
        # FIXED WIDTHS as requested
        gb.configure_column("Risk",       cellRenderer=status_r, width=110, minWidth=110, maxWidth=110, pinned="left")
        gb.configure_column("Material",   width=170, minWidth=170, maxWidth=170, pinned="left")
        gb.configure_column("Stock",      width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
        gb.configure_column("SAP SS",     width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
        gb.configure_column("ARIA SS",    width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
        gb.configure_column("Days Cover", width=120, minWidth=120, maxWidth=120, cellRenderer=cover_r)
        gb.configure_column("Demand/mo",  width=78,  minWidth=78,  maxWidth=78,  type=["numericColumn"])
        gb.configure_column("Trend",      width=68,  minWidth=68,  maxWidth=68)
        gb.configure_column("Breaches",   width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
        gb.configure_column("Last Breach",width=82,  minWidth=82,  maxWidth=82)
        gb.configure_column("Order Now",  width=82,  minWidth=82,  maxWidth=82,  cellRenderer=order_r)
        gb.configure_column("Spark",      width=90,  minWidth=90,  maxWidth=90,  cellRenderer=spark_r, headerName="8m Trend")
        gb.configure_grid_options(rowHeight=42,headerHeight=34,getRowStyle=row_style,
                                   suppressMovableColumns=True,suppressColumnVirtualisation=True)
        gb.configure_selection("single",use_checkbox=False)
        gb.configure_default_column(resizable=False,sortable=True,filter=False)

        AgGrid(df_grid,gridOptions=gb.build(),height=340,allow_unsafe_jscode=True,
               update_mode=GridUpdateMode.SELECTION_CHANGED,theme="alpine",
               custom_css={
                   ".ag-root-wrapper":{"border":"1px solid #E2E8F0!important","border-radius":"14px!important","overflow":"hidden"},
                   ".ag-header":{"background":"#F8FAFE!important"},
                   ".ag-row-even":{"background":"#FFFFFF!important"},".ag-row-odd":{"background":"#F8FAFE!important"},
                   ".ag-cell":{"border-right":"1px solid #F0F4F9!important"},
               })

    # ── RIGHT: Intelligence Feed (equal height 340px) ─────────────────────────
    with feed_col:
        st.markdown("<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",unsafe_allow_html=True)

        feed_items=[]
        # Critical materials with rich detail
        for _,row in summary[summary.risk=="CRITICAL"].iterrows():
            repl_q = int(row["repl_quantity"])
            feed_items.append({"dot":"#EF4444","type":"crit","time":"Now",
                "msg":"<span>⛔ "+row["name"]+"</span>",
                "sub":str(round(row["sih"]))+" units stock · "+str(round(row["days_cover"]))+"d cover · SS="+str(round(row["safety_stock"]))+
                      (" · ORDER "+str(repl_q)+" units NOW" if repl_q>0 else "")})
        # Warning
        for _,row in summary[summary.risk=="WARNING"].iterrows():
            feed_items.append({"dot":ORANGE,"type":"warn","time":"Live",
                "msg":"<span>⚠ "+row["name"]+"</span>",
                "sub":str(round(row["days_cover"]))+"d cover remaining · Approaching safety stock threshold"})
        # SS gaps with numbers
        ss_gap=summary[(summary.safety_stock<summary.rec_safety_stock)&(summary.risk!="INSUFFICIENT_DATA")]
        for _,row in ss_gap.sort_values("breach_count",ascending=False).head(2).iterrows():
            g=round(row["rec_safety_stock"]-row["safety_stock"])
            if g>0:
                feed_items.append({"dot":"#F59E0B","type":"warn","time":"Audit",
                    "msg":"<span>SAP SS Under-configured</span> — "+row["name"][:20],
                    "sub":"SAP: "+str(round(row["safety_stock"]))+" units · ARIA recommends: "+str(round(row["rec_safety_stock"]))+" · Gap: "+str(g)+" units"})
        # Historical breaches
        top_b=summary[(summary.breach_count>0)&(summary.risk!="INSUFFICIENT_DATA")].sort_values("breach_count",ascending=False)
        if len(top_b)>0:
            r=top_b.iloc[0]
            feed_items.append({"dot":ORANGE,"type":"info","time":"History",
                "msg":"<span>"+r["name"]+"</span> — "+str(r["breach_count"])+" stockout events",
                "sub":"Worst performer over 25 months · "+str(round(r["breach_count"]))+" periods below safety stock"})
        # Lead time urgency
        lt_critical=summary[(summary.days_cover<summary.lead_time)&(summary.risk!="INSUFFICIENT_DATA")]
        for _,row in lt_critical.iterrows():
            feed_items.append({"dot":"#EF4444","type":"crit","time":"Urgent",
                "msg":"<span>Lead Time Exceeds Cover</span> — "+row["name"][:22],
                "sub":"Cover="+str(round(row["days_cover"]))+"d but Lead Time="+str(round(row["lead_time"]))+"d · Order immediately"})
        # System health
        feed_items.append({"dot":"#22C55E","type":"ok","time":"System",
            "msg":"<span>ARIA</span> — Safety stock models updated",
            "sub":"Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master"})

        tag_map={"crit":"ftc","warn":"ftw","ok":"fto","info":"fti"}
        tag_lbl={"crit":"Critical","warn":"Warning","ok":"Healthy","info":"Update"}
        items_html=""
        for i,item in enumerate(feed_items[:9]):
            line="" if i>=8 else "<div class='fi-line'></div>"
            sub_html=("<div class='fi-sub'>"+item.get("sub","")+"</div>") if item.get("sub") else ""
            items_html+=(
                "<div class='fi'><div class='fi-dc'>"
                "<div class='fi-dot' style='background:"+item["dot"]+";'></div>"+line+"</div>"
                "<div style='flex:1;min-width:0;'>"
                "<div class='fi-msg'>"+item["msg"]+"</div>"
                +sub_html+
                "<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
                "<div class='fi-time'>"+item["time"]+"</div>"
                "<span class='fi-tag "+tag_map[item["type"]]+"'>"+tag_lbl[item["type"]]+"</span>"
                "</div></div></div>")
        st.markdown(
            "<div class='fc' style='height:340px;overflow-y:auto;'>"
            "<div class='fh'><div class='fht'>Intelligence Feed</div>"
            "<div class='flv'><div class='dot dot-g'></div>Live</div>"
            "</div>"+items_html+"</div>",unsafe_allow_html=True)

    # ── ANALYTICS ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>",unsafe_allow_html=True)
    sec("Supply Chain Analytics")

    c1,c2=st.columns(2,gap="medium")

    with c1:
        # Stockout events — stacked by material so you can see which product
        st.markdown("<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Historical Stockout Events by Month & Product</div>",unsafe_allow_html=True)
        all_breaches=[]
        for _,row in summary[summary.breach_count>0].iterrows():
            sh3=get_stock_history(data,row["material"]); ss=row["safety_stock"]
            if ss<=0: continue
            b=sh3[sh3["Gross Stock"]<ss]
            for _,br in b.iterrows():
                all_breaches.append({"label":fmt_p(br["Fiscal Period"]),"period":br["Fiscal Period"],"material":row["name"][:16]})
        if all_breaches:
            df_br=pd.DataFrame(all_breaches)
            # Pivot to get stacked bars by material
            pivot=df_br.groupby(["period","label","material"]).size().reset_index(name="count")
            pivot=pivot.sort_values("period")
            # Keep last 14 periods for readability
            recent_periods=pivot["period"].unique()[-14:]
            pivot=pivot[pivot["period"].isin(recent_periods)]
            materials_breached=pivot["material"].unique().tolist()
            colors=["#EF4444","#F59E0B","#8B5CF6","#EC4899","#06B6D4"]
            fig1=go.Figure()
            for i,mat in enumerate(materials_breached):
                md=pivot[pivot.material==mat]
                periods_all=pivot["label"].unique().tolist()
                counts=[md[md.label==p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
                fig1.add_trace(go.Bar(
                    name=mat,x=periods_all,y=counts,
                    marker_color=colors[i%len(colors)],marker_line_width=0,
                    hovertemplate="<b>%{x}</b><br>"+mat+": %{y} breach(es)<extra></extra>"))
            ct(fig1,210); fig1.update_layout(barmode="stack",showlegend=True,
                                              legend=dict(font_size=9,orientation="h",y=1.12),
                                              xaxis_tickangle=-40,yaxis=dict(dtick=1,title="Breaches"))
            st.plotly_chart(fig1,use_container_width=True)
        else:
            st.markdown("<div style='height:210px;display:flex;align-items:center;justify-content:center;color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>No breach events recorded</div>",unsafe_allow_html=True)

    with c2:
        # Days of Cover per SKU (renamed, horizontal bars)
        st.markdown("<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",unsafe_allow_html=True)
        act2=summary[summary.risk.isin(["CRITICAL","WARNING","HEALTHY"])].sort_values("days_cover")
        fig2=go.Figure()
        clrs2=["#EF4444" if r=="CRITICAL" else "#F59E0B" if r=="WARNING" else "#22C55E" for r in act2["risk"]]
        cap=[min(float(v),300) for v in act2["days_cover"]]
        fig2.add_trace(go.Bar(
            y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
            marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
            text=[(str(round(v))+"d") for v in cap],
            textposition="outside", textfont=dict(size=9,color="#475569"),
            hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>"))
        fig2.add_vline(x=30,line_color="#EF4444",line_dash="dot",line_width=1.5,
                       annotation_text="30d min",annotation_font_color="#EF4444",annotation_font_size=9)
        ct(fig2,210); fig2.update_layout(showlegend=False,xaxis_title="Days",margin=dict(l=8,r=48,t=28,b=8))
        st.plotly_chart(fig2,use_container_width=True)

    # ── ARIA LLM Insight for Command Center ───────────────────────────────────
    if st.session_state.azure_client:
        ai2,rb2=st.columns([10,1])
        with rb2:
            if st.button("↺",key="ref_cc",help="Refresh ARIA overview"):
                st.session_state.cc_insight=None
        if st.session_state.cc_insight is None:
            crit_mat=summary[summary.risk=="CRITICAL"]
            ctx_str=(
                f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
                + (f" ({', '.join(crit_mat['name'].tolist())})" if len(crit_mat)>0 else "")
                + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
                + f"Most critical: {summary.sort_values('days_cover').iloc[0]['name']} "
                + f"with {summary.sort_values('days_cover').iloc[0]['days_cover']:.1f}d cover, "
                + f"stock={summary.sort_values('days_cover').iloc[0]['sih']:.0f} vs SS={summary.sort_values('days_cover').iloc[0]['safety_stock']:.0f}."
            )
            try:
                insight=chat_with_data(st.session_state.azure_client,AZURE_DEPLOYMENT,
                    "Give a 2-sentence executive briefing on the current supply chain health. Identify the single biggest risk and one specific action.",
                    ctx_str)
                st.session_state.cc_insight=insight
            except: st.session_state.cc_insight=None
        if st.session_state.cc_insight:
            st.markdown(
                "<div class='ic' style='margin:10px 0;'>"
                "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
                "<div class='ib' style='margin-top:4px;'>"+st.session_state.cc_insight+"</div>"
                "</div>",unsafe_allow_html=True)

    # ── Product drill-down with month filter ───────────────────────────────────
    sec("Product Deep-Dive")
    note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")
    pd_col1, pd_col2=st.columns([2,1])
    with pd_col1:
        prod_opts=[r["name"] for _,r in summary[summary.risk!="INSUFFICIENT_DATA"].iterrows()]
        sel_prod=st.selectbox("Select product",prod_opts,key="cc_prod")
    with pd_col2:
        month_range=st.slider("Show last N months",6,60,24,step=6,key="cc_months")

    sel_mat_id=summary[summary.name==sel_prod]["material"].values[0]
    dh_cc=get_demand_history(data,sel_mat_id)
    sh_cc=get_stock_history(data,sel_mat_id)
    ss_cc=summary[summary.material==sel_mat_id]["safety_stock"].values[0]
    repl_cc=int(summary[summary.material==sel_mat_id]["repl_quantity"].values[0])
    lt_cc=float(summary[summary.material==sel_mat_id]["lead_time"].values[0])
    lot_cc=float(summary[summary.material==sel_mat_id]["lot_size"].values[0])
    sih_cc=float(summary[summary.material==sel_mat_id]["sih"].values[0])

    # Filter to selected months
    sh_cc=sh_cc.tail(month_range)
    dh_cc_fil=dh_cc.tail(month_range)

    if len(sh_cc)>0:
        # Single merged chart: stock + demand on same time axis
        fig_dd=go.Figure()
        avg_d=float(dh_cc_fil[dh_cc_fil.demand>0]["demand"].mean()) if len(dh_cc_fil[dh_cc_fil.demand>0])>0 else 0
        # Area: stock
        fig_dd.add_trace(go.Scatter(
            x=sh_cc["label"],y=sh_cc["Gross Stock"],mode="lines+markers",name="Stock (units)",
            line=dict(color=ORANGE,width=2.5),marker=dict(size=4,color=ORANGE),
            fill="tozeroy",fillcolor="rgba(244,123,37,0.08)",yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
        # Bar: demand (secondary y)
        dem_aligned=dh_cc_fil[dh_cc_fil.label.isin(sh_cc["label"].tolist())]
        if len(dem_aligned)>0:
            fig_dd.add_trace(go.Bar(
                x=dem_aligned["label"],y=dem_aligned["demand"],name="Demand/mo",
                marker_color="rgba(148,163,184,0.3)",marker_line_width=0,yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
        if ss_cc>0:
            fig_dd.add_hline(y=ss_cc,line_color="#EF4444",line_dash="dot",line_width=1.5,
                             annotation_text="SAP SS "+str(round(ss_cc))+"u",
                             annotation_font_color="#EF4444",annotation_font_size=9)
        ct(fig_dd,240)
        fig_dd.update_layout(
            title=dict(text=sel_prod+" — Stock vs Demand (last "+str(month_range)+"mo)",
                       font=dict(size=11,color="#475569"),x=0),
            xaxis=dict(tickangle=-35),
            yaxis=dict(title="Stock (units)",gridcolor="#F0F4F9"),
            yaxis2=dict(title="Demand/mo",overlaying="y",side="right",showgrid=False),
            legend=dict(orientation="h",y=1.1),margin=dict(l=8,r=50,t=44,b=8),
        )
        st.plotly_chart(fig_dd,use_container_width=True)

    if repl_cc>0:
        st.markdown(
            "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
            "<div style='font-size:16px;'>⛔</div>"
            "<div style='flex:1;'>"
            "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
            "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
            "Stock-in-Hand: <strong>"+str(round(sih_cc))+"</strong> · SAP SS: <strong>"+str(round(ss_cc))+"</strong> · "
            "Lead time: <strong>"+str(round(lt_cc))+"d</strong> (Material Master) · "
            "Lot size: <strong>"+str(round(lot_cc))+"</strong>"
            "</div></div>"
            "<div style='text-align:right;'>"
            "<div style='font-size:22px;font-weight:900;color:#EF4444;'>"+str(repl_cc)+" units</div>"
            "<div style='font-size:9px;color:#EF4444;'>CEILING("+str(round(ss_cc-sih_cc))+"/"+str(round(lot_cc))+")×"+str(round(lot_cc))+"</div>"
            "</div></div>",unsafe_allow_html=True)

    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MATERIAL INTELLIGENCE — Agentic
# ══════════════════════════════════════════════════════════════════════════════
elif selected == "Material Intelligence":
    mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
    sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
                            help="Select a finished good to analyse")
    sel_mat = mat_opts[sel_name]
    mat_row = summary[summary.material == sel_mat].iloc[0]
    risk = mat_row["risk"]

    if risk == "INSUFFICIENT_DATA":
        reasons = []
        if mat_row["nonzero_demand_months"] < 3:
            reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
        if mat_row["zero_periods"] > 10:
            reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
        if sel_mat == "3515-0010":
            reasons.append("Marked inactive in sales history")
        r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
            f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
            f"<div class='flag-box' style='max-width:520px;'>"
            f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
            f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
            f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
            f"{r_html}</div>", unsafe_allow_html=True)
        st.stop()

    # HEADER
    h1c, h2c = st.columns([5, 1])
    with h1c:
        dq_flags = mat_row.get("data_quality_flags", [])
        flags_html = ""
        if dq_flags:
            flags_html = "".join(f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>' for f in dq_flags[:2])
        st.markdown(
            f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
            f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
            f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>"
            f"{flags_html}</div>", unsafe_allow_html=True)
    with h2c:
        run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

    analysis = st.session_state.agent_cache.get(sel_mat)
    if run_an:
        if st.session_state.azure_client:
            with st.spinner("ARIA investigating…"):
                ctx = get_material_context(data, sel_mat, summary)
                analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
                st.session_state.agent_cache[sel_mat] = analysis
                st.session_state.last_analysed_mat = sel_mat
        else:
            st.markdown("<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);border-radius:9px;font-size:12px;color:var(--or);'>Enter Azure API key in sidebar to enable ARIA analysis.</div>", unsafe_allow_html=True)

    # Show analysis if available for this material
    if analysis and st.session_state.agent_cache.get(sel_mat):
        key_findings = analysis.get("key_findings", [])
        if not isinstance(key_findings, list):
            key_findings = [str(key_findings)]
        else:
            key_findings = [str(f) for f in key_findings]
        fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

        conf = str(analysis.get("data_confidence", "MEDIUM"))
        conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
        cc = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

        dq = analysis.get("data_quality_flags", [])
        dq_html = ""
        if dq:
            dq_html = "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>" + "".join(
                f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq) + "</div>"

        st.markdown(
            f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
            f"<div class='ih'>{analysis.get('headline', '')}</div>"
            f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
            f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
            f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
            f"{fh}{dq_html}</div>"
            f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
            f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
            f"</div></div>", unsafe_allow_html=True)

        ca, cb = st.columns(2)
        sap_gap = analysis.get("sap_gap", "")
        if not isinstance(sap_gap, str):
            sap_gap = str(sap_gap)
        recom = analysis.get("recommendation", "")
        if not isinstance(recom, str):
            recom = str(recom)

        # Clean up if model returned error strings
        if "Unable to parse" in sap_gap:
            sap_gap = f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units."
        if "No replenishment triggered" in recom and mat_row["repl_triggered"]:
            repl = mat_row
            recom = (f"Order {int(repl['repl_quantity'])} units immediately. "
                     f"Stock-in-Hand ({repl['sih']:.0f}) below SAP SS ({repl['safety_stock']:.0f}). "
                     f"Lead time: {repl['lead_time']:.0f}d. Formula: {repl['repl_formula']}")
        with ca:
            st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
        with cb:
            st.markdown(f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div><pre style='font-size:11px;white-space:pre-wrap;margin:0;color:#14532d;'>{recom}</pre><div style='margin-top:5px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>", unsafe_allow_html=True)

        # Supplier action
        sup_action = analysis.get("supplier_action")
        if sup_action:
            st.markdown(f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>📧 <strong>Supplier Action:</strong> {sup_action}</div>", unsafe_allow_html=True)
    elif not run_an:
        st.markdown(
            "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
            "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
            "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
            unsafe_allow_html=True)

    # ── MONTE CARLO SIMULATION ────────────────────────────────────────────────
    sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
    note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
         "Shows probability of stockout and range of outcomes.")
    avg_d = mat_row["avg_monthly_demand"]
    std_d = mat_row["std_demand"]
    ss_v = mat_row["safety_stock"]
    rec = mat_row["rec_safety_stock"]
    lt_v = mat_row["lead_time"]
    if avg_d > 0 and std_d > 0:
        mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
        risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B", "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)
        mc_col1, mc_col2, mc_col3 = st.columns(3)
        with mc_col1:
            st.markdown(f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                        f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
                        f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
                        f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
                        f"</div>", unsafe_allow_html=True)
        with mc_col2:
            st.markdown(f"<div class='sc' style='flex-direction:column;gap:0;'>"
                        f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                        f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
                        f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                        f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
                        f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
                        f"<div style='display:flex;justify-content:space-between;'>"
                        f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
                        f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
                        f"</div>", unsafe_allow_html=True)
        with mc_col3:
            if mc["avg_breach_month"]:
                st.markdown(f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                            f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
                            f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
                            f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
                            f"</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                            f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
                            f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
                            f"</div>", unsafe_allow_html=True)
        if mc["end_stock_distribution"]:
            dist = mc["end_stock_distribution"]
            fig_mc = go.Figure()
            fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
                                          marker_color=ORANGE, marker_line_width=0, opacity=0.7))
            if ss_v > 0:
                fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot",
                                 line_width=1.5, annotation_text=f"Safety Stock {round(ss_v)}",
                                 annotation_font_color="#EF4444", annotation_font_size=9)
            ct(fig_mc, 180)
            fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
                                 margin=dict(l=8, r=8, t=16, b=8))
            st.plotly_chart(fig_mc, use_container_width=True)

    # ── STOCK TRAJECTORY ───────────────────────────────────────────────
    sec("Stock Trajectory")
    note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
         "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

    month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
    sh = get_stock_history(data, sel_mat).tail(month_filter)
    dh = get_demand_history(data, sel_mat).tail(month_filter)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
                             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
                             fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
                             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
    if ss_v > 0:
        fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
                                 name=f"SAP SS ({round(ss_v)})", yaxis="y1",
                                 line=dict(color="#EF4444", width=1.5, dash="dot")))
    if rec > ss_v:
        fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
                                 name=f"ARIA SS ({round(rec)})", yaxis="y1",
                                 line=dict(color="#22C55E", width=1.5, dash="dash")))
    if len(dh) > 0:
        dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
        if len(dh_aligned) > 0:
            fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
                                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
                                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
    ct(fig, 320)
    fig.update_layout(
        yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
        yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
        xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── SAFETY STOCK AUDIT ────────────────────────────────────────────────────
    ss_col, repl_col = st.columns(2)
    with ss_col:
        sec("Safety Stock Audit")
        note("SAP SS: Material Master → Safety Stock column. "
             "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
             "Current Inventory SS = 0 for all SKUs (known data gap).")
        gap = rec - ss_v
        gp = (gap / ss_v * 100) if ss_v > 0 else 100
        if gap > 10:
            gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
        else:
            gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
        st.markdown(
            f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
            f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
            f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
            f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
            f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
            f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
            f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
            f"</div>", unsafe_allow_html=True)

        if st.session_state.azure_client and analysis:
            if st.button("◈ Get SS Recommendation", key="ss_rec"):
                with st.spinner("ARIA analysing safety stock…"):
                    ss_ctx = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
                              f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
                              f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
                              f"Monte Carlo breach probability: {run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
                    rec_txt = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT,
                                             "Should the safety stock be adjusted? Give a specific recommendation with reasoning and the recommended value.",
                                             ss_ctx)
                st.markdown(f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ SS Recommendation</div><div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>", unsafe_allow_html=True)

    with repl_col:
        sec("Replenishment Details")
        repl_t = mat_row["repl_triggered"]
        repl_q = int(mat_row["repl_quantity"])
        repl_s = int(mat_row["repl_shortfall"])
        repl_f = mat_row["repl_formula"]
        if repl_t:
            st.markdown(
                f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
                f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
                f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
                f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
                f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
                f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
                f"</table></div>", unsafe_allow_html=True)
        else:
            st.markdown(
                f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
                f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
                f"✓ No replenishment triggered — stock above safety stock.<br>"
                f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
                f"</div>", unsafe_allow_html=True)

    # ── BOM Components ─────────────────────────────────────────────────────────
    bom = get_bom_components(data, sel_mat)
    if len(bom) > 0:
        sec("BOM Components & Supplier Intelligence")
        lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
        if len(lvl) > 0:
            bom_display = []
            for _, b in lvl.iterrows():
                fq = "✓ Fixed=1" if b.get("Fixed Qty Flag", False) else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—"
                sup = b.get("Supplier Display", "—")
                loc = b.get("Supplier Location", "—")
                transit = b.get("Transit Days", None)
                bom_display.append({
                    "Material": str(b["Material"]),
                    "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
                    "Qty": fq,
                    "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
                    "Procurement": b.get("Procurement Label", "—"),
                    "Supplier": sup,
                    "Location": loc,
                    "Transit": f"{transit}d" if transit is not None else "—",
                })
            df_bom_disp = pd.DataFrame(bom_display)
            sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
            gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
            gb3.configure_column("Material", width=85)
            gb3.configure_column("Description", width=220)
            gb3.configure_column("Qty", width=78)
            gb3.configure_column("Unit", width=52)
            gb3.configure_column("Procurement", width=110)
            gb3.configure_column("Supplier", width=175, cellRenderer=sup_r2)
            gb3.configure_column("Location", width=130)
            gb3.configure_column("Transit", width=62)
            gb3.configure_grid_options(rowHeight=36, headerHeight=32)
            gb3.configure_default_column(resizable=True, sortable=True, filter=False)
            AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290, allow_unsafe_jscode=True, theme="alpine",
                   custom_css={".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
                               ".ag-header": {"background": "#F8FAFE!important"},
                               ".ag-row-even": {"background": "#FFFFFF!important"}, ".ag-row-odd": {"background": "#F8FAFE!important"}})

            # Supplier email draft
            if st.session_state.azure_client:
                external_suppliers = []
                for _, b in lvl.iterrows():
                    sup_raw = b.get("Supplier Name(Vendor)", "")
                    if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
                        email_raw = b.get("Supplier Email address(Vendor)", "")
                        email = str(email_raw) if pd.notna(email_raw) else "—"
                        if mat_row["repl_triggered"]:
                            existing = [s for s in external_suppliers if s["supplier"] == str(sup_raw).strip()]
                            if not existing:
                                external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

                if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
                    for sup_info in external_suppliers[:3]:
                        with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
                            email_txt = draft_supplier_email(
                                st.session_state.azure_client, AZURE_DEPLOYMENT,
                                sup_info["supplier"], sup_info["email"],
                                [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}])
                        st.markdown(
                            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
                            f"padding:12px 14px;margin-top:8px;'>"
                            f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
                            f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
                            f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
                            f"</div>", unsafe_allow_html=True)

    # Supplier consolidation
    consol = get_supplier_consolidation(data, summary)
    relevant = consol[consol.material_list.apply(lambda x: sel_mat in x) & (consol.finished_goods_supplied > 1)]
    if len(relevant) > 0:
        sec("Supplier Consolidation Opportunities")
        note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
        for _, r in relevant.iterrows():
            other_mats = [m for m in r["material_list"] if m != sel_mat]
            other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
            needs_order = r["consolidation_opportunity"]
            bc = "#22C55E" if not needs_order else "#F47B25"
            st.markdown(
                f"<div class='prow'>"
                f"<div style='font-size:14px;'>🏭</div>"
                f"<div style='flex:1;'>"
                f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
                f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
                f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
                f"</div>"
                f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
                f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
                f"</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RISK RADAR
# ══════════════════════════════════════════════════════════════════════════════
elif selected == "Risk Radar":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
        unsafe_allow_html=True)

    active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
    note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

    sec("Replenishment Priority Queue")
    note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")
    for _, row in active_m.sort_values("days_cover").iterrows():
        risk = row["risk"]
        if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
            continue
        brd = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
        bgc = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
        repl_q = int(row.get("repl_quantity", 0))
        lt = round(row["lead_time"])
        dc = round(row["days_cover"])
        stock = round(row["sih"])
        ss = round(row["safety_stock"])
        action_html = ""
        if repl_q > 0:
            action_html = (
                f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
                f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
                f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
                f"</div>")
        else:
            action_html = (
                f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
                f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>")
        st.markdown(
            f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
            f"{sbadge(risk)}"
            f"<div style='flex:1;margin-left:8px;'>"
            f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
            f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
            f"</div>"
            f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
            + "".join([
                f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
                f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
                f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
                for val, lbl, vc in [
                    (str(stock), "SIH", "#EF4444" if stock < ss else "#1E293B"),
                    (str(ss), "SAP SS", "#1E293B"),
                    (f"{dc}d", "Cover", "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
                    (f"{lt}d", "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
                ]
            ])
            + f"</div></div>{action_html}",
            unsafe_allow_html=True)

    sec("Historical Breach Timeline")
    note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")
    breach_events = []
    for _, row in active_m.iterrows():
        sh_r = get_stock_history(data, row["material"])
        ss = row["safety_stock"]
        if ss <= 0:
            continue
        for _, sr in sh_r.iterrows():
            s = 0
            if sr["Gross Stock"] < ss:
                s = 2
            elif sr["Gross Stock"] < ss * 1.5:
                s = 1
            breach_events.append({"Material": row["name"][:22], "Period": sr["label"], "period_raw": sr["Fiscal Period"], "Status": s})
    if breach_events:
        df_be = pd.DataFrame(breach_events)
        ap = df_be.drop_duplicates("period_raw").sort_values("period_raw")
        sc_ = [fmt_p(p) for p in ap["period_raw"].tolist()]
        pv = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
        pv = pv[[c for c in sc_ if c in pv.columns]]
        fig_bt = go.Figure(data=go.Heatmap(
            z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
            colorscale=[[0, "#F8FAFE"], [0.49, "#F8FAFE"], [0.5, "rgba(245,158,11,0.35)"], [0.99, "rgba(245,158,11,0.35)"], [1, "rgba(239,68,68,0.55)"]],
            showscale=True, colorbar=dict(title="", tickvals=[0, 1, 2], ticktext=["Safe", "Warning", "Breach"], thickness=10, len=0.6, tickfont=dict(size=9)),
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>", zmin=0, zmax=2))
        ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
        fig_bt.update_layout(xaxis=dict(tickangle=-40, tickfont=dict(size=9)), yaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(fig_bt, use_container_width=True)
        if st.session_state.azure_client:
            if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
                with st.spinner("ARIA interpreting…"):
                    chart_data = {"total_breach_events": int(summary["breach_count"].sum()),
                                  "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
                                  "worst_material": summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
                                  "worst_count": int(summary["breach_count"].max())}
                    interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT, "Historical Breach Timeline heatmap", chart_data)
                st.markdown(f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div><div class='ib' style='margin-top:4px;'>{interp}</div></div>", unsafe_allow_html=True)

    sec("Safety Stock Coverage Gap Analysis")
    gap_data = active_m.copy()
    gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
    gap_data = gap_data.sort_values("ss_gap", ascending=True)
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h", name="SAP Safety Stock",
                             marker_color="rgba(239,68,68,0.5)", marker_line_width=0))
    fig_gap.add_trace(go.Bar(y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h", name="ARIA Recommended (95% SL)",
                             marker_color="rgba(34,197,94,0.5)", marker_line_width=0))
    fig_gap.add_trace(go.Scatter(y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers", name="Current Stock (SIH)",
                                 marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white"))))
    ct(fig_gap, 240)
    fig_gap.update_layout(barmode="overlay", xaxis_title="Units", legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
    st.plotly_chart(fig_gap, use_container_width=True)
    note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
         "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")
    if st.session_state.azure_client:
        if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
            with st.spinner("ARIA interpreting…"):
                cd = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
                interp2 = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT, "Safety Stock Coverage Gap chart", cd,
                                          "Which materials have the most concerning safety stock gaps and what should procurement prioritise?")
            st.markdown(f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div><div class='ib' style='margin-top:4px;'>{interp2}</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO ENGINE
# ══════════════════════════════════════════════════════════════════════════════
elif selected == "Scenario Engine":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Scenario Engine</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "Forward simulation · Supply disruption · Historical replay · LLM interpretation</div>",
        unsafe_allow_html=True)

    sim_tab, dis_tab, rep_tab = st.tabs(["📈  Demand Shock", "🔴  Supply Disruption", "↺  Historical Replay"])

    with sim_tab:
        st.markdown("<div style='padding:8px 0;font-size:12px;color:var(--t2);'>"
                    "<strong>Demand Shock</strong> simulates how different demand levels affect your stock over 6 months. "
                    "Use the shock month/multiplier to model sudden demand spikes (e.g. seasonal peak or unexpected order).</div>", unsafe_allow_html=True)
        cc2, rc = st.columns([1, 2])
        with cc2:
            sec("Controls")
            sim_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
            sn = st.selectbox("Material", list(sim_opts.keys()), key="sm")
            sid = sim_opts[sn]
            sr = summary[summary.material == sid].iloc[0]
            ad = sr["avg_monthly_demand"]
            ss_sim = sr["safety_stock"]
            lot_sim = sr["lot_size"]
            lt_sim = sr["lead_time"]
            st.markdown(f'<div class="chip" style="margin-bottom:8px;font-size:10px;">SIH: {round(sr["sih"])} · SS: {round(ss_sim)} · LT: {round(lt_sim)}d · Lot: {round(lot_sim)}</div>', unsafe_allow_html=True)
            st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:4px;'>Expected demand/month</div>", unsafe_allow_html=True)
            ed = st.slider("ed", int(ad * 0.3), int(ad * 3 + 50), int(ad), step=5, label_visibility="collapsed")
            son = st.toggle("Add demand shock", False, key="son", help="Simulates a sudden spike in one specific month")
            smo = smx = None
            if son:
                st.markdown("<div style='font-size:10px;color:var(--t3);'>Shock month: which month the spike occurs</div>", unsafe_allow_html=True)
                smo = st.slider("Shock month", 1, 6, 2, key="smo")
                st.markdown("<div style='font-size:10px;color:var(--t3);'>Multiplier: how many times the normal demand</div>", unsafe_allow_html=True)
                smx = st.slider("Multiplier", 1.5, 5.0, 2.5, step=0.5, key="smx")
            oon = st.toggle("Place order", False, key="oon", help="Simulates placing an emergency order that arrives after the lead time")
            oq = ot = None
            if oon:
                repl_default = max(int(max(ss_sim - sr["sih"], 0) / max(lot_sim, 1)) * int(lot_sim) if lot_sim > 0 else int(max(ss_sim - sr["sih"], 0)), 100)
                oq = st.slider("Order qty", 50, 2000, repl_default, step=50)
                ot = st.slider("Arrives (days)", 1, 60, int(lt_sim))
            rsim = st.button("▶  Run Demand Simulation", use_container_width=True)

        with rc:
            sec("6-Month Projection")
            if rsim or st.session_state.get("sim_ran"):
                mos = 6
                stk = sr["sih"]
                ss = ss_sim
                scns = {"Low (−40%)": [ed * 0.6] * mos, "Expected": [ed] * mos, "High (+60%)": [ed * 1.6] * mos}
                if son and smo and smx:
                    for k in scns:
                        if k != "Low (−40%)":
                            scns[k][smo - 1] = ed * smx
                oa = int(ot / 30) if oon and ot else None
                fs = go.Figure()
                scc_m = {"Low (−40%)": "#22C55E", "Expected": ORANGE, "High (+60%)": "#EF4444"}
                bi = {}
                for sc_k, dems in scns.items():
                    proj = []
                    s = stk
                    for m, d in enumerate(dems):
                        if oon and oq and m == oa:
                            s += oq
                        s = max(0.0, s - d)
                        proj.append(s)
                    bi[sc_k] = next((m + 1 for m, sp in enumerate(proj) if sp < max(ss, 1)), None)
                    fs.add_trace(go.Scatter(x=[f"M{i+1}" for i in range(mos)], y=proj, mode="lines+markers", name=sc_k,
                                            line=dict(color=scc_m[sc_k], width=2.5), marker=dict(size=5, color=scc_m[sc_k])))
                if ss > 0:
                    fs.add_hline(y=ss, line_color="#EF4444", line_dash="dot", line_width=1.5,
                                 annotation_text=f"SAP SS ({round(ss)})", annotation_font_color="#EF4444", annotation_font_size=9)
                ct(fs, 270)
                st.plotly_chart(fs, use_container_width=True)
                st.session_state["sim_ran"] = True
                vc = st.columns(3)
                for col, (sc_k, br) in zip(vc, bi.items()):
                    cl = "#EF4444" if br else "#22C55E"
                    bg = "#FEF2F2" if br else "#F0FDF4"
                    txt = f"⛔ Breach M{br}" if br else "✓ Safe 6mo"
                    with col:
                        st.markdown(f"<div class='sc' style='padding:9px 11px;flex-direction:column;gap:2px;'><div style='font-size:9px;color:var(--t3);'>{sc_k}</div><div style='font-size:12px;font-weight:800;color:{cl};background:{bg};padding:3px 7px;border-radius:6px;'>{txt}</div></div>", unsafe_allow_html=True)
                note(f"Replenishment qty: CEILING(max(0,SS−SIH)/FLS)×FLS = {int(math.ceil(max(0, ss - stk) / lot_sim) * lot_sim) if lot_sim > 0 else 0} units")
                if st.session_state.azure_client and rsim:
                    with st.spinner("ARIA evaluating…"):
                        sv = simulate_scenario(st.session_state.azure_client, AZURE_DEPLOYMENT, sn, stk, ss, lt_sim, lot_sim,
                                               {"low": ed * 0.6, "expected": ed, "high": ed * 1.6},
                                               {"quantity": oq, "timing_days": ot} if oon else None)
                    urg = sv.get("urgency", "MONITOR")
                    uc = {"ACT TODAY": "#EF4444", "ACT THIS WEEK": "#F59E0B", "MONITOR": ORANGE, "SAFE": "#22C55E"}.get(urg, ORANGE)
                    st.markdown(f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict</div><div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'><span style='font-size:12px;font-weight:800;color:{uc};'>{urg}</span><span class='chip'>Min order: {sv.get('min_order_recommended', '—')} units</span></div><div class='ib'>{sv.get('simulation_verdict', '')}</div></div>", unsafe_allow_html=True)

    with dis_tab:
        st.markdown("<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
                    "<strong>Supply Disruption</strong> simulates a freeze in replenishment across selected materials. "
                    "This models scenarios like supplier insolvency, geopolitical disruption, or production shutdown. "
                    "ARIA ranks which SKUs breach safety stock first and by how much.</div>", unsafe_allow_html=True)
        note("Formula: daily consumption × disruption days = stock consumed. "
             "Breach = remaining stock < Safety Stock. Emergency order = CEILING(Shortfall/FLS)×FLS.")
        dc2, dr = st.columns([1, 2])
        with dc2:
            sec("Disruption Parameters")
            st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:3px;'>Duration of supply freeze</div>", unsafe_allow_html=True)
            disruption_days = st.slider("days", 7, 90, 30, step=7, label_visibility="collapsed", key="dis_days")
            affected = st.multiselect("Affected materials (blank=all)", [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()], key="dis_mats")
            run_dis = st.button("🔴  Run Disruption", use_container_width=True)
        with dr:
            sec("Impact — Ranked by Severity")
            if run_dis or st.session_state.get("dis_ran"):
                adis = summary[summary.risk != "INSUFFICIENT_DATA"]
                if affected:
                    adis = adis[adis.name.isin(affected)]
                sku_data = [{"material": r["material"], "name": r["name"], "current_stock": r["sih"], "safety_stock": r["safety_stock"],
                             "lead_time": r["lead_time"], "fixed_lot_size": r["lot_size"], "avg_monthly_demand": r["avg_monthly_demand"],
                             "risk": r["risk"]} for _, r in adis.iterrows()]
                results = simulate_multi_sku_disruption(None, None, disruption_days, sku_data)
                st.session_state["dis_ran"] = True
                for i, r in enumerate(results):
                    bc = r["breach_occurs"]
                    brd = "#EF4444" if bc else "#22C55E"
                    bgc = "rgba(239,68,68,0.03)" if bc else "#FFFFFF"
                    days_txt = f"Breach Day {r['days_to_breach']}" if bc and r["days_to_breach"] is not None else (f"Already breached" if bc else f"Safe for {disruption_days}d")
                    st.markdown(
                        f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};margin-bottom:6px;'>"
                        f"<div style='min-width:22px;font-size:13px;font-weight:900;color:{brd};'>{i+1}</div>"
                        f"<div style='font-size:16px;'>{'⛔' if bc else '✓'}</div>"
                        f"<div style='flex:1;'>"
                        f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['name']}</div>"
                        f"<div style='font-size:10px;color:{brd};font-weight:600;margin-top:1px;'>{days_txt}</div>"
                        f"</div>"
                        f"<div style='display:grid;grid-template-columns:repeat(4,62px);gap:4px;text-align:center;'>"
                        + "".join([f"<div style='background:var(--s3);border-radius:5px;padding:4px;'><div style='font-size:11px;font-weight:800;color:{c};'>{v}</div><div style='font-size:8px;color:var(--t3);'>{l}</div></div>"
                                   for v, l, c in [(str(r["stock_at_end"]), "End", ("#EF4444" if r["shortfall_units"] > 0 else "#22C55E")),
                                                   (str(r["shortfall_units"]), "Short", ("#EF4444" if r["shortfall_units"] > 0 else "#94A3B8")),
                                                   (f"{r['lead_time']}d", "LT", "#1E293B"),
                                                   (str(r["reorder_qty"]), "Order", "#EF4444" if r["reorder_qty"] > 0 else "#94A3B8")]])
                        + f"</div></div>", unsafe_allow_html=True)
                if st.session_state.azure_client and run_dis:
                    breached = [r for r in results if r["breach_occurs"]]
                    if breached:
                        ctx_dis = f"Disruption: {disruption_days}d freeze. Breaches: {', '.join([r['name'] for r in breached])}. Worst: {breached[0]['name']} on day {breached[0]['days_to_breach'] or 0}."
                        with st.spinner("ARIA evaluating…"):
                            dv = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, "2-sentence executive verdict on this supply disruption. What is most critical?", ctx_dis)
                        st.markdown(f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA DISRUPTION VERDICT</div><div class='ib' style='margin-top:4px;'>{dv}</div></div>", unsafe_allow_html=True)

    with rep_tab:
        st.markdown("<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
                    "<strong>Historical Replay</strong> shows what actually happened in a past period and reconstructs when ARIA would have triggered an order signal — demonstrating the value of predictive replenishment.</div>", unsafe_allow_html=True)
        rp_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
        rp_sn = st.selectbox("Material", list(rp_opts.keys()), key="rp_mat")
        rp_sid = rp_opts[rp_sn]
        rp_sr = summary[summary.material == rp_sid].iloc[0]
        shrp = get_stock_history(data, rp_sid)
        pds_lbl = shrp["label"].tolist()
        if len(pds_lbl) > 4:
            rps = st.selectbox("Replay from period", pds_lbl[:-3], index=min(8, len(pds_lbl) - 4), key="rps")
            if st.button("↺  Replay this period", key="rpb"):
                idx = pds_lbl.index(rps)
                rd = shrp.iloc[idx:idx+6]
                ssr = rp_sr["safety_stock"]
                fr = go.Figure()
                fr.add_trace(go.Scatter(x=rd["label"], y=rd["Gross Stock"], mode="lines+markers", name="Actual Stock",
                                        line=dict(color=ORANGE, width=2.5), marker=dict(size=7, color=ORANGE),
                                        fill="tozeroy", fillcolor="rgba(244,123,37,0.07)",
                                        hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>"))
                if ssr > 0:
                    fr.add_hline(y=ssr, line_color="#EF4444", line_dash="dot", annotation_text=f"SAP SS {round(ssr)}", annotation_font_color="#EF4444")
                br2 = rd[rd["Gross Stock"] < max(ssr, 1)]
                if len(br2) > 0:
                    bp = br2.iloc[0]["label"]
                    prev_idx = max(0, rd.index.tolist().index(br2.index[0]) - 1)
                    fr.add_vline(x=bp, line_color="#EF4444", line_dash="dash", annotation_text="⛔ Breach", annotation_font_color="#EF4444")
                    fr.add_vline(x=rd.iloc[prev_idx]["label"], line_color="#22C55E", line_dash="dash", annotation_text="◈ ARIA signal", annotation_font_color="#22C55E")
                ct(fr, 260)
                st.plotly_chart(fr, use_container_width=True)
                msg = "⛔ Breach detected. ARIA would have signalled an order one period earlier." if len(br2) > 0 else "✓ No breach in this period — stock remained above safety stock."
                mc2 = "#EF4444" if len(br2) > 0 else "#22C55E"
                mb2 = "#FEF2F2" if len(br2) > 0 else "#F0FDF4"
                st.markdown(f"<div style='font-size:11px;color:{mc2};padding:7px 11px;background:{mb2};border-radius:8px;'>{msg}</div>", unsafe_allow_html=True)
    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPPLY NETWORK
# ══════════════════════════════════════════════════════════════════════════════
elif selected == "Supply Network":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
        unsafe_allow_html=True)

    snn = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
    snid = summary[summary.name == snn]["material"].values[0]
    snr = summary[summary.material == snid].iloc[0]
    bsn = get_bom_components(data, snid)

    if not len(bsn):
        st.markdown("<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div><div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>", unsafe_allow_html=True)
    else:
        cw = int(bsn["Supplier Name(Vendor)"].notna().sum())
        cn = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
        us = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
        tc = len(bsn)
        inhouse_n = int((bsn["Procurement type"] == "E").sum())
        external_n = int((bsn["Procurement type"] == "F").sum())

        n1, n2, n3, n4 = st.columns(4)
        for col, val, lbl, vc in [(n1, tc, "Total Components", "#1E293B"), (n2, inhouse_n, "Revvity Inhouse", "#22C55E"),
                                  (n3, cn, "Missing Supplier", "#F59E0B" if cn > 0 else "#1E293B"), (n4, us, "Unique Ext Suppliers", "#1E293B")]:
            with col:
                st.markdown(f"<div class='sc'><div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div><div class='sl'>{lbl}</div></div></div>", unsafe_allow_html=True)

        sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

        with sn_tab:
            sec("BOM Propagation Map")
            note("Blue = External supplier named. Amber = External, no supplier data. Green = Revvity Inhouse production. Hover nodes for detail.")
            risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
            root_color = risk_color_map.get(snr["risk"], "#94A3B8")
            fig_tree = plot_bom_tree(bsn, snr["name"], root_color)
            st.plotly_chart(fig_tree, use_container_width=True)
            if st.session_state.azure_client:
                if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
                    with st.spinner("ARIA interpreting…"):
                        bom_ctx = {"material": snr["name"], "total_components": tc, "inhouse": inhouse_n,
                                   "external_named": cw - inhouse_n, "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"]}
                        interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT, "BOM Risk Propagation Map", bom_ctx,
                                                 "What are the key supply chain risks in this BOM and what should procurement prioritise?")
                        st.markdown(f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div><div class='ib'>{interp}</div></div>", unsafe_allow_html=True)

        with comp_tab:
            sec("Component Detail")
            bom_display2 = []
            for _, b in bsn.iterrows():
                fq_txt = "1 (Fixed)" if b.get("Fixed Qty Flag", False) else str(round(float(b.get("Effective Order Qty", b["Comp. Qty (CUn)"])), 3)) if pd.notna(b.get("Effective Order Qty", b["Comp. Qty (CUn)"])) else "—"
                bom_display2.append({
                    "Material": str(b["Material"]),
                    "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
                    "Level": str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
                    "Qty": fq_txt,
                    "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
                    "Type": b.get("Procurement Label", "—"),
                    "Supplier": b.get("Supplier Display", "—"),
                    "Location": b.get("Supplier Location", "—"),
                    "Transit": f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
                })
            df_bd2 = pd.DataFrame(bom_display2)
            sup_r3 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
            gb4 = GridOptionsBuilder.from_dataframe(df_bd2)
            gb4.configure_column("Material", width=82)
            gb4.configure_column("Description", width=215)
            gb4.configure_column("Level", width=85)
            gb4.configure_column("Qty", width=75)
            gb4.configure_column("Unit", width=50)
            gb4.configure_column("Type", width=100)
            gb4.configure_column("Supplier", width=170, cellRenderer=sup_r3)
            gb4.configure_column("Location", width=130)
            gb4.configure_column("Transit", width=58)
            gb4.configure_grid_options(rowHeight=36, headerHeight=32)
            gb4.configure_default_column(resizable=True, sortable=True, filter=False)
            AgGrid(df_bd2, gridOptions=gb4.build(), height=320, allow_unsafe_jscode=True, theme="alpine",
                   custom_css={".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
                               ".ag-header": {"background": "#F8FAFE!important"},
                               ".ag-row-even": {"background": "#FFFFFF!important"}, ".ag-row-odd": {"background": "#F8FAFE!important"}})

        with risk_tab:
            sec("Risk Cascade Analysis")
            risks = []
            if snr["risk"] in ["CRITICAL", "WARNING"]:
                risks.append({"icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
                              "title": f"Finished Good at {snr['risk'].title()} Risk",
                              "detail": f"{snr['name']} has {round(snr['days_cover'])}d of cover. SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. Production continuity at risk.",
                              "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today."})
            if cn > 0:
                risks.append({"icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                              "title": f"Missing Supplier Data — {cn} External Components",
                              "detail": f"{cn} of {external_n} external components have no named supplier. Single-source risk cannot be assessed for these.",
                              "action": "Procurement to verify and update BOM with supplier names and lead times."})
            if us <= 2 and us > 0:
                risks.append({"icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                              "title": f"Supplier Concentration — {us} Unique Supplier(s)",
                              "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
                              "action": "Evaluate dual-sourcing for critical external components."})
            ext_comps = bsn[bsn["Procurement type"] == "F"]
            if len(ext_comps) > 0:
                risks.append({"icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
                              "title": f"External Procurement: {len(ext_comps)} Components",
                              "detail": f"External components depend on supplier availability and transit times. "
                                        f"Suppliers located in: {', '.join(list(set([str(r) for r in bsn[bsn['Procurement type'] == 'F']['Supplier Location'].dropna().tolist()[:4]])))}.",
                              "action": "Review external component lead times — stock buffers for long-transit items."})
            if not risks:
                st.markdown("<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);font-size:12px;color:#14532d;'>✓ No critical propagation risks identified.</div>", unsafe_allow_html=True)
            else:
                for r in sorted(risks, key=lambda x: -x["sev"]):
                    st.markdown(
                        f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
                        f"border-left:4px solid {r['color']};border-radius:var(--r);"
                        f"padding:12px 14px;margin-bottom:8px;'>"
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
                        f"<span style='font-size:16px;'>{r['icon']}</span>"
                        f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
                        f"</div>"
                        f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
                        f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
                        f"</div>", unsafe_allow_html=True)

            consol2 = get_supplier_consolidation(data, summary)
            relevant2 = consol2[consol2.material_list.apply(lambda x: snid in x) & (consol2.finished_goods_supplied > 1) & consol2.consolidation_opportunity]
            if len(relevant2) > 0:
                sec("Supplier Consolidation Opportunities")
                for _, r2 in relevant2.iterrows():
                    others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
                    st.markdown(
                        f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
                        f"<div style='flex:1;'>"
                        f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
                        f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
                        f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
                        f"</div>"
                        f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
                        f"</div>", unsafe_allow_html=True)

            if st.session_state.azure_client:
                sec("Ask ARIA About This Network")
                uq = st.text_input("Question", placeholder="e.g. Which supplier poses the highest single-source risk?", key="snq", label_visibility="collapsed")
                if uq and st.button("Ask ARIA", key="sna"):
                    ctx3 = (f"Material: {snr['name']}, Risk: {snr['risk']}, Components: {tc}, Inhouse: {inhouse_n}, External: {external_n}, Missing supplier: {cn}, Unique suppliers: {us}, Suppliers: {', '.join(bsn['Supplier Name(Vendor)'].dropna().unique().tolist()[:5])}")
                    with st.spinner("Thinking…"):
                        ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
                    st.markdown(f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div><div class='ib'>{ans}</div></div>", unsafe_allow_html=True)

    st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
