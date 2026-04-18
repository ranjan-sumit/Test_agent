"""
ARIA Supply Intelligence · MResult
Complete rebuild — all feedback applied:
Command Center: date-formatted axes, better charts, GPT insight card, equal-height layout
Material Intelligence: demand bar chart, formatted dates, SS audit note
Risk Radar: complete redesign — replenishment priority queue + breach timeline
Scenario Engine: demand shock + supply disruption simulation tabs
Supply Network: BOM with readable text, visual risk cascade, component table
"""

import os, base64
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_option_menu import option_menu
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

from data_loader import (
    load_all, build_material_summary, get_stock_history,
    get_demand_history, get_bom_components, get_material_context, RISK_COLORS,
)
from agent import (
    get_azure_client, analyse_material, simulate_scenario,
    simulate_multi_sku_disruption, chat_with_data, PARAMETER_SOURCES,
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
  --bg:#F5F7FB;--surface:#FFFFFF;--s2:#F8FAFE;--s3:#F0F4F9;--s4:#E9EFF5;
  --orange:#F47B25;--orange-lt:#FF9F50;--orange-dk:#C45D0A;
  --og:rgba(244,123,37,0.12);--ob:rgba(244,123,37,0.07);--obr:rgba(244,123,37,0.25);
  --bl:rgba(0,0,0,0.06);--bl2:rgba(0,0,0,0.10);--bll:#E2E8F0;
  --t:#1E293B;--t2:#475569;--t3:#94A3B8;
  --green:#22C55E;--gbg:rgba(34,197,94,0.10);
  --amber:#F59E0B;--abg:rgba(245,158,11,0.10);
  --red:#EF4444;--rbg:rgba(239,68,68,0.08);
  --gbg2:rgba(100,116,139,0.08);
  --r:12px;--rl:16px;
  --fn:'Inter','Segoe UI',system-ui,-apple-system,sans-serif;
  --tr:0.2s cubic-bezier(0.4,0,0.2,1);
  --sh:0 1px 2px rgba(0,0,0,0.02),0 1px 3px rgba(0,0,0,0.03);
  --shm:0 6px 14px -6px rgba(0,0,0,0.08),0 1px 2px rgba(0,0,0,0.02);
}
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:var(--fn);color:var(--t);}
.stApp{background:var(--bg);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0!important;}

section[data-testid="stSidebar"]{background:var(--surface)!important;border-right:2px solid var(--bll)!important;overflow:hidden!important;min-width:240px!important;max-width:240px!important;}
section[data-testid="stSidebar"]>div{padding:0!important;overflow:hidden!important;}
section[data-testid="stSidebar"]::-webkit-scrollbar{display:none!important;}
section[data-testid="stSidebar"] *{color:var(--t2)!important;}
section[data-testid="stSidebar"] .stTextInput>div>div{background:rgba(244,123,37,0.04)!important;border:1px solid var(--obr)!important;border-radius:9px!important;font-size:12px!important;color:var(--t3)!important;}

