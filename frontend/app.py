"""
app.py — Streamlit Executive Command Center Dashboard
=======================================================
Interactive dashboard that connects to the FastAPI backend and presents:

  Tab 1: Executive KPI Summary & Cold-Chain Breach Overview
  Tab 2: Inventory Expiry Risk Matrix (filterable)
  Tab 3: Automated Redistribution Planner

Run:  streamlit run frontend/app.py
"""

import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="DOH Cold-Chain Command Center",
    page_icon="PH",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# MINIMALIST LIGHT THEME CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp, .stMarkdown, p, h1, h2, h3, h4, h5, h6, 
    .stButton > button, .stSelectbox, .stMultiSelect, .stDataFrame, .stTable, .stMetric {
        font-family: 'Inter', sans-serif !important;
    }

    /* App Background - Clean Light */
    .stApp {
        background-color: #F8FAFC !important;
    }

    /* Clean Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown p, 
    section[data-testid="stSidebar"] .stMarkdown h2, 
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #334155 !important;
    }

    /* Minimalist Header Banner */
    .hero-banner {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 32px 40px;
        margin-bottom: 32px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 8px;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        font-weight: 400;
        color: #64748B;
        margin: 0;
    }

    /* Section Headers */
    .section-head {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1E293B;
        margin: 32px 0 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid #E2E8F0;
    }

    /* Metric Cards Override */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] {
        font-weight: 700 !important;
        color: #0F172A !important;
        font-size: 1.8rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-weight: 500 !important;
        color: #64748B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.75rem !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 12px !important;
        padding-bottom: 12px !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        color: #64748B !important;
    }
    .stTabs [aria-selected="true"] {
        color: #0F172A !important;
        border-bottom: 2px solid #2563EB !important;
    }

    /* Dataframes */
    .stDataFrame {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }

    /* Buttons */
    .stButton > button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        border: 1px solid #CBD5E1 !important;
        background-color: #FFFFFF !important;
        color: #334155 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: none !important;
    }

    /* Inputs */
    [data-baseweb="select"] > div, .stMultiSelect > div > div {
        border-radius: 6px !important;
        border-color: #CBD5E1 !important;
        background-color: #FFFFFF !important;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 500 !important;
        color: #334155 !important;
    }
    details {
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        background-color: #FFFFFF !important;
        margin-bottom: 8px;
    }
    
    .stMarkdown p, .stMarkdown li { color: #334155; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: #0F172A; }
</style>
""", unsafe_allow_html=True)


# ===========================================================================
# Plotly chart theme — minimalist light
# ===========================================================================
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#475569", family="Inter, sans-serif", size=12),
    margin=dict(t=50, b=30, l=30, r=20),
    xaxis=dict(
        gridcolor="#F1F5F9",
        zeroline=False,
        title_font=dict(family="Inter, sans-serif", weight=500, color="#1E293B"),
    ),
    yaxis=dict(
        gridcolor="#F1F5F9",
        zeroline=False,
        title_font=dict(family="Inter, sans-serif", weight=500, color="#1E293B"),
    ),
    legend=dict(
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="#E2E8F0",
        borderwidth=1,
        font=dict(size=11, family="Inter, sans-serif"),
    ),
    hoverlabel=dict(
        bgcolor="#1E293B",
        bordercolor="#1E293B",
        font=dict(family="Inter, sans-serif", size=12, color="#F8FAFC"),
    ),
)

RISK_COLORS = {
    "High Spoilage Risk": "#DC2626",
    "Near-Expiry Warning": "#D97706",
    "Optimal": "#059669",
    "Expired": "#991B1B",
}


# ===========================================================================
# API Helpers
# ===========================================================================
@st.cache_data(ttl=60)
def fetch_audit_report():
    try:
        resp = requests.get(f"{API_BASE}/api/v1/audit/full", timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def seed_database():
    try:
        resp = requests.post(f"{API_BASE}/api/v1/seed", timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Seed Error: {e}")
        return None


# ===========================================================================
# SIDEBAR
# ===========================================================================
with st.sidebar:
    st.markdown("""
    <div style="padding: 16px 0 24px;">
        <h2 style="font-weight: 700; font-size: 1.25rem; color: #0F172A; margin: 0 0 4px; letter-spacing: -0.5px;">
            Cold-Chain Engine
        </h2>
        <p style="font-size: 0.75rem; font-weight: 500; color: #64748B; text-transform: uppercase; letter-spacing: 1px; margin: 0;">
            Department of Health
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Seed / Reset Database", use_container_width=True, type="primary"):
        with st.spinner("Generating facility data..."):
            result = seed_database()
            if result:
                st.success("Database successfully seeded.")
                st.cache_data.clear()
            else:
                st.error("Failed to seed database.")

    if st.button("Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("""
    <div style="margin-top: 32px;">
        <p style="font-size: 0.85rem; font-weight: 600; color: #334155; margin-bottom: 8px;">
            About This Engine
        </p>
        <p style="font-size: 0.8rem; color: #64748B; line-height: 1.5;">
            Real-time visibility into the regional vaccine cold-chain network. Monitors integrity, predicts expiration leakage, and generates redistribution routes.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ===========================================================================
# HERO BANNER
# ===========================================================================
st.markdown("""
<div class="hero-banner">
    <h1 class="hero-title">Public Health Cold-Chain Command Center</h1>
    <p class="hero-subtitle">
        Vaccine Supply Monitoring &nbsp;&middot;&nbsp; Expiration Risk Analytics &nbsp;&middot;&nbsp; Automated Redistribution Intelligence
    </p>
</div>
""", unsafe_allow_html=True)


# ===========================================================================
# FETCH DATA
# ===========================================================================
report = fetch_audit_report()

if report is None:
    st.warning("Backend API Not Connected. Please start the FastAPI server.")
    st.stop()

kpi = report["kpi_summary"]
risk_profiles = report["risk_profiles"]
breaches = report["cold_chain_breaches"]
redistribution = report["redistribution_plan"]

if kpi["total_active_inventory_doses"] == 0:
    st.info("No inventory data found. Click Seed / Reset Database in the sidebar.")
    st.stop()


# ===========================================================================
# TABS
# ===========================================================================
tab1, tab2, tab3 = st.tabs([
    "Executive Dashboard",
    "Expiry Risk Matrix",
    "Redistribution Planner",
])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1 — Executive Dashboard
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    
    st.markdown('<div class="section-head">Key Performance Indicators</div>', unsafe_allow_html=True)
    
    # ── KPI Row 1 ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active Inventory Value", f"₱{kpi['total_active_inventory_value_usd']:,.0f}", f"{kpi['total_active_inventory_doses']:,} doses")
    c2.metric("Projected Leakage", f"₱{kpi['total_projected_leakage_usd']:,.0f}", f"{kpi['total_leakage_doses']:,} at risk doses", delta_color="inverse")
    c3.metric("Cold-Chain Breaches", f"{kpi['active_cold_chain_breaches']}", "Compromised batches", delta_color="inverse")
    c4.metric("Redistributions Needed", f"{kpi['redistribution_opportunities']}", f"{kpi['clinics_with_stockout_risk']} facilities at risk")

    # ── KPI Row 2 ──
    d1, d2, d3 = st.columns(3)
    d1.metric("High Spoilage Risk", f"{kpi['batches_at_high_risk']} batches", "Immediate action req.")
    d2.metric("Near-Expiry Warning", f"{kpi['batches_near_expiry_warning']} batches", "Within 30-day window")
    d3.metric("Optimal Batches", f"{kpi['batches_optimal']} batches", "Safe trajectory", delta_color="normal")

    # ── Charts Row ──
    st.markdown('<div class="section-head">Regional Leakage & Risk Breakdown</div>', unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        if risk_profiles:
            df_risk = pd.DataFrame(risk_profiles)
            region_leakage = df_risk.groupby("region")["financial_leakage_usd"].sum().reset_index()
            region_leakage = region_leakage.sort_values("financial_leakage_usd", ascending=True)

            fig_bar = go.Figure(data=[go.Bar(
                y=region_leakage["region"],
                x=region_leakage["financial_leakage_usd"],
                orientation="h",
                marker=dict(
                    color=region_leakage["financial_leakage_usd"],
                    colorscale=[[0, "#E2E8F0"], [0.5, "#94A3B8"], [1, "#475569"]],
                    line=dict(width=0),
                ),
                hovertemplate="<b>%{y}</b><br>Projected Leakage: ₱%{x:,.0f}<extra></extra>",
            )])
            fig_bar.update_layout(
                title=dict(text="Financial Leakage by Region", font=dict(size=14, color="#1E293B", family="Inter, sans-serif")),
                showlegend=False,
                coloraxis_showscale=False,
                height=380,
                **CHART_LAYOUT,
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    with col_chart2:
        risk_counts = {
            "High Spoilage Risk": kpi['batches_at_high_risk'],
            "Near-Expiry Warning": kpi['batches_near_expiry_warning'],
            "Optimal": kpi['batches_optimal'],
        }
        fig_donut = go.Figure(data=[go.Pie(
            labels=list(risk_counts.keys()),
            values=list(risk_counts.values()),
            hole=0.6,
            marker=dict(
                colors=["#DC2626", "#D97706", "#059669"],
                line=dict(color="#FFFFFF", width=2),
            ),
            textinfo="label+percent",
            textfont=dict(size=12, family="Inter, sans-serif", color="#475569"),
            hovertemplate="<b>%{label}</b><br>%{value} batches (%{percent})<extra></extra>",
        )])
        fig_donut.update_layout(
            title=dict(text="Risk Tier Distribution", font=dict(size=14, color="#1E293B", family="Inter, sans-serif")),
            showlegend=False,
            height=380,
            **{k: v for k, v in CHART_LAYOUT.items() if k not in ('xaxis', 'yaxis')},
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # ── Cold-Chain Breach Log ──
    if breaches:
        st.markdown('<div class="section-head">Cold-Chain Excursions Log</div>', unsafe_allow_html=True)
        df_breaches = pd.DataFrame(breaches)
        df_display = df_breaches[[
            "batch_code", "vaccine_name", "clinic_name",
            "breach_temperature", "breach_type", "recorded_at"
        ]].copy()
        df_display.columns = ["Batch Code", "Vaccine", "Facility", "Temp (°C)", "Excursion Type", "Recorded At"]
        df_display["Temp (°C)"] = df_display["Temp (°C)"].round(2)
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2 — Expiry Risk Matrix
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-head">Inventory Expiry Risk Analysis</div>', unsafe_allow_html=True)

    if risk_profiles:
        df_risk = pd.DataFrame(risk_profiles)

        filter_cols = st.columns(4)
        with filter_cols[0]:
            selected_risk = st.multiselect("Risk Tier", options=df_risk["risk_tier"].unique(), default=df_risk["risk_tier"].unique())
        with filter_cols[1]:
            selected_region = st.multiselect("Region", options=sorted(df_risk["region"].unique()), default=sorted(df_risk["region"].unique()))
        with filter_cols[2]:
            selected_vaccine = st.multiselect("Vaccine Type", options=sorted(df_risk["vaccine_name"].unique()), default=sorted(df_risk["vaccine_name"].unique()))
        with filter_cols[3]:
            dte_range = st.slider("Days to Expiry", int(df_risk["days_to_expiry"].min()), int(df_risk["days_to_expiry"].max()), (int(df_risk["days_to_expiry"].min()), int(df_risk["days_to_expiry"].max())))

        df_filtered = df_risk[
            (df_risk["risk_tier"].isin(selected_risk)) &
            (df_risk["region"].isin(selected_region)) &
            (df_risk["vaccine_name"].isin(selected_vaccine)) &
            (df_risk["days_to_expiry"].between(dte_range[0], dte_range[1]))
        ]

        st.markdown('<div class="section-head">Days-to-Expiry vs. Projected Leakage</div>', unsafe_allow_html=True)

        fig_scatter = px.scatter(
            df_filtered,
            x="days_to_expiry",
            y="financial_leakage_usd",
            color="risk_tier",
            size="quantity_doses",
            hover_data=["batch_code", "vaccine_name", "clinic_name"],
            color_discrete_map=RISK_COLORS,
            labels={"days_to_expiry": "Days to Expiry (DTE)", "financial_leakage_usd": "Projected Leakage (₱)", "risk_tier": "Risk Tier", "quantity_doses": "Remaining Doses"},
        )
        fig_scatter.update_layout(height=450, **CHART_LAYOUT)
        fig_scatter.update_traces(marker=dict(line=dict(width=1, color="#FFFFFF")), opacity=0.8)
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown('<div class="section-head">Detailed Risk Profiles</div>', unsafe_allow_html=True)
        df_table = df_filtered[[
            "batch_code", "vaccine_name", "clinic_name", "region",
            "quantity_doses", "days_to_expiry", "projected_waste_doses", "financial_leakage_usd", "risk_tier"
        ]].copy()
        df_table.columns = ["Batch", "Vaccine", "Facility", "Region", "Qty", "DTE", "Waste Risk", "Leakage (₱)", "Risk Tier"]
        df_table = df_table.sort_values("DTE", ascending=True)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    else:
        st.info("No risk profile data available.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3 — Redistribution Planner
# ═══════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-head">Automated Redistribution Directives</div>', unsafe_allow_html=True)

    if redistribution:
        df_redist = pd.DataFrame(redistribution)
        
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total Transfers", f"{len(df_redist):,}")
        r2.metric("Doses to Move", f"{df_redist['transfer_quantity'].sum():,.0f}")
        r3.metric("Value Restored", f"₱{df_redist['financial_value_usd'].sum():,.0f}")
        r4.metric("Critical Priority", f"{len(df_redist[df_redist['priority'] == 'Critical'])}")

        st.markdown('<div class="section-head">Transfer Schedule</div>', unsafe_allow_html=True)
        df_sched = df_redist[["priority", "source_clinic", "destination_clinic", "vaccine_name", "batch_code", "transfer_quantity", "days_to_expiry", "financial_value_usd"]].copy()
        df_sched.columns = ["Priority", "Origin", "Destination", "Vaccine", "Batch", "Qty", "DTE", "Value (₱)"]
        df_sched = df_sched.sort_values(["Priority", "DTE"], ascending=[True, True], key=lambda x: x.map({"Critical": 0, "High": 1, "Medium": 2}) if x.name == "Priority" else x)
        st.dataframe(df_sched, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-head">Transfer Rationales</div>', unsafe_allow_html=True)
        for _, row in df_redist.iterrows():
            with st.expander(f"{row['batch_code']} | {row['source_clinic']} -> {row['destination_clinic']} ({row['transfer_quantity']:,} doses)"):
                cols = st.columns(3)
                cols[0].markdown(f"**Vaccine:** {row['vaccine_name']}")
                cols[1].markdown(f"**DTE:** {row['days_to_expiry']} days")
                cols[2].markdown(f"**Value:** ₱{row['financial_value_usd']:,.2f}")
                st.markdown(f"**Rationale:** {row['rationale']}")
    else:
        st.success("Inventory is fully balanced. No redistributions required at this time.")