.accent-bar{height:3px;background:linear-gradient(90deg,var(--orange-dk),var(--orange),var(--orange-lt),var(--orange));background-size:200% 100%;animation:shimmer 3s linear infinite;width:100%;}
@keyframes shimmer{0%{background-position:200%}100%{background-position:-200%}}
@keyframes pulse-dot{0%{box-shadow:0 0 0 0 rgba(34,197,94,0.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse-dot 2s infinite;display:inline-block;flex-shrink:0;}

.aria-topbar{height:54px;background:var(--surface);border-bottom:1px solid var(--bll);display:flex;align-items:center;padding:0 24px;gap:14px;}
.topbar-title{font-size:14px;font-weight:700;color:var(--t);}
.topbar-title span{color:var(--t3);font-weight:400;}
.tbadge{background:var(--ob);border:1px solid var(--obr);color:var(--orange);font-size:10px;font-weight:700;padding:2px 9px;border-radius:20px;}

.sc{background:var(--surface);border:1px solid var(--bll);border-radius:var(--rl);padding:14px 16px;display:flex;align-items:center;gap:12px;transition:all var(--tr);box-shadow:var(--sh);}
.sc:hover{border-color:var(--bl2);transform:translateY(-1px);box-shadow:var(--shm);}
.si{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.si svg{width:19px;height:19px;}
.si-o{background:var(--ob);border:1px solid var(--obr);}
.si-r{background:var(--rbg);border:1px solid rgba(239,68,68,0.2);}
.si-a{background:var(--abg);border:1px solid rgba(245,158,11,0.2);}
.si-g{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);}
.si-x{background:var(--gbg2);border:1px solid rgba(100,116,139,0.15);}
.sv{font-size:24px;font-weight:900;color:var(--t);letter-spacing:-1px;line-height:1;}
.sl{font-size:10px;color:var(--t2);margin-top:3px;}
.sd{font-size:10px;padding:2px 7px;border-radius:20px;font-weight:600;margin-left:auto;white-space:nowrap;}
.sd-u{background:var(--gbg);color:var(--green);}
.sd-w{background:var(--abg);color:var(--amber);}
.sd-c{background:var(--rbg);color:var(--red);}

.sb{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;}
.sb-c{background:var(--rbg);color:var(--red);border:1px solid rgba(239,68,68,0.2);}
.sb-w{background:var(--abg);color:var(--amber);border:1px solid rgba(245,158,11,0.2);}
.sb-h{background:var(--gbg);color:var(--green);border:1px solid rgba(34,197,94,0.2);}
.sb-n{background:var(--gbg2);color:var(--t2);border:1px solid var(--bll);}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
.dot-r{background:var(--red);}.dot-a{background:var(--amber);}.dot-g{background:var(--green);animation:pulse-dot 2s infinite;}.dot-n{background:var(--t3);}

.fc{background:var(--surface);border:1px solid var(--bll);border-radius:var(--rl);overflow:hidden;box-shadow:var(--sh);}
.fh{padding:12px 16px;border-bottom:1px solid var(--bll);display:flex;align-items:center;justify-content:space-between;}
.fht{font-size:12px;font-weight:700;color:var(--t);}
.flv{background:var(--gbg);border-radius:20px;padding:2px 8px;font-size:9px;color:var(--green);display:flex;align-items:center;gap:4px;}
.fi{display:flex;gap:10px;padding:9px 16px;border-bottom:1px solid var(--bll);transition:background var(--tr);}
.fi:last-child{border-bottom:none;}
.fi:hover{background:var(--s2);}
.fi-dc{display:flex;flex-direction:column;align-items:center;padding-top:4px;}
.fi-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.fi-line{width:1px;flex:1;background:var(--bll);min-height:14px;margin-top:3px;}
.fi-msg{font-size:11px;font-weight:500;color:var(--t);line-height:1.4;}
.fi-msg span{color:var(--orange);font-weight:700;}
.fi-time{font-size:9px;color:var(--t3);margin-top:1px;}
.fi-tag{font-size:8px;padding:2px 5px;border-radius:4px;margin-top:2px;display:inline-block;font-weight:700;}
.ft-c{background:var(--rbg);color:var(--red);}.ft-w{background:var(--abg);color:var(--amber);}
.ft-o{background:var(--gbg);color:var(--green);}.ft-i{background:var(--ob);color:var(--orange);}

.ic{background:var(--surface);border:1px solid var(--obr);border-radius:var(--rl);padding:20px 22px;margin:12px 0;box-shadow:0 0 0 3px var(--og);position:relative;}
.il{position:absolute;top:-10px;left:16px;background:var(--orange);color:#fff;font-size:9px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:2px 10px;border-radius:20px;}
.ih{font-size:15px;font-weight:800;color:var(--t);margin-bottom:8px;line-height:1.4;}
.ib{font-size:12px;color:var(--t2);line-height:1.8;}
.if_{display:flex;gap:8px;align-items:flex-start;margin:7px 0;font-size:11px;color:var(--t2);}
.id{width:5px;height:5px;border-radius:50%;background:var(--orange);margin-top:5px;flex-shrink:0;}

.sap-box{background:var(--abg);border:1px solid rgba(245,158,11,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#78350f;}
.sap-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#92400e;margin-bottom:4px;text-transform:uppercase;}
.rec-box{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;}
.rec-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#166534;margin-bottom:4px;text-transform:uppercase;}
.flag-box{background:var(--s2);border:1px dashed var(--bl2);border-radius:var(--rl);padding:24px;text-align:center;color:var(--t3);font-size:13px;}
.chip{display:inline-flex;align-items:center;padding:2px 9px;border-radius:6px;background:var(--s3);border:1px solid var(--bll);font-size:10px;color:var(--t2);font-weight:500;}
.sdv{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin:18px 0 10px;padding-bottom:7px;border-bottom:1px solid var(--bll);}
.pfooter{text-align:center;margin-top:28px;padding:14px 0 6px;border-top:1px solid var(--bll);font-size:11px;color:var(--t3);}
.pfooter strong{color:var(--orange);}
.mc{background:var(--surface);border:1px solid var(--bll);border-radius:var(--rl);padding:18px 20px;overflow:hidden;transition:all var(--tr);box-shadow:var(--sh);}
.mc:hover{border-color:var(--obr);transform:translateY(-2px);box-shadow:var(--shm);}

/* note box */
.note-box{background:rgba(244,123,37,0.04);border-left:3px solid var(--orange);border-radius:0 8px 8px 0;padding:8px 12px;font-size:11px;color:var(--t2);margin:8px 0;}

/* severity row */
.sev-row{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:var(--r);margin-bottom:6px;border:1px solid var(--bll);background:var(--surface);}
.sev-row:hover{border-color:var(--obr);box-shadow:var(--sh);}

.stButton>button{background:var(--orange);color:#fff;border:none;border-radius:var(--r);font-family:var(--fn);font-size:13px;font-weight:700;padding:8px 18px;transition:all var(--tr);box-shadow:0 2px 8px rgba(244,123,37,0.2);}
.stButton>button:hover{background:var(--orange-dk);border:none;box-shadow:0 4px 12px rgba(244,123,37,0.3);transform:translateY(-1px);}
.stSelectbox>div>div,.stTextInput>div>div{background:var(--s2)!important;border:1px solid var(--bll)!important;border-radius:var(--r)!important;font-size:13px!important;color:var(--t)!important;}
.nav-link{color:var(--t2)!important;background:transparent!important;border-radius:9px!important;font-size:13px!important;font-weight:500!important;}
.nav-link:hover{background:var(--s3)!important;color:var(--t)!important;}
.nav-link-selected{background:var(--ob)!important;color:var(--orange)!important;border:1px solid var(--obr)!important;font-weight:600!important;}
.nav-link .icon{color:inherit!important;}

/* AgGrid */
.ag-root-wrapper{border:1px solid var(--bll)!important;border-radius:var(--rl)!important;overflow:hidden;box-shadow:var(--sh);}
.ag-header{background:#F8FAFE!important;border-bottom:1px solid var(--bll)!important;}
.ag-header-cell-label{font-size:10px!important;font-weight:700!important;color:#475569!important;letter-spacing:0.3px;text-transform:uppercase;}
.ag-row-even{background:#FFFFFF!important;}.ag-row-odd{background:#F8FAFE!important;}
.ag-row:hover{background:rgba(244,123,37,0.03)!important;}
.ag-cell{display:flex;align-items:center;border-right:1px solid #F0F4F9!important;}

::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:2px;}
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────
def ct(fig, h=280):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", height=h,
        margin=dict(l=8,r=8,t=32,b=8),
        font=dict(family="Inter",color="#94A3B8",size=11),
        xaxis=dict(gridcolor="#F0F4F9",zerolinecolor="#F0F4F9",tickfont_color="#94A3B8",showline=False),
        yaxis=dict(gridcolor="#F0F4F9",zerolinecolor="#F0F4F9",tickfont_color="#94A3B8",showline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)",font_color="#94A3B8",font_size=10,orientation="h",y=1.1),
        hoverlabel=dict(bgcolor="#FFFFFF",font_color="#1E293B",bordercolor="#E2E8F0",font_size=11),
    )
    return fig

def fmt_period(p_str):
    """Convert '202403' → 'Mar '24'"""
    try:
        import pandas as pd
        return pd.to_datetime(str(p_str), format="%Y%m").strftime("%b '%y")
    except: return str(p_str)

def sbadge(risk):
    m={"CRITICAL":("sb-c","dot-r","⛔ Critical"),"WARNING":("sb-w","dot-a","⚠ Warning"),
       "HEALTHY":("sb-h","dot-g","✓ Healthy"),"INSUFFICIENT_DATA":("sb-n","dot-n","◌ No Data")}
    sc,dc,lb=m.get(risk,("sb-n","dot-n",risk))
    return '<span class="sb '+sc+'"><span class="dot '+dc+'"></span>'+lb+'</span>'

def sec(t):
    st.markdown('<div class="sdv">'+t+'</div>',unsafe_allow_html=True)

def note(t):
    st.markdown('<div class="note-box">'+t+'</div>',unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for k,v in [("data",None),("summary",None),("azure_client",None),
             ("agent_cache",{}),("sim_ran",False),("data_error",""),
             ("cc_insight",None)]:
    if k not in st.session_state: st.session_state[k]=v

# ── Auto-load ──────────────────────────────────────────────────────────────────
if st.session_state.data is None and not st.session_state.data_error:
    try:
        st.session_state.data    = load_all()
        st.session_state.summary = build_material_summary(st.session_state.data)
    except Exception as e:
        st.session_state.data_error = str(e)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    if _logo_b64:
        st.markdown(
            "<div style='padding:12px 16px 10px;border-bottom:1px solid var(--bll);"
            "display:flex;align-items:center;justify-content:center;'>"
            "<img src='data:image/jpeg;base64,"+_logo_b64+"' "
            "style='max-height:40px;max-width:160px;object-fit:contain;border-radius:6px;'/>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            "<div style='padding:12px 16px 10px;border-bottom:1px solid var(--bll);'>"
            "<div style='display:flex;align-items:center;gap:9px;'>"
            "<div style='width:28px;height:28px;background:var(--orange);border-radius:7px;"
            "display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:900;color:#fff;'>M</div>"
            "<div style='font-size:14px;font-weight:800;color:var(--t);'>MResult</div>"
            "</div></div>",unsafe_allow_html=True)

    if st.session_state.summary is not None:
        smry=st.session_state.summary
        crit=int((smry.risk=="CRITICAL").sum()); warn=int((smry.risk=="WARNING").sum())
        ok=int((smry.risk=="HEALTHY").sum()); nd=int((smry.risk=="INSUFFICIENT_DATA").sum())
        active=smry[smry.risk!="INSUFFICIENT_DATA"]
        worst=active.sort_values("days_cover").iloc[0] if len(active)>0 else None
        st.markdown(
            "<div style='padding:10px 14px;border-bottom:1px solid var(--bll);'>"
            "<div style='font-size:9px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;"
            "color:var(--t3);margin-bottom:7px;'>Platform Status · FI11</div>"
            "<div style='display:grid;grid-template-columns:1fr 1fr;gap:5px;'>"
            "<div style='background:var(--rbg);border:1px solid rgba(239,68,68,0.15);border-radius:7px;"
            "padding:7px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:var(--red);line-height:1;'>"+str(crit)+"</div>"
            "<div style='font-size:9px;color:var(--red);margin-top:1px;'>Critical</div></div>"
            "<div style='background:var(--abg);border:1px solid rgba(245,158,11,0.15);border-radius:7px;"
            "padding:7px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:var(--amber);line-height:1;'>"+str(warn)+"</div>"
            "<div style='font-size:9px;color:var(--amber);margin-top:1px;'>Warning</div></div>"
            "<div style='background:var(--gbg);border:1px solid rgba(34,197,94,0.15);border-radius:7px;"
            "padding:7px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:var(--green);line-height:1;'>"+str(ok)+"</div>"
            "<div style='font-size:9px;color:var(--green);margin-top:1px;'>Healthy</div></div>"
            "<div style='background:var(--gbg2);border:1px solid var(--bll);border-radius:7px;"
            "padding:7px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:var(--t2);line-height:1;'>"+str(nd)+"</div>"
            "<div style='font-size:9px;color:var(--t3);margin-top:1px;'>No Data</div></div></div>"
            +(
                "<div style='margin-top:7px;padding:6px 9px;background:var(--rbg);"
                "border:1px solid rgba(239,68,68,0.2);border-radius:7px;font-size:10px;color:var(--red);'>"
                "⛔ "+worst["name"][:22]+" — "+str(round(worst["days_cover"]))+"d cover"
                "</div>" if worst is not None and worst["days_cover"]<30 else ""
            )+"</div>",unsafe_allow_html=True)

    ai_on=st.session_state.azure_client is not None
    dot="#22C55E" if ai_on else "#CBD5E1"; lbl="AI Agent Online" if ai_on else "AI Agent Offline"
    st.markdown(
        "<div style='padding:7px 14px;border-bottom:1px solid var(--bll);"
        "border-top:1px solid var(--bll);display:flex;align-items:center;gap:6px;'>"
        "<div style='width:6px;height:6px;border-radius:50%;background:"+dot+";"
        +("animation:pulse-dot 2s infinite;" if ai_on else "")+"flex-shrink:0;'></div>"
        "<span style='font-size:10px;color:"+dot+";font-weight:600;'>"+lbl+"</span>"
        "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span></div>",
        unsafe_allow_html=True)

    st.markdown("<div style='padding:7px 14px 4px;'>"
                "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
                "</div>",unsafe_allow_html=True)
    azure_key=st.text_input("k","",type="password",placeholder="Enter Azure OpenAI key…",
                             label_visibility="collapsed",key="az_key")
    if azure_key and not st.session_state.azure_client:
        try: st.session_state.azure_client=get_azure_client(azure_key,AZURE_ENDPOINT,AZURE_API_VER)
        except: pass
    st.markdown("<div style='padding:6px 14px;border-top:1px solid var(--bll);'>"
                "<div style='font-size:9px;color:var(--t3);text-align:center;'>Supply Intelligence · FI11 Turku</div>"
                "</div>",unsafe_allow_html=True)

# ── Guard ──────────────────────────────────────────────────────────────────────
if st.session_state.data_error:
    st.error("Data load failed: "+st.session_state.data_error); st.stop()
if st.session_state.data is None:
    st.info("Loading…"); st.stop()

data=st.session_state.data; summary=st.session_state.summary

# ── Topbar ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="accent-bar"></div>',unsafe_allow_html=True)
st.markdown(
    "<div class='aria-topbar'>"
    "<div class='topbar-title'>Supply Intelligence <span>/ FI11 Turku · Apr 2026</span></div>"
    "<div class='tbadge'>◈ Live</div>"
    "<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
    "<span class='live-dot'></span><span style='font-size:10px;color:var(--t3);'>Real-time</span>"
    "<div style='width:30px;height:30px;border-radius:8px;"
    "background:linear-gradient(135deg,var(--orange-dk),var(--orange));"
    "display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;'>AI</div>"
    "</div></div>",unsafe_allow_html=True)

# ── Navigation ─────────────────────────────────────────────────────────────────
selected=option_menu(
    menu_title=None,
    options=["Command Center","Material Intelligence","Risk Radar","Scenario Engine","Supply Network"],
    icons=["grid","search","broadcast","lightning","diagram-3"],
    orientation="horizontal",
    styles={
        "container":{"padding":"6px 24px","background-color":"#FFFFFF","border-bottom":"1px solid #E2E8F0"},
        "nav-link":{"font-family":"Inter,sans-serif","font-size":"12px","font-weight":"500",
                    "color":"#475569","padding":"7px 14px","border-radius":"9px","margin":"0 2px","--hover-color":"#F0F4F9"},
        "nav-link-selected":{"background-color":"rgba(244,123,37,0.07)","color":"#F47B25",
                              "border":"1px solid rgba(244,123,37,0.25)","font-weight":"600"},
        "icon":{"font-size":"13px"},
    },
)
st.markdown('<div style="padding:18px 24px;">',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMMAND CENTER
# ══════════════════════════════════════════════════════════════════════════════
if selected=="Command Center":
    total=len(summary); crit_n=int((summary.risk=="CRITICAL").sum())
    warn_n=int((summary.risk=="WARNING").sum()); ok_n=int((summary.risk=="HEALTHY").sum())
    active=summary[summary.risk!="INSUFFICIENT_DATA"]
    min_row=active.sort_values("days_cover").iloc[0] if len(active)>0 else None

    SVG={
        "agents":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
        "alert": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        "check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
        "pulse": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    }
    def kpi(col,svg,si,val,vc,lbl,dlt=None,dc="sd-u"):
        dh=('<span class="sd '+dc+'">'+dlt+'</span>') if dlt else ""
        with col:
            st.markdown("<div class='sc'><div class='si "+si+"'>"+svg+"</div>"
                        "<div style='flex:1;min-width:0;'>"
                        "<div class='sv' style='color:"+vc+";'>"+str(val)+"</div>"
                        "<div class='sl'>"+lbl+"</div></div>"+dh+"</div>",unsafe_allow_html=True)

    k1,k2,k3,k4=st.columns(4)
    kpi(k1,SVG["agents"],"si-o",total,"#1E293B","Total Materials")
    kpi(k2,SVG["alert"],"si-r",crit_n,"#EF4444","Critical Alerts",
        "⛔ "+str(crit_n)+" urgent" if crit_n>0 else "✓ None","sd-c" if crit_n>0 else "sd-u")
    kpi(k3,SVG["pulse"],"si-a",warn_n,"#F59E0B","Under Watch",
        str(warn_n)+" materials","sd-w" if warn_n>0 else "sd-u")
    kpi(k4,SVG["check"],"si-g",ok_n,"#22C55E","Healthy","↑ Operating","sd-u")

    # ── ARIA GPT Insight Card (refreshable) ────────────────────────────────────
    st.markdown("<div style='height:14px;'></div>",unsafe_allow_html=True)

    ai_col, refresh_col = st.columns([10,1])
    with ai_col:
        st.markdown("<div style='font-size:13px;font-weight:700;color:var(--t);'>◈ ARIA Overview — Plant Intelligence</div>",unsafe_allow_html=True)
    with refresh_col:
        refresh_insight = st.button("↺",key="ref_insight",help="Refresh ARIA overview")

    if st.session_state.azure_client and (st.session_state.cc_insight is None or refresh_insight):
        with st.spinner("ARIA generating plant overview…"):
            crit_mat = summary[summary.risk=="CRITICAL"]
            crit_names = ", ".join(crit_mat["name"].tolist()) if len(crit_mat)>0 else "none"
            total_breach = int(summary["breach_count"].sum())
            ctx_str = (
                f"Plant FI11 Turku — {total} materials tracked. "
                f"Critical: {crit_n} ({crit_names}). Warning: {warn_n}. Healthy: {ok_n}. "
                f"Total historical breach events: {total_breach}. "
                f"Most critical: {min_row['name'] if min_row is not None else 'N/A'} with "
                f"{round(min_row['days_cover'],1) if min_row is not None else 'N/A'} days cover, "
                f"stock={round(min_row['current_stock']) if min_row is not None else 'N/A'} vs SS={round(min_row['safety_stock']) if min_row is not None else 'N/A'}. "
                f"Data covers Jan 2021–Sep 2026."
            )
            try:
                insight = chat_with_data(
                    st.session_state.azure_client, AZURE_DEPLOYMENT,
                    "Provide a 3-sentence executive briefing on the current supply chain health at this plant. "
                    "Identify the single biggest risk, what is driving it, and what action is needed today.",
                    ctx_str
                )
                st.session_state.cc_insight = insight
            except Exception as e:
                st.session_state.cc_insight = "ARIA analysis unavailable — connect Azure API key in sidebar."

    if st.session_state.cc_insight:
        st.markdown(
            "<div class='ic' style='margin:8px 0 16px;'>"
            "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
            "<div class='ib' style='margin-top:4px;'>"+st.session_state.cc_insight+"</div>"
            "</div>",unsafe_allow_html=True)
    elif not st.session_state.azure_client:
        st.markdown(
            "<div style='padding:10px 14px;background:var(--ob);border:1px solid var(--obr);"
            "border-radius:9px;font-size:12px;color:var(--orange);margin-bottom:12px;'>"
            "Enter Azure API key in sidebar to enable ARIA plant intelligence overview.</div>",
            unsafe_allow_html=True)

    # ── MAIN ROW: Health Board (left 60%) + Feed (right 40%) ──────────────────
    board_col, feed_col = st.columns([3, 2], gap="medium")

    # ── LEFT: Material Health Board ────────────────────────────────────────────
    with board_col:
        st.markdown(
            "<div style='display:flex;align-items:baseline;gap:8px;margin-bottom:10px;'>"
            "<div style='font-size:13px;font-weight:800;color:var(--t);'>Material Health Board</div>"
            "<div style='font-size:11px;color:var(--t3);'>Click row · Sortable · Live data</div>"
            "</div>",unsafe_allow_html=True)

        grid_rows=[]
        for _,row in summary.iterrows():
            sh2=get_stock_history(data,row["material"]); dh2=get_demand_history(data,row["material"])
            nz=dh2[dh2.demand>0]; avg=float(nz.demand.mean()) if len(nz)>0 else 0
            ss=row["safety_stock"]; br=sh2[sh2["Gross Stock"]<max(ss,1)] if ss>0 else pd.DataFrame()
            lb=fmt_period(br["Fiscal Period"].iloc[-1]) if len(br)>0 else "—"
            spark=sh2["Gross Stock"].tail(8).tolist()
            grid_rows.append({
                "Risk":row["risk"],"Material":row["name"],"Stock":int(row["current_stock"]),
                "SAP SS":int(ss),"ARIA SS":int(row["rec_safety_stock"]),
                "Days Cover":int(row["days_cover"]) if row["days_cover"]<999 else 0,
                "Demand/mo":round(avg,0),"Trend":row["trend"],
                "Breaches":int(row["breach_count"]),"Last Breach":lb,
                "Spark":(",".join([str(round(v)) for v in spark])),
                "Order Qty":int(row.get("repl_quantity",0)),
            })
        df_grid=pd.DataFrame(grid_rows)

        status_r=JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 8px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
        spark_r=JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=80,h=24,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
        cover_r=JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:5px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:26px;">${v}d</span>`;}getGui(){return this.e;}}""")
        order_r=JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText='Order '+v;}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
        row_style=JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

        gb=GridOptionsBuilder.from_dataframe(df_grid)
        gb.configure_column("Risk",cellRenderer=status_r,width=112,pinned="left")
        gb.configure_column("Material",width=185,pinned="left")
        gb.configure_column("Stock",width=68,type=["numericColumn"])
        gb.configure_column("SAP SS",width=68,type=["numericColumn"])
        gb.configure_column("ARIA SS",width=72,type=["numericColumn"])
        gb.configure_column("Days Cover",width=128,cellRenderer=cover_r)
        gb.configure_column("Demand/mo",width=82,type=["numericColumn"])
        gb.configure_column("Trend",width=76)
        gb.configure_column("Breaches",width=72,type=["numericColumn"])
        gb.configure_column("Last Breach",width=90)
        gb.configure_column("Spark",width=98,cellRenderer=spark_r,headerName="8m Trend")
        gb.configure_column("Order Qty",width=90,cellRenderer=order_r,headerName="Order Now")
        gb.configure_grid_options(rowHeight=44,headerHeight=34,getRowStyle=row_style,
                                   suppressMovableColumns=True)
        gb.configure_selection("single",use_checkbox=False)
        gb.configure_default_column(resizable=True,sortable=True,filter=False)

        AgGrid(df_grid,gridOptions=gb.build(),height=340,allow_unsafe_jscode=True,
               update_mode=GridUpdateMode.SELECTION_CHANGED,theme="alpine",
               custom_css={".ag-root-wrapper":{"border":"1px solid #E2E8F0!important","border-radius":"14px!important","overflow":"hidden"},
                           ".ag-header":{"background":"#F8FAFE!important","border-bottom":"1px solid #E2E8F0!important"},
                           ".ag-row-even":{"background":"#FFFFFF!important"},".ag-row-odd":{"background":"#F8FAFE!important"},
                           ".ag-cell":{"border-right":"1px solid #F0F4F9!important"}})

    # ── RIGHT: Intelligence Feed (same height container) ─────────────────────
    with feed_col:
        st.markdown("<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:10px;'>Intelligence Feed</div>",unsafe_allow_html=True)
        feed_items=[]
        for _,row in summary[summary.risk=="CRITICAL"].iterrows():
            feed_items.append({"dot":"#EF4444","type":"crit","time":"Now",
                "msg":"<span>"+row["name"]+"</span> — "+str(round(row["days_cover"]))+"d cover · "+str(round(row["current_stock"]))+" units · order "+str(int(row.get("repl_quantity",0)))+" units"})
        for _,row in summary[summary.risk=="WARNING"].iterrows():
            feed_items.append({"dot":ORANGE,"type":"warn","time":"Live",
                "msg":"<span>"+row["name"]+"</span> — approaching safety stock threshold"})
        ss_gap=summary[(summary.safety_stock<summary.rec_safety_stock)&(summary.risk!="INSUFFICIENT_DATA")]
        for _,row in ss_gap.sort_values("breach_count",ascending=False).head(2).iterrows():
            g=round(row["rec_safety_stock"]-row["safety_stock"])
            if g>0:
                feed_items.append({"dot":"#F59E0B","type":"warn","time":"Audit",
                    "msg":"<span>SAP SS gap</span> — "+row["name"][:20]+" needs +"+str(g)+" units buffer"})
        top_b=summary[(summary.breach_count>0)&(summary.risk!="INSUFFICIENT_DATA")].sort_values("breach_count",ascending=False)
        if len(top_b)>0:
            r=top_b.iloc[0]
            feed_items.append({"dot":ORANGE,"type":"info","time":"History",
                "msg":"<span>"+r["name"]+"</span> — "+str(r["breach_count"])+" stockout events in 25 months"})
        rising=summary[(summary.trend=="Rising")&(summary.risk=="HEALTHY")]
        if len(rising)>0:
            feed_items.append({"dot":"#22C55E","type":"ok","time":"Trend",
                "msg":"<span>"+rising.iloc[0]["name"]+"</span> — stock recovering ↑"})
        feed_items.append({"dot":"#22C55E","type":"ok","time":"System",
            "msg":"<span>ARIA</span> — replenishment formula: max(gap-to-SS, lot-size). SS from Material Master."})

        tag_map={"crit":"ft-c","warn":"ft-w","ok":"ft-o","info":"ft-i"}
        tag_lbl={"crit":"Critical","warn":"Warning","ok":"Healthy","info":"Update"}
        items_html=""
        for i,item in enumerate(feed_items[:9]):
            line="" if i>=8 else "<div class='fi-line'></div>"
            items_html+=(
                "<div class='fi'><div class='fi-dc'><div class='fi-dot' style='background:"+item["dot"]+";'></div>"+line+"</div>"
                "<div style='flex:1;min-width:0;'>"
                "<div class='fi-msg'>"+item["msg"]+"</div>"
                "<div class='fi-time'>"+item["time"]+"</div>"
                "<span class='fi-tag "+tag_map[item["type"]]+"'>"+tag_lbl[item["type"]]+"</span>"
                "</div></div>")
        st.markdown(
            "<div class='fc' style='height:340px;overflow-y:auto;'>"
            "<div class='fh'><div class='fht'>System Activity</div>"
            "<div class='flv'><div class='dot dot-g'></div>Live</div></div>"
            +items_html+"</div>",unsafe_allow_html=True)

    # ── ANALYTICS SECTION ──────────────────────────────────────────────────────
    st.markdown("<div style='height:20px;'></div>",unsafe_allow_html=True)
    st.markdown("<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:14px;'>Supply Chain Analytics</div>",unsafe_allow_html=True)

    c1,c2=st.columns(2,gap="medium")

    with c1:
        # Chart 1: Stockout events by month — proper date labels
        st.markdown("<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:6px;'>Historical Stockout Events (by Month)</div>",unsafe_allow_html=True)
        all_breaches=[]
        for _,row in summary[summary.breach_count>0].iterrows():
            sh3=get_stock_history(data,row["material"]); ss=row["safety_stock"]
            if ss<=0: continue
            b=sh3[sh3["Gross Stock"]<ss]
            for _,br in b.iterrows():
                all_breaches.append({
                    "label": fmt_period(br["Fiscal Period"]),
                    "period": br["Fiscal Period"],
                    "material": row["name"][:16]
                })
        if all_breaches:
            df_br=pd.DataFrame(all_breaches)
            br_by_period=df_br.groupby(["period","label"]).size().reset_index(name="count")
            br_by_period=br_by_period.sort_values("period").tail(16)
            clrs=["#EF4444" if c>=2 else "#F59E0B" for c in br_by_period["count"]]
            fig1=go.Figure(go.Bar(
                x=br_by_period["label"],y=br_by_period["count"],
                marker_color=clrs,marker_line_width=0,
                text=br_by_period["count"].astype(str),
                textposition="outside",textfont=dict(size=9,color="#475569"),
                hovertemplate="<b>%{x}</b><br>Stockout events: %{y}<extra></extra>",
            ))
            ct(fig1,210); fig1.update_layout(showlegend=False,xaxis_tickangle=-40,
                                              yaxis=dict(gridcolor="#F0F4F9",dtick=1,title="Breaches"))
            st.plotly_chart(fig1,use_container_width=True)
            note("Red = multiple SKUs breached same month · Amber = single SKU breach · "
                 "Source: Inventory extract vs SAP Safety Stock (Material Master)")
        else:
            st.markdown("<div class='flag-box' style='height:210px;display:flex;align-items:center;justify-content:center;'>No breach events recorded</div>",unsafe_allow_html=True)

    with c2:
        # Chart 2: Replenishment Priority — replaces confusing Safety Stock Audit bar
        st.markdown("<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:6px;'>Replenishment Priority (Days of Cover)</div>",unsafe_allow_html=True)
        act2=summary[summary.risk.isin(["CRITICAL","WARNING","HEALTHY"])].sort_values("days_cover")
        fig2=go.Figure()
        clrs2=["#EF4444" if r=="CRITICAL" else "#F59E0B" if r=="WARNING" else "#22C55E" for r in act2["risk"]]
        cap=[min(float(v),200) for v in act2["days_cover"]]
        fig2.add_trace(go.Bar(
            y=act2["name"].str[:20].tolist(), x=cap,
            orientation="h",
            marker_color=clrs2,marker_opacity=0.85,marker_line_width=0,
            text=[("<30d ⛔" if v<30 else str(round(v))+"d") for v in cap],
            textposition="outside",textfont=dict(size=9,color="#475569"),
            hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
        ))
        fig2.add_vline(x=30,line_color="#EF4444",line_dash="dot",line_width=1.5,
                       annotation_text="30d min",annotation_font_color="#EF4444",annotation_font_size=9)
        ct(fig2,210); fig2.update_layout(showlegend=False,xaxis_title="Days",margin=dict(l=8,r=40,t=32,b=8))
        st.plotly_chart(fig2,use_container_width=True)
        note("Days of cover = current stock ÷ avg daily demand (from Sales file). "
             "Threshold: 30 days minimum before replenishment trigger.")

    # ── Product Drill-Down (filterable, meaningful for enterprise) ─────────────
    st.markdown("<div style='height:6px;'></div>",unsafe_allow_html=True)
    sec("Product Deep-Dive — Demand & Stock by SKU")
    note("Select a product to inspect its demand history and stock trajectory. "
         "Demand sourced from Sales file (includes write-offs and internal consumption — not netted). "
         "Stock from Inventory extract. SAP Safety Stock from Material Master.")

    prod_opts=[r["name"] for _,r in summary[summary.risk!="INSUFFICIENT_DATA"].iterrows()]
    sel_prod=st.selectbox("Select product",prod_opts,key="cc_prod")
    sel_mat_id=summary[summary.name==sel_prod]["material"].values[0]
    dh_cc=get_demand_history(data,sel_mat_id); sh_cc=get_stock_history(data,sel_mat_id)
    ss_cc=summary[summary.material==sel_mat_id]["safety_stock"].values[0]
    lt_cc=summary[summary.material==sel_mat_id]["lead_time"].values[0]
    lot_cc=summary[summary.material==sel_mat_id]["lot_size"].values[0]
    repl_cc=int(summary[summary.material==sel_mat_id]["repl_quantity"].values[0])

    if len(dh_cc)>0:
        # Format dates properly
        dh_cc["label"]=dh_cc["period_dt"].dt.strftime("%b '%y")
        sh_cc["label"]=sh_cc["period_dt"].dt.strftime("%b '%y")

        fig_dd=make_subplots(rows=1,cols=2,
            subplot_titles=("Monthly Demand — "+sel_prod[:25],
                            "Stock vs Safety Stock"),
            column_widths=[0.5,0.5])

        avg_d=float(dh_cc[dh_cc.demand>0]["demand"].mean()) if len(dh_cc[dh_cc.demand>0])>0 else 0
        clrs_dd=[("#EF4444" if v>avg_d*2 else ORANGE) for v in dh_cc["demand"]]
        fig_dd.add_trace(go.Bar(
            x=dh_cc["label"],y=dh_cc["demand"],marker_color=clrs_dd,
            marker_line_width=0,name="Demand",showlegend=False,
            hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>"),row=1,col=1)
        if avg_d>0:
            fig_dd.add_hline(y=avg_d,line_color="#94A3B8",line_dash="dot",line_width=1,
                             row=1,col=1,annotation_text="avg "+str(round(avg_d)),
                             annotation_font_color="#94A3B8",annotation_font_size=9)
        fig_dd.add_trace(go.Scatter(
            x=sh_cc["label"],y=sh_cc["Gross Stock"],mode="lines+markers",
            name="Stock",line=dict(color=ORANGE,width=2),marker=dict(size=4,color=ORANGE),
            fill="tozeroy",fillcolor="rgba(244,123,37,0.07)",showlegend=False,
            hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"),row=1,col=2)
        if ss_cc>0:
            fig_dd.add_hline(y=ss_cc,line_color="#EF4444",line_dash="dot",line_width=1.5,
                             row=1,col=2,annotation_text="SAP SS "+str(round(ss_cc)),
                             annotation_font_color="#EF4444",annotation_font_size=9)
        ct(fig_dd,240); fig_dd.update_layout(margin=dict(l=8,r=8,t=44,b=8),xaxis_tickangle=-40,xaxis2_tickangle=-40)
        st.plotly_chart(fig_dd,use_container_width=True)

        # Replenishment card below the chart
        if repl_cc>0:
            st.markdown(
                "<div style='background:var(--rbg);border:1px solid rgba(239,68,68,0.2);"
                "border-radius:var(--r);padding:12px 16px;display:flex;align-items:center;gap:16px;'>"
                "<div style='font-size:20px;'>⛔</div>"
                "<div style='flex:1;'>"
                "<div style='font-size:12px;font-weight:800;color:var(--red);'>Replenishment Required Now</div>"
                "<div style='font-size:11px;color:var(--t2);margin-top:3px;'>"
                "Current stock: "+str(round(summary[summary.material==sel_mat_id]["current_stock"].values[0]))+" units · "
                "SAP SS: "+str(round(ss_cc))+" units · "
                "Lead time: "+str(round(lt_cc))+"d (Material Master) · "
                "Lot size: "+str(round(lot_cc))+" units · "
                "</div></div>"
                "<div style='text-align:right;'>"
                "<div style='font-size:22px;font-weight:900;color:var(--red);'>"+str(repl_cc)+" units</div>"
                "<div style='font-size:9px;color:var(--red);'>max(gap="+str(int(max(0,ss_cc-summary[summary.material==sel_mat_id]['current_stock'].values[0])))
                +", lot="+str(round(lot_cc))+")</div>"
                "</div></div>",unsafe_allow_html=True)

    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong> — Enterprise AI &amp; Supply Chain Intelligence</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MATERIAL INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════
elif selected=="Material Intelligence":
    mat_opts={row["name"]:row["material"] for _,row in summary.iterrows()}
    sel_name=st.selectbox("Select Material",list(mat_opts.keys()),key="mi_mat")
    sel_mat=mat_opts[sel_name]; mat_row=summary[summary.material==sel_mat].iloc[0]; risk=mat_row["risk"]

    if risk=="INSUFFICIENT_DATA":
        reasons=[]
        if mat_row["nonzero_demand_months"]<3: reasons.append("Only "+str(mat_row["nonzero_demand_months"])+" months of demand data (min 6)")
        if mat_row["zero_periods"]>10: reasons.append("Zero stock in "+str(mat_row["zero_periods"])+"/"+str(mat_row["total_periods"])+" periods")
        if sel_mat=="3515-0010": reasons.append("Marked inactive in sales history")
        r_html="".join('<div style="font-size:11px;color:var(--t3);margin:3px 0;">• '+r+'</div>' for r in reasons)
        st.markdown(
            "<div style='display:flex;align-items:center;gap:12px;margin-bottom:18px;'>"
            "<div style='font-size:18px;font-weight:800;'>"+sel_name+"</div>"+sbadge(risk)+"</div>"
            "<div class='flag-box' style='max-width:540px;'>"
            "<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
            "<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:6px;'>Insufficient Data for ARIA Analysis</div>"
            "<div style='font-size:12px;color:var(--t3);margin-bottom:10px;'>Requires 6+ months of confirmed demand history.</div>"
            +r_html+"</div>",unsafe_allow_html=True); st.stop()

    h1c,h2c=st.columns([5,1])
    with h1c:
        st.markdown("<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
                    "<div style='font-size:19px;font-weight:900;'>"+sel_name+"</div>"
                    +sbadge(risk)+'<div class="chip">'+sel_mat+"</div></div>",unsafe_allow_html=True)
    with h2c:
        run_an=st.button("◈ Analyse",use_container_width=True)

    analysis=st.session_state.agent_cache.get(sel_mat)
    if run_an or (analysis is None and st.session_state.azure_client):
        if st.session_state.azure_client:
            with st.spinner("ARIA investigating…"):
                ctx=get_material_context(data,sel_mat,summary)
                analysis=analyse_material(st.session_state.azure_client,AZURE_DEPLOYMENT,ctx)
                st.session_state.agent_cache[sel_mat]=analysis
        else:
            st.markdown("<div style='padding:10px 14px;background:var(--ob);border:1px solid var(--obr);border-radius:9px;font-size:12px;color:var(--orange);'>Enter Azure API key in sidebar to enable AI analysis.</div>",unsafe_allow_html=True)

    if analysis:
        fh="".join('<div class="if_"><div class="id"></div><div>'+f+'</div></div>' for f in analysis.get("key_findings",[]))
        conf=str(analysis.get("data_confidence","MEDIUM")); cc="#22C55E" if "HIGH" in conf else "#F59E0B" if "MEDIUM" in conf else "#EF4444"
        st.markdown("<div class='ic'><div class='il'>◈ ARIA Intelligence</div><div class='ih'>"+analysis.get("headline","")+"</div><div class='ib'>"+analysis.get("executive_summary","")+"</div><div style='margin-top:12px;border-top:1px solid var(--bll);padding-top:10px;'><div style='font-size:9px;font-weight:700;letter-spacing:1px;color:var(--orange);text-transform:uppercase;margin-bottom:7px;'>Key Findings</div>"+fh+"</div><div style='margin-top:8px;font-size:10px;color:var(--t3);'>Confidence: <span style='color:"+cc+";font-weight:700;'>"+conf+"</span></div></div>",unsafe_allow_html=True)
        ca,cb=st.columns(2)
        with ca: st.markdown("<div class='sap-box'><div class='sap-lbl'>SAP Gap</div>"+analysis.get("sap_gap","")+"</div>",unsafe_allow_html=True)
        with cb: st.markdown("<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"+analysis.get("recommendation","")+"<div style='margin-top:5px;font-size:10px;opacity:0.75;'>If ignored: "+analysis.get("risk_if_ignored","")+"</div></div>",unsafe_allow_html=True)

    sec("Stock Trajectory · 25 Months")
    sh=get_stock_history(data,sel_mat); dh=get_demand_history(data,sel_mat)
    # Format dates properly
    sh["label"]=sh["period_dt"].dt.strftime("%b '%y")
    dh["label"]=dh["period_dt"].dt.strftime("%b '%y")
    ss_v=mat_row["safety_stock"]; rec=mat_row["rec_safety_stock"]
    fig=make_subplots(rows=2,cols=1,shared_xaxes=False,row_heights=[0.65,0.35],vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=sh["label"],y=sh["Gross Stock"],mode="lines+markers",name="Stock",
                              line=dict(color=ORANGE,width=2.5),marker=dict(size=4,color=ORANGE),
                              fill="tozeroy",fillcolor="rgba(244,123,37,0.07)",
                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"),row=1,col=1)
    if ss_v>0: fig.add_trace(go.Scatter(x=sh["label"],y=[ss_v]*len(sh),mode="lines",
                               name="SAP SS ("+str(round(ss_v))+")",line=dict(color="#EF4444",width=1.5,dash="dot")),row=1,col=1)
    if rec>ss_v: fig.add_trace(go.Scatter(x=sh["label"],y=[rec]*len(sh),mode="lines",
                               name="ARIA SS ("+str(round(rec))+")",line=dict(color="#22C55E",width=1.5,dash="dash")),row=1,col=1)
    if len(dh)>0:
        fig.add_trace(go.Bar(x=dh["label"],y=dh["demand"],name="Demand",
                             marker_color="rgba(244,123,37,0.2)",marker_line_width=0,
                             hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"),row=2,col=1)
        ad=float(dh[dh.demand>0]["demand"].mean()) if len(dh[dh.demand>0])>0 else 0
        if ad>0: fig.add_hline(y=ad,line_color="#94A3B8",line_dash="dot",line_width=1,row=2,col=1,
                               annotation_text="avg "+str(round(ad)),annotation_font_color="#94A3B8",annotation_font_size=9)
    ct(fig,380); fig.update_layout(yaxis_title="Units",yaxis2_title="Demand (units/mo)",
                                    xaxis=dict(tickangle=-30),xaxis2=dict(tickangle=-30))
    st.plotly_chart(fig,use_container_width=True)

    pc,sc2=st.columns(2)
    with pc:
        sec("Demand Patterns")
        nz=dh[dh.demand>0]; avg=float(nz.demand.mean()) if len(nz)>0 else 0
        cv=float(nz.demand.std()/avg*100) if avg>0 else 0
        cv_c="#EF4444" if cv>80 else "#F59E0B" if cv>40 else "#22C55E"
        spk=nz[nz.demand>avg*2] if avg>0 else pd.DataFrame()

        # Better: mini histogram instead of text stats
        fig_dp=go.Figure()
        fig_dp.add_trace(go.Bar(
            x=nz["label"] if "label" in nz.columns else nz["period"].apply(fmt_period),
            y=nz["demand"],
            marker_color=[("#EF4444" if v>avg*2 else ("#F59E0B" if v>avg*1.5 else ORANGE)) for v in nz["demand"]],
            marker_line_width=0,name="Demand",
            hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>",
        ))
        if avg>0: fig_dp.add_hline(y=avg,line_color="#94A3B8",line_dash="dot",line_width=1,
                                   annotation_text="avg",annotation_font_color="#94A3B8",annotation_font_size=9)
        if avg>0: fig_dp.add_hline(y=avg*2,line_color="#EF4444",line_dash="dot",line_width=1,
                                   annotation_text="spike",annotation_font_color="#EF4444",annotation_font_size=9)
        ct(fig_dp,180); fig_dp.update_layout(showlegend=False,xaxis_tickangle=-40,
                                             title=dict(text="Monthly Demand",font=dict(size=11,color="#475569"),x=0))
        st.plotly_chart(fig_dp,use_container_width=True)

        st.markdown(
            "<div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:4px;'>"
            "<div style='background:var(--s3);border-radius:8px;padding:8px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:var(--t);'>"+str(round(avg))+"</div>"
            "<div style='font-size:9px;color:var(--t3);'>Avg/mo</div></div>"
            "<div style='background:var(--s3);border-radius:8px;padding:8px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:"+cv_c+";'>"+str(round(cv))+"%</div>"
            "<div style='font-size:9px;color:var(--t3);'>Variability (CV)</div></div>"
            "<div style='background:var(--s3);border-radius:8px;padding:8px 10px;text-align:center;'>"
            "<div style='font-size:16px;font-weight:900;color:"+("#EF4444" if len(spk)>2 else "#1E293B")+";'>"+str(len(spk))+"</div>"
            "<div style='font-size:9px;color:var(--t3);'>Spikes (>2x)</div></div>"
            "</div>",unsafe_allow_html=True)

    with sc2:
        sec("Safety Stock Audit")
        gap=rec-ss_v; gp=(gap/ss_v*100) if ss_v>0 else 100
        if gap>10: gi,gc,gm="⚠","#F59E0B","Gap of "+str(round(gap))+" units ("+str(round(gp))+"%) — SAP SS insufficient."
        else:       gi,gc,gm="✓","#22C55E","SAP safety stock adequately configured."
        st.markdown(
            "<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
            "<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;'>"
            "<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS</div>"
            "<div style='font-size:22px;font-weight:900;color:var(--red);'>"+str(round(ss_v))+"</div>"
            "<div style='font-size:9px;color:var(--t3);'>Source: Material Master</div></div>"
            "<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA SS</div>"
            "<div style='font-size:22px;font-weight:900;color:var(--green);'>"+str(round(rec))+"</div>"
            "<div style='font-size:9px;color:var(--t3);'>95% service level</div></div></div>"
            "<div style='background:var(--s3);border-radius:8px;padding:9px 11px;font-size:11px;color:var(--t2);'>"
            "<span style='color:"+gc+";font-weight:700;'>"+gi+" </span>"+gm+"</div>"
            "</div>",unsafe_allow_html=True)
        note("ARIA formula: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
             "SAP Safety Stock sourced from Material Master (Current Inventory = 0 for all SKUs — known data quality issue). "
             "Lead time from Material Master: max(Planned Delivery Time, Inhouse Production Time).")

    bom=get_bom_components(data,sel_mat)
    if len(bom)>0:
        sec("BOM Components")
        lvl=bom[bom["Level"].str.contains("Level 03|Level 02|Level 1",na=False,regex=True)]
        if len(lvl)>0:
            sl=[(str(s)[:30] if pd.notna(s) else "⚠ Not specified") for s in lvl["Supplier Name(Vendor)"].tolist()]
            sc_c=["#94A3B8" if pd.notna(s) else "#F59E0B" for s in lvl["Supplier Name(Vendor)"].tolist()]
            fb=go.Figure(data=[go.Table(
                columnwidth=[80,200,60,60,155],
                header=dict(values=["<b>Material</b>","<b>Description</b>","<b>Qty</b>","<b>Unit</b>","<b>Supplier</b>"],
                            fill_color="#F0F4F9",font=dict(color="#475569",size=10,family="Inter"),
                            align="left",line_color="#E2E8F0",height=32),
                cells=dict(values=[lvl["Material"].tolist(),[str(d)[:34] for d in lvl["Material Description"].tolist()],
                                   [str(round(float(q),3)) for q in lvl["Comp. Qty (CUn)"].tolist()],
                                   lvl["Component unit"].tolist(),sl],
                           fill_color=[["#FFFFFF" if i%2==0 else "#F8FAFE" for i in range(len(lvl))]]*5,
                           font=dict(color=["#1E293B","#475569","#1E293B","#94A3B8",sc_c],size=10,family="Inter"),
                           align="left",line_color="#E2E8F0",height=30))])
            fb.update_layout(paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),
                             height=min(38+len(lvl)*32,360))
            st.plotly_chart(fb,use_container_width=True)
    st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# RISK RADAR — Complete Redesign
# ══════════════════════════════════════════════════════════════════════════════
elif selected=="Risk Radar":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:16px;'>"
        "Replenishment priority queue · Breach event timeline · Demand coverage analysis</div>",
        unsafe_allow_html=True)

    active_m=summary[summary.risk!="INSUFFICIENT_DATA"]

    # ── HERO: Replenishment Priority Queue ─────────────────────────────────────
    sec("Replenishment Priority Queue")
    note("Replenishment formula: max(gap to safety stock, fixed lot size). "
         "Safety Stock from Material Master. Lead time from Material Master.")

    alerts=active_m.sort_values("days_cover")
    for _,row in alerts.iterrows():
        risk=row["risk"]
        if risk not in ["CRITICAL","WARNING","HEALTHY"]: continue
        brd="#EF4444" if risk=="CRITICAL" else "#F59E0B" if risk=="WARNING" else "#E2E8F0"
        bgc="rgba(239,68,68,0.03)" if risk=="CRITICAL" else "rgba(245,158,11,0.02)" if risk=="WARNING" else "#FFFFFF"
        repl_qty=int(row.get("repl_quantity",0))
        lot=int(row["lot_size"]); gap_ss=int(row.get("gap_to_ss",0))
        days=round(row["days_cover"]); lt=round(row["lead_time"]); stock=round(row["current_stock"])
        ss=round(row["safety_stock"])

        action_html = ""
        if repl_qty > 0:
            parts = [
                "<div style='padding:8px 12px;background:#FEE2E2;",
                "border-radius:7px;margin-top:10px;'>",
                "<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:3px;'>",
                "IMMEDIATE ACTION REQUIRED</div>",
                "<div style='font-size:11px;color:#475569;'>",
                "Order <strong style='color:#EF4444;font-size:13px;'>" + str(repl_qty) + " units</strong> &nbsp;|&nbsp; ",
                "Lead time: <strong>" + str(lt) + "d</strong> (Material Master) &nbsp;|&nbsp; ",
                "Lot size: <strong>" + str(lot) + "</strong> &nbsp;|&nbsp; ",
                "Formula: max(gap=" + str(gap_ss) + ", lot=" + str(lot) + ") = " + str(repl_qty),
                "</div></div>",
            ]
            action_html = "".join(parts)
        else:
            parts = [
                "<div style='padding:6px 12px;background:#DCFCE7;",
                "border-radius:7px;margin-top:8px;font-size:10px;color:#14532d;'>",
                "&#10003; Stock above safety stock — no replenishment triggered (" + str(days) + "d cover remaining)",
                "</div>",
            ]
            action_html = "".join(parts)


        st.markdown(
            "<div class='sev-row' style='border-left:3px solid "+brd+";background:"+bgc+";'>"
            "<div style='min-width:120px;'>"+sbadge(risk)+"</div>"
            "<div style='flex:1;'>"
            "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:2px;'>"+row["name"]+"</div>"
            "<div style='font-size:10px;color:var(--t3);font-family:monospace;'>"+row["material"]+"</div>"
            "</div>"
            "<div style='display:grid;grid-template-columns:repeat(4,80px);gap:6px;text-align:center;'>"
            "<div style='background:var(--s3);border-radius:7px;padding:6px;'>"
            "<div style='font-size:13px;font-weight:900;color:"+("#EF4444" if stock<ss else "#1E293B")+";'>"+str(stock)+"</div>"
            "<div style='font-size:8px;color:var(--t3);'>Stock</div></div>"
            "<div style='background:var(--s3);border-radius:7px;padding:6px;'>"
            "<div style='font-size:13px;font-weight:900;color:#1E293B;'>"+str(ss)+"</div>"
            "<div style='font-size:8px;color:var(--t3);'>SAP SS</div></div>"
            "<div style='background:var(--s3);border-radius:7px;padding:6px;'>"
            "<div style='font-size:13px;font-weight:900;color:"+("#EF4444" if days<15 else "#F59E0B" if days<30 else "#22C55E")+";'>"+str(days)+"d</div>"
            "<div style='font-size:8px;color:var(--t3);'>Cover</div></div>"
            "<div style='background:var(--s3);border-radius:7px;padding:6px;'>"
            "<div style='font-size:13px;font-weight:900;color:#1E293B;'>"+str(lt)+"d</div>"
            "<div style='font-size:8px;color:var(--t3);'>Lead Time</div></div>"
            "</div></div>"
            + action_html,
            unsafe_allow_html=True)

    # ── Breach Event Timeline (Gantt-style) ────────────────────────────────────
    sec("Historical Breach Timeline")
    note("Each row shows when a material's stock dropped below its SAP safety stock threshold. "
         "Red = breach (stock < SS). Amber = warning zone (stock < SS × 1.5).")

    breach_events=[]
    for _,row in active_m.iterrows():
        sh_r=get_stock_history(data,row["material"]); ss=row["safety_stock"]
        if ss<=0: continue
        for _,sr in sh_r.iterrows():
            period_label=fmt_period(sr["Fiscal Period"])
            status_val=0
            if sr["Gross Stock"]<ss: status_val=2
            elif sr["Gross Stock"]<ss*1.5: status_val=1
            breach_events.append({"Material":row["name"][:22],"Period":period_label,
                                   "period_raw":sr["Fiscal Period"],"Status":status_val})

    if breach_events:
        df_be=pd.DataFrame(breach_events)
        pv=df_be.pivot_table(index="Material",columns="Period",values="Status",aggfunc="first").fillna(0)
        # Sort columns chronologically
        all_periods=df_be.drop_duplicates("period_raw").sort_values("period_raw")
        sorted_cols=[fmt_period(p) for p in all_periods["period_raw"].tolist()]
        sorted_cols=[c for c in sorted_cols if c in pv.columns]
        pv=pv[sorted_cols]

        fig_bt=go.Figure(data=go.Heatmap(
            z=pv.values,
            x=pv.columns.tolist(),
            y=pv.index.tolist(),
            colorscale=[[0,"#F8FAFE"],[0.49,"#F8FAFE"],[0.5,"rgba(245,158,11,0.35)"],[0.99,"rgba(245,158,11,0.35)"],[1,"rgba(239,68,68,0.55)"]],
            showscale=True,
            colorbar=dict(title="Severity",tickvals=[0,1,2],ticktext=["Safe","Warning","Breach"],
                          thickness=12,len=0.6,tickfont=dict(size=9)),
            hovertemplate="<b>%{y}</b><br>%{x}<br>Status: %{z:.0f}<extra></extra>",
            zmin=0,zmax=2,
        ))
        ct(fig_bt,240)
        fig_bt.update_layout(xaxis_tickangle=-40,margin=dict(l=10,r=80,t=20,b=60),
                             xaxis=dict(tickfont=dict(size=9)),
                             yaxis=dict(tickfont=dict(size=10)))
        st.plotly_chart(fig_bt,use_container_width=True)

    # ── Coverage Gap Analysis ──────────────────────────────────────────────────
    sec("Safety Stock Coverage Gap Analysis")
    fig_gap=go.Figure()
    gap_data=active_m.copy()
    gap_data["ss_gap"]=gap_data["rec_safety_stock"]-gap_data["safety_stock"]
    gap_data["gap_pct"]=gap_data.apply(lambda r: (r["ss_gap"]/r["safety_stock"]*100) if r["safety_stock"]>0 else 100,axis=1)
    gap_data=gap_data.sort_values("ss_gap",ascending=True)

    fig_gap.add_trace(go.Bar(
        y=gap_data["name"].str[:20],x=gap_data["safety_stock"],
        orientation="h",name="SAP Safety Stock",marker_color="rgba(239,68,68,0.5)",marker_line_width=0))
    fig_gap.add_trace(go.Bar(
        y=gap_data["name"].str[:20],x=gap_data["rec_safety_stock"],
        orientation="h",name="ARIA Recommended (95% SL)",marker_color="rgba(34,197,94,0.5)",marker_line_width=0))
    fig_gap.add_trace(go.Scatter(
        y=gap_data["name"].str[:20],x=gap_data["current_stock"],
        mode="markers",name="Current Stock",
        marker=dict(symbol="diamond",size=10,color=ORANGE,line=dict(width=1.5,color="white")),
        hovertemplate="<b>%{y}</b><br>Current stock: %{x} units<extra></extra>"))
    ct(fig_gap,240)
    fig_gap.update_layout(barmode="overlay",xaxis_title="Units",
                          legend=dict(font_size=9,y=1.1),margin=dict(l=10,r=40,t=32,b=8))
    st.plotly_chart(fig_gap,use_container_width=True)
    note("ARIA formula: 1.65 × σ_demand × √(lead_time/30). "
         "Diamond = current stock. Where diamond is left of red bar, replenishment is overdue.")
    st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO ENGINE — Demand Shock + Supply Disruption
# ══════════════════════════════════════════════════════════════════════════════
elif selected=="Scenario Engine":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Scenario Engine</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:16px;'>"
        "Demand shock simulation · Supply disruption analysis · Historical replay</div>",
        unsafe_allow_html=True)

    # Sub-tabs
    sim_tab, dis_tab, rep_tab = st.tabs(["📈  Demand Shock", "🔴  Supply Disruption", "↺  Historical Replay"])

    # ── TAB 1: DEMAND SHOCK ────────────────────────────────────────────────────
    with sim_tab:
        cc2,rc=st.columns([1,2])
        with cc2:
            sec("Simulation Controls")
            sim_opts={r["name"]:r["material"] for _,r in summary[summary.risk!="INSUFFICIENT_DATA"].iterrows()}
            sn=st.selectbox("Material",list(sim_opts.keys()),key="sm"); sid=sim_opts[sn]
            sr=summary[summary.material==sid].iloc[0]; ad=sr["avg_monthly_demand"]
            ss_sim=sr["safety_stock"]; lot_sim=sr["lot_size"]; lt_sim=sr["lead_time"]
            st.markdown(
                '<div class="chip" style="margin-bottom:8px;font-size:11px;">Stock: '+str(round(sr["current_stock"]))+
                ' · SS: '+str(round(ss_sim))+' · LT: '+str(round(lt_sim))+'d · Lot: '+str(round(lot_sim))+'</div>',
                unsafe_allow_html=True)
            ed=st.slider("Expected demand/month",int(ad*0.3),int(ad*3+50),int(ad),step=5)
            son=st.toggle("Add demand shock",False,key="son"); smo=smx=None
            if son: smo=st.slider("Shock month",1,6,2,key="smo"); smx=st.slider("Multiplier",1.5,5.0,2.5,step=0.5,key="smx")
            oon=st.toggle("Place order",False,key="oon"); oq=ot=None
            if oon:
                oq=st.slider("Order qty",50,2000,max(int(max(ss_sim-sr["current_stock"],lot_sim)),100),step=50)
                ot=st.slider("Arrives (days)",1,60,int(lt_sim))
            rsim=st.button("▶  Run Simulation",use_container_width=True)

        with rc:
            sec("6-Month Forward Projection")
            if rsim or st.session_state.get("sim_ran"):
                mos=6; stk=sr["current_stock"]; ss=ss_sim
                scns={"Low (−40%)":[ed*0.6]*mos,"Expected":[ed]*mos,"High (+60%)":[ed*1.6]*mos}
                if son and smo and smx:
                    for k in scns:
                        if k!="Low (−40%)": scns[k][smo-1]=ed*smx
                oa=int(ot/30) if oon and ot else None
                fs=go.Figure()
                scc_m={"Low (−40%)":"#22C55E","Expected":ORANGE,"High (+60%)":"#EF4444"}
                bi={}
                for sc_k,dems in scns.items():
                    proj=[]; s=stk
                    for m,d in enumerate(dems):
                        if oon and oq and m==oa: s+=oq
                        s=max(0.0,s-d); proj.append(s)
                    bi[sc_k]=next((m+1 for m,sp in enumerate(proj) if sp<max(ss,1)),None)
                    fs.add_trace(go.Scatter(x=list(range(1,mos+1)),y=proj,mode="lines+markers",name=sc_k,
                                            line=dict(color=scc_m[sc_k],width=2.5),marker=dict(size=5,color=scc_m[sc_k])))
                if ss>0: fs.add_hline(y=ss,line_color="#EF4444",line_dash="dot",line_width=1.5,
                                      annotation_text="SAP SS ("+str(round(ss))+")",annotation_font_color="#EF4444",annotation_font_size=9)
                ct(fs,280); fs.update_layout(xaxis=dict(tickvals=list(range(1,mos+1)),ticktext=["M"+str(i) for i in range(1,mos+1)]),yaxis_title="Projected Stock (units)")
                st.plotly_chart(fs,use_container_width=True); st.session_state["sim_ran"]=True
                vc=st.columns(3)
                for col,(sc_k,br) in zip(vc,bi.items()):
                    cl="#EF4444" if br else "#22C55E"; bg="var(--rbg)" if br else "var(--gbg)"
                    txt=("⛔ Breach M"+str(br)) if br else "✓ Safe 6mo"
                    with col: st.markdown("<div class='sc' style='padding:10px 12px;'><div style='font-size:9px;color:var(--t3);margin-bottom:3px;'>"+sc_k+"</div><div style='font-size:12px;font-weight:800;color:"+cl+";background:"+bg+";padding:4px 8px;border-radius:6px;'>"+txt+"</div></div>",unsafe_allow_html=True)

                # Replenishment note
                repl_sim=int(max(max(0,ss-stk),lot_sim)) if lot_sim>0 else int(max(0,ss-stk))
                note("Replenishment formula: max(gap_to_SS="+str(int(max(0,ss-stk)))+", lot_size="+str(int(lot_sim))+") = <strong>"+str(repl_sim)+" units</strong>. Lead time: "+str(round(lt_sim))+"d.")

                if st.session_state.azure_client and rsim:
                    with st.spinner("Agent evaluating…"):
                        sv=simulate_scenario(
                            st.session_state.azure_client,AZURE_DEPLOYMENT,sn,stk,ss,lt_sim,lot_sim,
                            {"low":ed*0.6,"expected":ed,"high":ed*1.6},
                            {"quantity":oq,"timing_days":ot} if oon else None)
                    urg=sv.get("urgency","MONITOR"); uc={"ACT TODAY":"#EF4444","ACT THIS WEEK":"#F59E0B","MONITOR":ORANGE,"SAFE":"#22C55E"}.get(urg,ORANGE)
                    st.markdown("<div class='ic' style='margin-top:12px;'><div class='il'>◈ ARIA Verdict</div><div style='display:flex;align-items:center;gap:8px;margin-bottom:7px;'><span style='font-size:12px;font-weight:800;color:"+uc+";'>"+urg+"</span><span class='chip'>Min order: "+str(sv.get("min_order_recommended","—"))+" units</span></div><div class='ib'>"+sv.get("simulation_verdict","")+"</div></div>",unsafe_allow_html=True)

    # ── TAB 2: SUPPLY DISRUPTION ────────────────────────────────────────────────
    with dis_tab:
        st.markdown(
            "<div style='padding:12px 0 8px;font-size:13px;color:var(--t2);'>"
            "Simulate a supply freeze across all materials. ARIA ranks which SKUs will breach "
            "safety stock first and recommends emergency actions.</div>",
            unsafe_allow_html=True)
        note("Parameters: Current Inventory, SAP Safety Stock (Material Master), "
             "Lead Time (Material Master), Fixed Lot Size (Material Master). "
             "Replenishment: max(gap_to_SS, lot_size).")

        dis_col, dis_res = st.columns([1,2])
        with dis_col:
            sec("Disruption Parameters")
            disruption_days=st.slider("Supply freeze duration (days)",7,90,30,step=7)
            affected_materials=st.multiselect(
                "Affected materials (leave blank for all)",
                [r["name"] for _,r in summary[summary.risk!="INSUFFICIENT_DATA"].iterrows()],
                default=[],key="dis_mats")
            run_dis=st.button("🔴  Run Disruption Simulation",use_container_width=True)

        with dis_res:
            sec("Impact Assessment — Ranked by Severity")
            if run_dis or st.session_state.get("dis_ran"):
                active_dis=summary[summary.risk!="INSUFFICIENT_DATA"]
                if affected_materials:
                    active_dis=active_dis[active_dis.name.isin(affected_materials)]

                sku_data=[]
                for _,row in active_dis.iterrows():
                    sku_data.append({
                        "material":row["material"],"name":row["name"],
                        "current_stock":row["current_stock"],"safety_stock":row["safety_stock"],
                        "lead_time":row["lead_time"],"fixed_lot_size":row["lot_size"],
                        "avg_monthly_demand":row["avg_monthly_demand"],"risk":row["risk"]
                    })

                results=simulate_multi_sku_disruption(None,None,disruption_days,sku_data)
                st.session_state["dis_ran"]=True

                for i,r in enumerate(results):
                    priority_n=i+1
                    bc=r["breach_occurs"]
                    brd="#EF4444" if bc else "#22C55E"; bgc="rgba(239,68,68,0.03)" if bc else "rgba(34,197,94,0.02)"
                    icon="⛔" if bc else "✓"
                    days_txt="Breaches Day "+str(r["days_to_breach"]) if bc and r["days_to_breach"] is not None else ("⚠ Already breached" if bc else "Safe for "+str(disruption_days)+"d freeze")
                    st.markdown(
                        "<div class='sev-row' style='border-left:3px solid "+brd+";background:"+bgc+";margin-bottom:8px;'>"
                        "<div style='min-width:28px;font-size:14px;font-weight:900;color:"+brd+";'>"+str(priority_n)+"</div>"
                        "<div style='min-width:24px;font-size:16px;'>"+icon+"</div>"
                        "<div style='flex:1;'>"
                        "<div style='font-size:12px;font-weight:800;color:var(--t);'>"+r["name"]+"</div>"
                        "<div style='font-size:10px;color:"+brd+";font-weight:600;margin-top:2px;'>"+days_txt+"</div>"
                        "</div>"
                        "<div style='display:grid;grid-template-columns:repeat(4,72px);gap:5px;text-align:center;'>"
                        "<div style='background:var(--s3);border-radius:6px;padding:5px;'>"
                        "<div style='font-size:12px;font-weight:900;color:var(--t);'>"+str(r["stock_at_end"])+"</div>"
                        "<div style='font-size:8px;color:var(--t3);'>End Stock</div></div>"
                        "<div style='background:var(--s3);border-radius:6px;padding:5px;'>"
                        "<div style='font-size:12px;font-weight:900;color:"+("#EF4444" if r["shortfall_units"]>0 else "#22C55E")+";'>"+str(r["shortfall_units"])+"</div>"
                        "<div style='font-size:8px;color:var(--t3);'>Shortfall</div></div>"
                        "<div style='background:var(--s3);border-radius:6px;padding:5px;'>"
                        "<div style='font-size:12px;font-weight:900;color:var(--t);'>"+str(r["lead_time"])+"d</div>"
                        "<div style='font-size:8px;color:var(--t3);'>Lead Time</div></div>"
                        "<div style='background:"+("var(--rbg)" if r["reorder_qty"]>0 else "var(--s3)")+";border-radius:6px;padding:5px;'>"
                        "<div style='font-size:12px;font-weight:900;color:"+("#EF4444" if r["reorder_qty"]>0 else "#94A3B8")+";'>"+str(r["reorder_qty"])+"</div>"
                        "<div style='font-size:8px;color:var(--t3);'>Order Now</div></div>"
                        "</div></div>",
                        unsafe_allow_html=True)

                # AI verdict for disruption
                if st.session_state.azure_client and run_dis:
                    breached=[r for r in results if r["breach_occurs"]]
                    if breached:
                        ctx_dis=("Supply disruption scenario: "+str(disruption_days)+"-day freeze. "
                                 "Breached materials: "+", ".join([r["name"] for r in breached])+". "
                                 "Worst case: "+breached[0]["name"]+" breaches on day "+str(breached[0]["days_to_breach"] or 0)+".")
                        with st.spinner("ARIA evaluating disruption…"):
                            dis_verdict=chat_with_data(st.session_state.azure_client,AZURE_DEPLOYMENT,
                                "Give a 2-sentence executive verdict on this supply disruption scenario. "
                                "What is the most critical action and why?",ctx_dis)
                        st.markdown("<div class='ic' style='margin-top:12px;'><div class='il'>◈ ARIA DISRUPTION VERDICT</div><div class='ib' style='margin-top:4px;'>"+dis_verdict+"</div></div>",unsafe_allow_html=True)

    # ── TAB 3: HISTORICAL REPLAY ────────────────────────────────────────────────
    with rep_tab:
        sec("Historical Replay — ARIA Signal Reconstruction")
        rp_mat_opts={r["name"]:r["material"] for _,r in summary[summary.risk!="INSUFFICIENT_DATA"].iterrows()}
        rp_sn=st.selectbox("Material",list(rp_mat_opts.keys()),key="rp_mat")
        rp_sid=rp_mat_opts[rp_sn]; rp_sr=summary[summary.material==rp_sid].iloc[0]
        shrp=get_stock_history(data,rp_sid)
        shrp["label"]=shrp["period_dt"].dt.strftime("%b '%y")
        pds=shrp["Fiscal Period"].tolist(); pds_lbl=shrp["label"].tolist()

        if len(pds)>4:
            rps=st.selectbox("Replay from period",pds_lbl[:-3],index=min(8,len(pds_lbl)-4),key="rps")
            if st.button("↺  Replay this period",key="rpb"):
                idx=pds_lbl.index(rps); rd=shrp.iloc[idx:idx+6]; ssr=rp_sr["safety_stock"]
                fr=go.Figure()
                fr.add_trace(go.Scatter(x=rd["label"],y=rd["Gross Stock"],mode="lines+markers",name="Actual Stock",
                                         line=dict(color=ORANGE,width=2.5),marker=dict(size=7,color=ORANGE),
                                         fill="tozeroy",fillcolor="rgba(244,123,37,0.07)",
                                         hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>"))
                if ssr>0: fr.add_hline(y=ssr,line_color="#EF4444",line_dash="dot",annotation_text="SAP SS "+str(round(ssr)))
                br2=rd[rd["Gross Stock"]<max(ssr,1)]
                if len(br2)>0:
                    bp=br2.iloc[0]["label"]; pv2=max(0,rd.index.tolist().index(br2.index[0])-1)
                    prev_lbl=rd.iloc[pv2]["label"] if pv2>=0 else bp
                    fr.add_vline(x=bp,line_color="#EF4444",line_dash="dash",annotation_text="⛔ Breach",annotation_font_color="#EF4444")
                    fr.add_vline(x=prev_lbl,line_color="#22C55E",line_dash="dash",annotation_text="◈ ARIA signal",annotation_font_color="#22C55E")
                ct(fr,260); st.plotly_chart(fr,use_container_width=True)
                msg="⛔ Breach detected. ARIA would have signalled an order one period earlier." if len(br2)>0 else "✓ No breach in this period."
                mc="#EF4444" if len(br2)>0 else "#22C55E"; mb="var(--rbg)" if len(br2)>0 else "var(--gbg)"
                st.markdown("<div style='font-size:11px;color:"+mc+";padding:7px 11px;background:"+mb+";border-radius:8px;'>"+msg+"</div>",unsafe_allow_html=True)
    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SUPPLY NETWORK — Complete Redesign
# ══════════════════════════════════════════════════════════════════════════════
elif selected=="Supply Network":
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:16px;'>"
        "BOM structure · Supplier intelligence · Risk cascade analysis</div>",
        unsafe_allow_html=True)

    snn=st.selectbox("Finished Good",[r["name"] for _,r in summary.iterrows()],key="snm")
    snid=summary[summary.name==snn]["material"].values[0]
    snr=summary[summary.material==snid].iloc[0]; bsn=get_bom_components(data,snid)

    if not len(bsn):
        st.markdown("<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div><div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",unsafe_allow_html=True)
    else:
        cw=int(bsn["Supplier Name(Vendor)"].notna().sum()); cn=int(bsn["Supplier Name(Vendor)"].isna().sum())
        us=int(bsn["Supplier Name(Vendor)"].dropna().nunique()); tc=len(bsn)

        # KPIs
        n1,n2,n3,n4=st.columns(4)
        for col,val,lbl,vc in [(n1,tc,"Total Components","#1E293B"),(n2,cw,"Suppliers Named","#22C55E"),
                               (n3,cn,"No Supplier Data","#F59E0B" if cn>0 else "#1E293B"),(n4,us,"Unique Suppliers","#1E293B")]:
            with col: st.markdown("<div class='sc'><div style='flex:1;'><div class='sv' style='color:"+vc+";'>"+str(val)+"</div><div class='sl'>"+lbl+"</div></div></div>",unsafe_allow_html=True)

        sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Component Detail", "⚠️  Risk Analysis"])

        with sn_tab:
            sec("BOM Risk Propagation Map")
            note("Orange nodes = component with named supplier. Amber = no supplier data (single-source risk). "
                 "Left node = finished good risk status. Hover for details.")
            # Build Sankey with better text visibility
            an=[snr["name"]]; rcs2={"CRITICAL":"#EF4444","WARNING":"#F59E0B","HEALTHY":"#22C55E"}
            nc=[rcs2.get(snr["risk"],"#94A3B8")]; src2,tgt,lv,lc=[],[],[],[]
            node_labels=[]
            for _,row in bsn.iterrows():
                desc=str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
                sup=str(row["Supplier Name(Vendor)"])[:20] if pd.notna(row["Supplier Name(Vendor)"]) else "No supplier"
                label=desc+"\n("+sup+")"
                if label not in an:
                    an.append(label)
                    nc.append("#3B82F6" if pd.notna(row["Supplier Name(Vendor)"]) else "#F59E0B")
                ni=an.index(label); qty=max(float(row["Comp. Qty (CUn)"]) if pd.notna(row["Comp. Qty (CUn)"]) else 1,0.1)
                src2.append(ni); tgt.append(0); lv.append(qty)
                lc.append("rgba(59,130,246,0.2)" if pd.notna(row["Supplier Name(Vendor)"]) else "rgba(245,158,11,0.2)")

            fsk=go.Figure(data=[go.Sankey(
                arrangement="snap",
                node=dict(pad=20,thickness=20,line=dict(color="#FFFFFF",width=1),
                          label=an,color=nc,
                          hovertemplate="<b>%{label}</b><extra></extra>"),
                link=dict(source=src2,target=tgt,value=lv,color=lc,
                          hovertemplate="%{source.label}<extra></extra>"),
            )])
            fsk.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", height=440,
                font=dict(family="Inter",size=12,color="#1E293B"),
                margin=dict(l=20,r=20,t=20,b=20))
            st.plotly_chart(fsk,use_container_width=True)

        with comp_tab:
            sec("Component Detail — All BOM Levels")
            # Rich component table
            comp_rows=[]
            for _,row in bsn.iterrows():
                sup=str(row["Supplier Name(Vendor)"]) if pd.notna(row["Supplier Name(Vendor)"]) else "⚠ Not specified"
                sup_contact=str(row["Supplier contact name(Vendor)"]) if pd.notna(row.get("Supplier contact name(Vendor)","")) else "—"
                sup_email=str(row["Supplier Email address(Vendor)"]) if pd.notna(row.get("Supplier Email address(Vendor)","")) else "—"
                proc=str(row["Procurement type"]) if pd.notna(row["Procurement type"]) else "—"
                proc_label="External" if proc=="E" else "In-house" if proc=="F" else proc
                comp_rows.append({
                    "Material":str(row["Material"]),
                    "Description":str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else "—",
                    "Level":str(row["Level"])[:30] if pd.notna(row["Level"]) else "—",
                    "Qty":str(round(float(row["Comp. Qty (CUn)"]),3)) if pd.notna(row["Comp. Qty (CUn)"]) else "—",
                    "Unit":str(row["Component unit"]) if pd.notna(row["Component unit"]) else "—",
                    "Supplier":sup,"Procurement":proc_label,
                    "Contact":sup_contact,
                })
            df_comp=pd.DataFrame(comp_rows)
            sup_r2=JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else{this.e.style.cssText='background:#DCFCE7;color:#22C55E;padding:2px 7px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
            gb2=GridOptionsBuilder.from_dataframe(df_comp)
            gb2.configure_column("Material",width=90); gb2.configure_column("Description",width=230)
            gb2.configure_column("Level",width=90); gb2.configure_column("Qty",width=65)
            gb2.configure_column("Unit",width=55); gb2.configure_column("Supplier",width=180,cellRenderer=sup_r2)
            gb2.configure_column("Procurement",width=100); gb2.configure_column("Contact",width=120)
            gb2.configure_grid_options(rowHeight=38,headerHeight=34)
            gb2.configure_default_column(resizable=True,sortable=True,filter=True)
            AgGrid(df_comp,gridOptions=gb2.build(),height=320,allow_unsafe_jscode=True,theme="alpine",
                   custom_css={".ag-root-wrapper":{"border":"1px solid #E2E8F0!important","border-radius":"12px!important"},
                               ".ag-header":{"background":"#F8FAFE!important"},".ag-row-even":{"background":"#FFFFFF!important"},
                               ".ag-row-odd":{"background":"#F8FAFE!important"}})

        with risk_tab:
            sec("Risk Cascade Analysis")

            # Risk score cards — visual and interesting
            risks=[]
            if snr["risk"] in ["CRITICAL","WARNING"]:
                severity=3 if snr["risk"]=="CRITICAL" else 2
                risks.append({"icon":"⛔","severity":severity,"color":"#EF4444","bg":"var(--rbg)",
                    "title":"Finished Good at Risk",
                    "detail":snr["name"]+" is "+snr["risk"].lower()+" with "+str(round(snr["days_cover"]))+"d of cover. "
                             "Current stock: "+str(round(snr["current_stock"]))+" vs SS: "+str(round(snr["safety_stock"]))+".",
                    "action":"Order "+str(int(snr.get("repl_quantity",0)))+" units immediately."})

            if cn>0:
                pct=round(cn/tc*100)
                risks.append({"icon":"⚠","severity":2,"color":"#F59E0B","bg":"var(--abg)",
                    "title":"Missing Supplier Data — "+str(cn)+" Components ("+str(pct)+"%)",
                    "detail":str(cn)+" of "+str(tc)+" components have no named supplier in BOM. "
                             "These cannot be assessed for single-source risk or lead time.",
                    "action":"Procurement team to verify and update BOM with supplier names."})

            if us<=2 and us>0:
                risks.append({"icon":"⚠","severity":2,"color":"#F59E0B","bg":"var(--abg)",
                    "title":"High Supplier Concentration — "+str(us)+" Unique Supplier(s)",
                    "detail":"Only "+str(us)+" unique supplier(s) cover all named components. "
                             "Any supplier disruption could cascade to multiple components simultaneously.",
                    "action":"Evaluate dual-source options for high-criticality components."})

            ext_comps=bsn[bsn["Procurement type"]=="E"]
            if len(ext_comps)>0:
                risks.append({"icon":"🌍","severity":1,"color":"#3B82F6","bg":"rgba(59,130,246,0.07)",
                    "title":"External Procurement Dependency — "+str(len(ext_comps))+" Components",
                    "detail":"External (E) components depend on supplier availability. "
                             "Lead time risk increases when multiple external components share a supplier.",
                    "action":"Review external component lead times — consider buffer stock for long lead items."})

            if not risks:
                st.markdown("<div style='display:flex;align-items:center;gap:8px;padding:12px 14px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);font-size:12px;color:#14532d;'><span class='dot dot-g'></span> No critical risk propagation identified for this finished good.</div>",unsafe_allow_html=True)
            else:
                for r in sorted(risks,key=lambda x:-x["severity"]):
                    st.markdown(
                        "<div style='background:"+r["bg"]+";border:1px solid "+r["color"]+"40;"
                        "border-left:4px solid "+r["color"]+";border-radius:var(--r);"
                        "padding:14px 16px;margin-bottom:10px;'>"
                        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                        "<span style='font-size:18px;'>"+r["icon"]+"</span>"
                        "<div style='font-size:13px;font-weight:800;color:"+r["color"]+";'>"+r["title"]+"</div>"
                        "</div>"
                        "<div style='font-size:12px;color:var(--t2);margin-bottom:6px;'>"+r["detail"]+"</div>"
                        "<div style='font-size:11px;color:"+r["color"]+";font-weight:600;'>"
                        "→ "+r["action"]+"</div></div>",
                        unsafe_allow_html=True)

            # ARIA Ask
            if st.session_state.azure_client:
                sec("Ask ARIA About This Supply Network")
                uq=st.text_input("Question",placeholder="e.g. Which supplier is the biggest single-source risk?",
                                 key="snq",label_visibility="collapsed")
                if uq and st.button("Ask ARIA",key="sna"):
                    ctx2=("Material: "+snr["name"]+", Risk: "+snr["risk"]+", Stock: "+str(round(snr["current_stock"]))+
                          ", Days cover: "+str(round(snr["days_cover"]))+", Components: "+str(tc)+
                          ", Named suppliers: "+str(cw)+", Missing supplier: "+str(cn)+
                          ", Unique suppliers: "+str(us)+", External components: "+str(len(ext_comps))+
                          ", Suppliers: "+", ".join(bsn["Supplier Name(Vendor)"].dropna().unique().tolist()[:5]))
                    with st.spinner("Thinking…"):
                        ans=chat_with_data(st.session_state.azure_client,AZURE_DEPLOYMENT,uq,ctx2)
                    st.markdown("<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA</div><div class='ib'>"+ans+"</div></div>",unsafe_allow_html=True)

        st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>',unsafe_allow_html=True)

st.markdown('</div>',unsafe_allow_html=True)
