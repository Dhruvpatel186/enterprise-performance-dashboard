import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import re
import hashlib

st.set_page_config(
    page_title="Enterprise Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ──────────────────────────────────────────────
#  DATA LOADING (cached so it runs only once)
# ──────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("project3_tech_advertising_campaigns_dataset.csv")

    # --- Convert date column ---
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["month"]      = df["start_date"].dt.month
    df["month_name"] = df["start_date"].dt.strftime("%b")
    df["year"]       = df["start_date"].dt.year

    # --- Drop low-value / redundant columns ---
    
    # campaign_id  → just a unique key, no analytical value
    # actual_cpc   → duplicate of CPC
    # creative_size → too granular, low signal
    # campaign_day  → already have start_date + quarter
    # ad_copy_length → low analytical value for this audience

    cols_to_drop = ["campaign_id", "actual_cpc", "creative_size",
                    "campaign_day", "ad_copy_length"]
    df.drop(columns=cols_to_drop, inplace=True, errors="ignore")

    # ---- feature engineering -----

    # Engagement Score = weighted mix of CTR, conversion_rate, quality_score
    df["engagement_score"] = (
        df["CTR"] * 0.4 +
        df["conversion_rate"] * 100 * 0.4 +
        df["quality_score"] * 0.2
    ).round(2)

    # Campaign Health: ROAS >= 3 → Good, 1-3 → Average, <1 → Poor
    df["campaign_health"] = pd.cut(
        df["ROAS"],
        bins=[-np.inf, 1, 3, np.inf],
        labels=["🔴 Poor", "🟡 Average", "🟢 Good"]
    )

    # Profit Margin %
    df["profit_margin_pct"] = (
        (df["profit"] / df["revenue"].replace(0, np.nan)) * 100
    ).round(2)

    # Cost Efficiency = Conversions per ₹ spent
    df["cost_efficiency"] = (
        df["conversions"] / df["ad_spend"].replace(0, np.nan)
    ).round(4)

    # Weekend flag
    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"])

    return df

# ──────────────────────────────────────────────
#  LOAD DATA
# ──────────────────────────────────────────────
df = load_data()

file = "users.csv"

# create csv file if not exists

if not os.path.exists(file):
    user_data = pd.DataFrame(columns=["First name", "Last name", "Email", "Phone", "Username", "Password"])
    user_data.to_csv(file, index=False)

# read csv
user_data = pd.read_csv(file)
# print(user_data)

# ------------------------------------------ session ---------------------------------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# query params
# restore data from query params

if "logged_in" in st.query_params:
    st.session_state.logged_in = True
    st.session_state.username = st.query_params.get("user", "")



def signup_page():
    st.markdown('<div class="form-title">📝 Create Account</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-sub">Join the analytics platform</div>', unsafe_allow_html=True)
    
    user_data = pd.read_csv(file)
    
    with st.form(key="signup form"):
        firstname = st.text_input("👤 First name", key=f"first_{st.session_state.get('form_version', 0)}")
        lastname = st.text_input("👥 Last name", key=f"lastt_{st.session_state.get('form_version', 0)}")
        email = st.text_input("📧 Email", key=f"emailt_{st.session_state.get('form_version', 0)}")
        phone = st.text_input("📱 Phone number", key=f"phonet_{st.session_state.get('form_version', 0)}")
        username = st.text_input("🔖 Username", key=f"usert_{st.session_state.get('form_version', 0)}")
        password = st.text_input("🔒 Password", type="password", key=f"past_{st.session_state.get('form_version', 0)}")
        re_password = st.text_input("🔑 Re enter Password", type="password", key=f"repasst_{st.session_state.get('form_version', 0)}")

        submit = st.form_submit_button("Register")

        # validations

        if submit:
            if not firstname or not lastname or not email or not phone or not username or not password or not re_password:
                st.error("All fields are mandatory")

            elif password != re_password:
                st.error("Password do not match")

            elif len(password) < 8:
                st.error("password must be at least 8 characters")

            elif not re.search(r"[A-Z]", password):
                st.error("At least one capital letter required")

            elif not re.search(r"[!@#$%^&*]", password):
                st.error("At least one special character required")

            elif not re.search(r"[0-9]", password):
                st.error("At least one digit required")

            elif not re.search(r"^\d{10}$", phone):
                st.error("Phone number must be 10 digits")

            # elif not re.search(r"^[a-zA-Z0-9._%+-]+@gmail\.com$", email):
                # st.error("Email must be a valid Gmail address (example@gmail.com)")

            # Sirf gmail nahi, koi bhi valid email accept karo
            
            elif not re.search(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                st.error("Enter a valid email address (example@gmail.com)")
            
            elif email in user_data["Email"].values:
                st.warning("You are already registered")

            elif username in user_data["Username"].values:
                st.warning("Username already exists")

            else:
                # store data into csv

                new_user = {
                    "First name": firstname,
                    "Last name": lastname,
                    "Email": email,
                    "Phone": phone,
                    "Username": username,
                    "Password": hash_password(password)
                }


                df = pd.concat([user_data, pd.DataFrame([new_user])], ignore_index=True)
                df.to_csv(file, index=False)

                # fields clear
                
                st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1
                st.session_state["signup_success"] = True
                st.rerun()

        # show success message
        
        if st.session_state.get("signup_success"):
            st.success("✅ Registration successful! Now login.")
            st.session_state.signup_success = False  # reset karo


def login_page():
    st.markdown('<div class="form-title">🔐 Welcome Back</div>', unsafe_allow_html=True)
    st.markdown('<div class="form-sub">Login to access your dashboard</div>', unsafe_allow_html=True)

    username = st.text_input("🔖 Username")
    password = st.text_input("🔒 Password", type="password")

    if st.button("Login"):
        user = user_data[(user_data["Username"] == username) & (user_data["Password"] == hash_password(password))]

        if not user.empty:
            st.success("✅ Login successful")

            # store data in session state

            st.session_state.logged_in = True
            st.session_state.username = username

            # query params

            st.query_params["logged_in"] = "true"
            st.query_params["user"] = username

            st.rerun()

        else:
            st.error("Invalid username and password")


def dashboard():
    # ── Section Selector ──
    with st.sidebar:
        st.sidebar.markdown(f"""
                            <div style="background:rgba(88,166,255,0.1); 
                            border:1px solid #58a6ff33;
                            border-radius:10px;
                            padding:10px;
                            text-align:center;
                            margin-bottom:10px;">
                            <span style="font-size:24px;">👨‍💼</span><br>
                            <span style="color:#58a6ff; font-weight:600;">
                            {st.session_state.username}</span><br>
                            <span style="color:#8b949e; font-size:12px;">Analytics User</span>
                            </div>
                            """, unsafe_allow_html=True)
        
        st.markdown("## 📊 Enterprise Insights Hub")
        st.markdown("---")
        selected = option_menu(
            "Insights Hub",
            options=["Overview & KPIs", "Platform Performance", "Audience Analysis", "Creative & Ad Format", "Budget & ROI", "Device & Technology Insights", "Trend & Time Analysis", "Advanced Insight Assistant", "Dataset Explorer", "Logout"],
            icons=["speedometer", "globe", "people", "palette", "currency-rupee", "cpu", "graph-up-arrow", "lightbulb", "table", "box-arrow-right"],
            menu_icon="bar-chart-line",
            default_index=0
        )

        st.markdown("---")
        st.markdown("### 🎛️ Filters")

        # Target audience filter
        all_target_audience = sorted(df["target_audience_gender"].unique())
        sel_audience =st.multiselect(
            "Gender", all_target_audience, default=all_target_audience, key="f_audience"
        )

        # Platform filter
        all_platforms = sorted(df["platform"].unique())
        sel_platform = st.multiselect(
            "Platform", all_platforms, default=all_platforms, key="f_platform"
        )
        
        # Industry filter
        all_industries = sorted(df["industry_vertical"].unique())
        sel_industry = st.multiselect(
            "Industry", all_industries, default=all_industries, key="f_industry"
        )
        
        # Budget Tier filter
        sel_budget = st.multiselect(
            "Budget Tier", ["High", "Medium", "Low"],
            default=["High", "Medium", "Low"], key="f_budget"
        )
        
        # Campaign Objective filter
        all_objectives = sorted(df["campaign_objective"].unique())
        sel_objective = st.multiselect(
            "Campaign Objective", all_objectives,
            default=all_objectives, key="f_objective"
        )
        
        # Quarter filter
        sel_quarter = st.multiselect(
            "Quarter", [1, 2, 3, 4], default=[1, 2, 3, 4], key="f_quarter"
        )
        
        st.markdown("---")
        st.caption("📁 Data: Tech Ad Campaigns Dataset")
        st.caption("🎓 College Project | External Review")
        
        filtered = df[
            df["target_audience_gender"].isin(sel_audience) &
            df["platform"].isin(sel_platform) &
            df["industry_vertical"].isin(sel_industry) &
            df["budget_tier"].isin(sel_budget) &
            df["campaign_objective"].isin(sel_objective) &
            df["quarter"].isin(sel_quarter)
        ].copy()


    def dark_layout(fig, title="", height=400):
        BG = "#161b22"; BORDER = "#30363d"
        TEXT = "#c9d1d9"; MUTED = "#8b949e"
        
        fig.update_layout(
            title=dict(text=f"<b>{title}</b>", font=dict(color=TEXT, size=15), x=0.01),
            paper_bgcolor=BG, plot_bgcolor=BG,
            font=dict(color=MUTED, size=11),
            height=height,
            margin=dict(l=50, r=30, t=55, b=50),
            legend=dict(
                bgcolor="rgba(22,27,34,0.85)", bordercolor=BORDER, borderwidth=1,
                font=dict(color=TEXT, size=11)
            ),
            
            hoverlabel=dict(bgcolor="#1f2937", bordercolor="#58a6ff", font=dict(color=TEXT, size=12)),
            xaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=MUTED)),
            yaxis=dict(gridcolor=BORDER, linecolor=BORDER, tickfont=dict(color=MUTED)),
        )

        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False)
        
        return fig


    def section_header(icon, title, subtitle=""):
        st.markdown(f"""
        <div class="section-header" 
                    style="background-color:#161b22;
                    padding:12px 16px;
                    border-radius:10px;
                    border:1px solid #30363d;">
            <h2 style="color:#58a6ff;margin:0;">{icon} &nbsp; {title}</h2>
            {'<p style="color:#c9d1d9;margin:4px 0 0;font-size:0.85rem;">' + subtitle + '</p>' if subtitle else ''}
        </div>
        """, unsafe_allow_html=True)


    if selected == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = ""

        # clear query params
        st.query_params.clear()

        st.success("Logged out successfully")
        st.rerun()        
            
    elif selected == "Overview & KPIs":
        section_header("🏠", "Overview & KPIs", "High-level campaign performance summary")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        # ── Top KPI Cards ──
        total_spend    = filtered["ad_spend"].sum()
        total_revenue  = filtered["revenue"].sum()
        total_profit   = filtered["profit"].sum()
        total_clicks   = filtered["clicks"].sum()
        total_conv     = filtered["conversions"].sum()
        avg_roas       = filtered["ROAS"].mean()
        avg_ctr        = filtered["CTR"].mean()
        avg_cpa        = filtered["CPA"].mean()
        conv_rate      = (total_conv / total_clicks) * 100 if total_clicks != 0 else 0
        total_imps     = filtered["impressions"].sum()
        total_profit   = filtered["profit"].sum()

        k1, k2, k3, k4, k5 = st.columns(5)

        k1.metric("💸 Total Ad Spend",   f"₹{total_spend:,.0f}",  f"Campaigns: {len(filtered):,}")
        k2.metric("💰 Total Revenue",    f"₹{total_revenue:,.0f}", f"Profit: ₹{total_profit:,.0f}")
        k3.metric("💵 Total Profit",     f"₹{total_profit:,.0f}",   f"ROAS: {avg_roas:.2f}x")
        k4.metric("📈 Avg ROAS",         f"{avg_roas:.2f}x",       "Return on Ad Spend")
        k5.metric("🖱️ Avg CTR",          f"{avg_ctr:.2f}%",        f"Conversions: {total_conv:,}")
        
        st.markdown("---")
        
        k6, k7, k8, k9, k10 = st.columns(5)
        
        k6.metric("👁️ Total Impressions",  f"{total_imps:,.0f}",  f"CTR: {avg_ctr:.2f}%")
        k7.metric("👆 Total Clicks",   f"{total_clicks:,}",  f"CTR: {avg_ctr:,.2f}%")
        k8.metric(
            "🎯 Total Conversions",   f"{total_conv:,}",    f"Conversion Rate: {conv_rate:.2f}%"
        )
        
        with k9:
            st.metric("💡 Avg CPA", f"₹{avg_cpa:,.2f}")
            st.caption("⬇️ Lower is better")

        k10.metric("✅ Good Campaigns",
              f"{(filtered['campaign_health'] == '🟢 Good').sum():,}",
              f"of {len(filtered):,} total")
        
        
        st.markdown("---")
        
        
        # ── Campaign Health Distribution (Donut) ──
        
        col1, col2 = st.columns(2)
        
        with col1:
            health_counts = filtered["campaign_health"].value_counts().reset_index()
            health_counts.columns = ["health", "count"]
            
            fig = px.pie(
                health_counts, names="health", values="count",
                hole=0.50, color="health",
                color_discrete_map={
                "🟢 Good": "#3fb950",
                "🟡 Average": "#d29922",
                "🔴 Poor": "#f85149"
            }
        )
            
            dark_layout(fig, "Campaign Health Distribution", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            
        with col2:
            # Spend vs Revenue by Objective
            
            obj_data = filtered.groupby("campaign_objective")[["ad_spend", "revenue"]].sum().reset_index()
            
            fig2 = go.Figure()
            fig2.add_bar(x=obj_data["campaign_objective"], y=obj_data["ad_spend"],
                         name="Ad Spend", marker_color="#d29922")
            fig2.add_bar(x=obj_data["campaign_objective"], y=obj_data["revenue"],
                         name="Revenue", marker_color="#3fb950")
            fig2.update_layout(barmode="group")
            
            dark_layout(fig2, "Spend vs Revenue by Campaign Objective", height=400)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")

        # campaign performance

        c_perf = filtered.sample(min(500, len(filtered)), random_state=42)
            
        fig3 = px.scatter(
            c_perf,
            x="CTR",
            y="conversion_rate",
            size="conversions",
            color="campaign_health",
            hover_data=["platform", "campaign_objective"],
        )
            
        dark_layout(fig3, "CTR vs Conversion Rate (Campaign Performance)", height=450)
        st.plotly_chart(fig3, use_container_width=True)
        

    elif selected == "Platform Performance":
        section_header("📱", "Platform Performance", "Compare ad platforms — ROI, CTR, Conversions")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)

        # ── Platform summary table ──
        plat_summary = filtered.groupby("platform").agg(
            Campaigns       = ("platform", "count"),
            Total_Spend     = ("ad_spend", "sum"),
            Total_Revenue   = ("revenue", "sum"),
            Avg_CTR         = ("CTR", "mean"),
            Avg_ROAS        = ("ROAS", "mean"),
            Total_Conversions = ("conversions", "sum"),
            Avg_CPA         = ("CPA", "mean"),
        ).reset_index()
        
        plat_summary["Avg_CTR"]  = plat_summary["Avg_CTR"].round(2)
        plat_summary["Avg_ROAS"] = plat_summary["Avg_ROAS"].round(2)
        plat_summary["Avg_CPA"]  = plat_summary["Avg_CPA"].round(2)
        plat_summary = plat_summary.sort_values("Avg_ROAS", ascending=False)
        
        st.dataframe(plat_summary.style.background_gradient(cmap="Blues", subset=["Avg_ROAS"]),use_container_width=True)
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # ROAS by Platform — Horizontal Bar
            fig = px.bar(
                plat_summary.sort_values("Avg_ROAS"),
                x="Avg_ROAS", y="platform", orientation="h",
                color="Avg_ROAS",
                color_continuous_scale="Blues",
                text="Avg_ROAS"
            )
            
            fig.update_traces(texttemplate="%{text:.2f}x", textposition="outside")
            dark_layout(fig, "Average ROAS by Platform", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            
        with col2:
            # CTR by Platform — Funnel chart
                
            fig2 = px.funnel(
                plat_summary.sort_values("Avg_CTR", ascending=False),
                x="Avg_CTR", y="platform",
                color_discrete_sequence=["#58a6ff"]
            )
                
            dark_layout(fig2, "Average CTR % by Platform", height=450)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")

        col3, col4 = st.columns(2)
        
        
        with col3:
            # Conversions distribution
             
            fig3 = px.bar(
                plat_summary.sort_values("Total_Conversions", ascending=False),
                x="platform", y="Total_Conversions",
                color="platform",
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            
            dark_layout(fig3, "Total Conversions by Platform", height=450)
            st.plotly_chart(fig3, use_container_width=True)
            
            
        with col4:
            # CPA comparison — lower is better
            
            fig4 = px.bar(
                plat_summary.sort_values("Avg_CPA"),
                x="platform", y="Avg_CPA",
                color="Avg_CPA",
                color_continuous_scale="RdYlGn_r",
                text="Avg_CPA"
            )
            
            fig4.update_traces(texttemplate="₹%{text:.0f}", textposition="outside")
            dark_layout(fig4, "Avg CPA by Platform (Lower = Better)", height=450)
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")
        
        # Platform + Age Group Treemap
        tree_data = filtered.groupby(
            ["platform", "target_audience_age"]).agg(
                Total_Revenue=("revenue", "sum"),
                Total_Clicks=("clicks", "sum"),
                Total_Conversions=("conversions", "sum")
        ).reset_index()
        
        fig = px.treemap(
            tree_data,
            path=["platform", "target_audience_age"],  # hierarchy
            values="Total_Revenue",  # size of box
            color="Total_Revenue",   # color intensity
            color_continuous_scale="Blues",
            title="Platform → Age Group Revenue Contribution",
            hover_data={
                "Total_Clicks": True,
                "Total_Conversions": True,
                "Total_Revenue": ":,.0f"
            })
        
        fig.update_layout(margin=dict(t=50, l=25, r=25, b=25))
        
        st.plotly_chart(fig, use_container_width=True)

    
    elif selected == "Audience Analysis":
        section_header("🎯", "Audience Analysis", "Age, Gender, Interest, Income & Retargeting insights")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        with col1:
            # CTR by Age Group
            
            age_data = filtered.groupby("target_audience_age").agg(
                Avg_CTR         = ("CTR", "mean"),
                Avg_ROAS        = ("ROAS", "mean"),
                Total_Conv      = ("conversions", "sum")
            ).reset_index()
            
            age_data["Avg_CTR"] = (age_data["Avg_CTR"]).round(2)
            
            fig = px.bar(
                age_data, x="target_audience_age", y="Avg_CTR",
                color="Avg_ROAS",
                color_continuous_scale=["#1e3a8a", "#2563eb", "#3b82f6", "#60a5fa", "#22c55e"],
                text="Avg_CTR"
            )
            
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            dark_layout(fig, "CTR by Target Age Group (Color = ROAS)", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Gender split — ROAS
            
            gender_data = filtered.groupby("target_audience_gender").agg(
                Avg_ROAS  = ("ROAS", "mean"),
                Avg_CTR   = ("CTR", "mean"),
                Total_Conv = ("conversions", "sum")
            ).reset_index()
            
            fig2 = px.pie(
                gender_data, names="target_audience_gender", values="Total_Conv",
                hole=0.5,
                color_discrete_sequence=["#3fb950", "#d29922", "#f85149"]
            )
            
            dark_layout(fig2, "Conversion Share by Gender", height=400)
            st.plotly_chart(fig2, use_container_width=True)
            
        st.markdown("---")

        col3, col4 = st.columns(2)
        
        with col3:
            # Income bracket vs ROAS
            
            inc_data = filtered.groupby("income_bracket")["ROAS"].mean().reset_index()
            inc_data.columns = ["income_bracket", "Avg_ROAS"]
            inc_data["Avg_ROAS"] = inc_data["Avg_ROAS"].round(2)
            
            fig3 = px.bar(
                inc_data.sort_values("Avg_ROAS", ascending=False),
                x="income_bracket", y="Avg_ROAS",
                color="Avg_ROAS",
                color_continuous_scale="Blues",
                text="Avg_ROAS"
            )
            
            fig3.update_traces(texttemplate="%{text:.2f}x", textposition="outside")
            dark_layout(fig3, "Avg ROAS by Income Bracket", height=450)
            st.plotly_chart(fig3, use_container_width=True)
            
            
        with col4:
            # Retargeting vs Non-retargeting
            
            ret_data = filtered.groupby("retargeting_flag").agg(
                Avg_CTR          = ("CTR", "mean"),
                Avg_conv_rate    = ("conversion_rate", "mean"),
                Avg_ROAS         = ("ROAS", "mean"),
            ).reset_index()
            
            ret_data["label"] = ret_data["retargeting_flag"].map(
                {True: "Retargeting ✅", False: "New Audience 🆕"}
            )
            
            ret_data["Avg_CTR"] = (ret_data["Avg_CTR"]).round(2)
            ret_data["Avg_conv_rate"] = (ret_data["Avg_conv_rate"]).round(2)
            
            fig4 = go.Figure()
            metrics = ["Avg_CTR", "Avg_conv_rate", "Avg_ROAS"]
            labels  = ["Avg CTR %", "Avg Conv Rate %", "Avg ROAS"]
            colors  = ["#58a6ff", "#3fb950"]
            
            
            for i, row in ret_data.iterrows():
                fig4.add_trace(go.Bar(
                    name=row["label"],
                    x=labels,
                    y=[row[m] for m in metrics],
                    marker_color=colors[i % 2]
                ))
                
                
            fig4.update_layout(barmode="group")
            dark_layout(fig4, "Retargeting vs New Audience Performance", height=450)
            st.plotly_chart(fig4, use_container_width=True)
            
        
        # Interest Category heatmap-style bar
        
        st.markdown("---")
        
        int_data = filtered.groupby("audience_interest_category").agg(
            Avg_ROAS  = ("ROAS", "mean"),
            Total_Conv = ("conversions", "sum"),
            Avg_CTR   = ("CTR", "mean")
        ).reset_index().sort_values("Avg_ROAS", ascending=False)
        
        fig5 = px.scatter(
            int_data,
            x="Avg_CTR", y="Avg_ROAS",
            size="Total_Conv",
            color="audience_interest_category",
            text="audience_interest_category",
            size_max=60
        )
        
        fig5.update_traces(textposition="top center")
        dark_layout(fig5, "Interest Category: CTR vs ROAS (Bubble Size = Conversions)", height=450)
        st.plotly_chart(fig5, use_container_width=True)


    elif selected == "Creative & Ad Format":
        section_header("🎨", "Creative & Ad Format Analysis", "Which formats, emotions, and placements drive results?")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        
        with col1:
            # Creative Format vs CTR
            
            fmt_data = filtered.groupby("creative_format").agg(
                Avg_CTR   = ("CTR", "mean"),
                Avg_ROAS  = ("ROAS", "mean"),
                Count     = ("creative_format", "count")
            ).reset_index()
            
            fmt_data["Avg_CTR"] = (fmt_data["Avg_CTR"]).round(2)
            fmt_data["Avg_ROAS"] = (fmt_data["Avg_ROAS"]).round(2)
            
            fig = px.bar(
                fmt_data.sort_values("Avg_CTR", ascending=False),
                x="creative_format", y="Avg_CTR",
                color="Avg_ROAS",
                color_continuous_scale=["#06b6d4", "#3b82f6", "#22c55e"],
                text="Avg_CTR"
            )
            
            fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            dark_layout(fig, "CTR by Creative Format (Color = ROAS)", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            
        with col2:
            # Creative Emotion vs conversion rate
            
            emo_data = filtered.groupby("creative_emotion").agg(
                Avg_Conv_Rate = ("conversion_rate", "mean"),
                Avg_ROAS      = ("ROAS", "mean")
            ).reset_index()
            
            
            emo_data["Avg_Conv_Rate"] = (emo_data["Avg_Conv_Rate"]).round(2)
            
            fig2 = px.bar(
                emo_data.sort_values("Avg_Conv_Rate", ascending=False),
                x="creative_emotion", 
                y="Avg_Conv_Rate",
                color="Avg_ROAS",
                color_continuous_scale=["#064e3b", "#10b981", "#a7f3d0"],
                text="Avg_Conv_Rate"
            )
            
            fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
            dark_layout(fig2, "Conversion Rate by Creative Emotion", height=450)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
                
        col3, col4 = st.columns(2)
        
        with col3:
            # Ad Placement performance
            
            place_data = filtered.groupby("ad_placement").agg(
                Avg_CTR  = ("CTR", "mean"),
                Avg_ROAS = ("ROAS", "mean"),
                Count    = ("ad_placement", "count")
            ).reset_index()
            
            place_data["Avg_CTR"] = (place_data["Avg_CTR"]).round(2)
            
            fig3 = px.scatter(
                place_data, x="Avg_CTR", y="Avg_ROAS",
                size="Count", color="ad_placement",
                text="ad_placement", size_max=50
            )
            
            fig3.update_traces(textposition="top center")
            dark_layout(fig3, "Ad Placement: CTR vs ROAS", height=450)
            st.plotly_chart(fig3, use_container_width=True)
            
        
        with col4:
            # CTA vs No CTA
            
            cta_data = filtered.groupby("has_call_to_action").agg(
                Avg_CTR       = ("CTR", "mean"),
                Avg_Conv_Rate = ("conversion_rate", "mean"),
                Avg_ROAS      = ("ROAS", "mean")
            ).reset_index()
            
            cta_data["label"] = cta_data["has_call_to_action"].map(
                {True: "Has CTA ✅", False: "No CTA ❌"}
            )
            
            cta_data["Avg_CTR"] = (cta_data["Avg_CTR"]).round(2)
            cta_data["Avg_Conv_Rate"] = (cta_data["Avg_Conv_Rate"]).round(2)
            
            
            fig4 = go.Figure()
            
            for i, row in cta_data.iterrows():
                fig4.add_trace(go.Bar(
                    name=row["label"],
                    x=["Avg CTR %", "Avg Conv Rate %", "Avg ROAS"],
                    y=[row["Avg_CTR"], row["Avg_Conv_Rate"], row["Avg_ROAS"]],
                    marker_color=["#3fb950", "#f85149"][i % 2]
                ))
                
            fig4.update_layout(barmode="group")
            dark_layout(fig4, "Call-to-Action Impact on Performance", height=450)
            st.plotly_chart(fig4, use_container_width=True)
            
            
        # Creative Age vs engagement
        
        st.markdown("---")
        age_bin = pd.cut(filtered["creative_age_days"], bins=[0, 15, 30, 60, 90],
                         labels=["0-15 days", "16-30 days", "31-60 days", "61-90 days"])
        
        age_perf = filtered.groupby(age_bin, observed=True).agg(
            Avg_CTR   = ("CTR", "mean"),
            Avg_ROAS  = ("ROAS", "mean"),
            Avg_Score = ("engagement_score", "mean")
        ).reset_index()
        
        age_perf.columns = ["creative_age_group", "Avg_CTR", "Avg_ROAS", "Avg_Engagement"]
        
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(
            x=age_perf["creative_age_group"], y=(age_perf["Avg_CTR"]).round(2),
            name="Avg CTR %", mode="lines+markers",
            marker=dict(size=9, color="#f85149"),
            line=dict(color="#f85149", width=2)
        ))
        
        fig5.add_trace(go.Scatter(
            x=age_perf["creative_age_group"], y=age_perf["Avg_ROAS"].round(2),
            name="Avg ROAS", mode="lines+markers",
            marker=dict(size=9, color="#3fb950"),
            line=dict(color="#3fb950", width=2)
        ))
        
        dark_layout(fig5, "Creative Age vs Performance (Does older creative fatigue?)", height=450)
        st.plotly_chart(fig5, use_container_width=True)

    elif selected == "Budget & ROI":
        section_header("💰", "Budget & ROI Analysis", "Spend efficiency, profit margins and ROAS deep-dive")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Budget Tier performance
            
            bud_data = filtered.groupby("budget_tier").agg(
                Avg_ROAS       = ("ROAS", "mean"),
                Total_Profit   = ("profit", "sum"),
                Avg_Margin     = ("profit_margin_pct", "mean"),
                Total_Spend    = ("ad_spend", "sum"),
                Total_Revenue  = ("revenue", "sum")
            ).reset_index()
            
            bud_data["Avg_ROAS"] = bud_data["Avg_ROAS"].round(2)
            
            fig = px.bar(
                bud_data,
                x="budget_tier",
                y=["Total_Spend", "Total_Revenue", "Total_Profit"],
                barmode="group",
                color_discrete_map={
                "Total_Spend": "#d29922",
                "Total_Revenue": "#3fb950",
                "Total_Profit": "#f85149"
                }
            )
            
            dark_layout(fig, "Spend / Revenue / Profit by Budget Tier", height=450)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # ROAS Distribution — Box plot
            
            fig2 = px.box(
                filtered, x="budget_tier", y="ROAS",
                color="budget_tier",
                color_discrete_sequence=["#388bfd", "#3fb950", "#d29922"]
            )
            
            fig2.update_layout(showlegend=False)
            dark_layout(fig2, "ROAS Distribution by Budget Tier", height=450)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
            
        col3, col4 = st.columns(2)
        
        with col3:
            # Industry Vertical — Profit comparison
            
            ind_data = filtered.groupby("industry_vertical").agg(
                Total_Profit   = ("profit", "sum"),
                Avg_ROAS       = ("ROAS", "mean"),
                Avg_Margin     = ("profit_margin_pct", "mean")
            ).reset_index().sort_values("Total_Profit", ascending=False)
            
            fig3 = px.bar(
                ind_data,
                x="industry_vertical", y="Total_Profit",
                color="Avg_ROAS",
                color_continuous_scale="Greens",
                text="Total_Profit"
            )
            
            fig3.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
            dark_layout(fig3, "Total Profit by Industry Vertical", height=400)
            st.plotly_chart(fig3, use_container_width=True)
            
        with col4:
            fig4 = px.scatter(
                ind_data,
                x="Avg_ROAS",
                y="Avg_Margin",
                size="Total_Profit",
                color="industry_vertical",
                text="industry_vertical"
            )
            
            fig4.update_traces(textposition="top center")
            
            dark_layout(fig4, "ROAS vs Profit Margin (Industry Level)", height=400)
            st.plotly_chart(fig4, use_container_width=True)

        st.markdown("---")

        # Cost Efficiency scatter — Ad Spend vs Revenue
        sample = filtered.sample(min(500, len(filtered)), random_state=42)
        fig4 = px.scatter(
            sample,
            x="ad_spend", y="revenue",
            color="platform",
            opacity=0.5,
            trendline="ols",
            size="revenue",
            hover_data=["campaign_objective", "ROAS"]
        )
        dark_layout(fig4, "Ad Spend vs Revenue (with trend line)", height=450)
        st.plotly_chart(fig4, use_container_width=True)
            
        # Profit Margin Heatmap — Platform × Industry
        
        st.markdown("---")
        pivot = filtered.pivot_table(
            values="profit_margin_pct",
            index="industry_vertical",
            columns="platform",
            aggfunc="mean"
        ).round(1)
        
        fig5 = px.imshow(
            pivot,
            text_auto=True,
            color_continuous_scale="RdYlGn",
            aspect="auto"
        )
        
        dark_layout(fig5, "Profit Margin % Heatmap — Industry × Platform", height=450)
        fig5.update_coloraxes(colorbar=dict(tickfont=dict(color="#c9d1d9")))
        st.plotly_chart(fig5, use_container_width=True)


    elif selected == "Device & Technology Insights":
        section_header("💻", "Device & Technology Insights", "Device type & OS performance analysis")
        
        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            #  Sunburst (Hierarchy View)
            
            sun_data = filtered.groupby(
                ["device_type", "operating_system"]).agg(
                    Revenue=("revenue", "sum")
            ).reset_index()
            
            fig1 = px.sunburst(
                sun_data,
                path=["device_type", "operating_system"],
                values="Revenue",
                color="Revenue",
                color_continuous_scale="Blues"
            )
            
            dark_layout(fig1, "Revenue Flow: Device → OS", height=450)
            st.plotly_chart(fig1, use_container_width=True)
            
        
        with col2:
            #  Box Plot (Distribution)
            
            fig2 = px.box(
                filtered,
                x="device_type",
                y="ROAS",
                color="device_type",
                color_discrete_sequence=["#3fb950", "#58a6ff", "#f85149"]
            )
            
            dark_layout(fig2, "ROAS Distribution by Device Type", height=450)
            st.plotly_chart(fig2, use_container_width=True)
            
        st.markdown("---")
    
        
        #  Bubble Chart (Relationship)
            
        bubble_data = filtered.groupby(
            ["device_type", "operating_system"]).agg(
                CTR=("CTR", "mean"),
                Conv_Rate=("conversion_rate", "mean"),
                Conversions=("conversions", "sum")
        ).reset_index()
            
        fig3 = px.scatter(
            bubble_data,
            x="CTR",
            y="Conv_Rate",
            size="Conversions",
            color="device_type",
            # symbol="operating_system",
            size_max=60
        )
            
        dark_layout(fig3, "CTR vs Conversion Rate", height=420)
        st.plotly_chart(fig3, use_container_width=True)
        
        
        st.markdown("---")
        
        #  4. Heatmap (Pattern)
        
        heat_data = filtered.pivot_table(
            values="CTR",
            index="operating_system",
            columns="device_type",
            aggfunc="mean"
        ).round(2)
        
        fig4 = px.imshow(
            heat_data,
            text_auto=True,
            color_continuous_scale="Blues",
            aspect="auto"
        )
        
        dark_layout(fig4, "CTR Heatmap (OS vs Device)", height=450)
        st.plotly_chart(fig4, use_container_width=True)
        
        st.markdown("---")
        
        #  5. Bar Chart (Simple Summary - ONLY ONE BAR)
        
        bar_data = filtered.groupby("device_type").agg(
            Total_Conversions=("conversions", "sum")
        ).reset_index()
        
        fig5 = px.bar(
            bar_data,
            x="device_type",
            y="Total_Conversions",
            color="device_type",
            text="Total_Conversions",
            color_discrete_sequence=["#58a6ff", "#3fb950", "#f85149"]
        )
        
        fig5.update_traces(textposition="outside")
        dark_layout(fig5, "Total Conversions by Device Type", height=450)
        st.plotly_chart(fig5, use_container_width=True)

    
    elif selected == "Trend & Time Analysis":
        section_header("📈", "Trend & Time Analysis", "Monthly trends, day-of-week patterns & peak hours")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Monthly Revenue & Spend trend
            
            monthly = filtered.groupby("month_name").agg(
                Total_Spend   = ("ad_spend", "sum"),
                Total_Revenue = ("revenue", "sum"),
                Avg_ROAS      = ("ROAS", "mean")
            ).reset_index()
            
            # Sort by month number
            
            month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun","Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            monthly["month_order"] = monthly["month_name"].apply(
                lambda x: month_order.index(x) if x in month_order else 99
            )
            
            monthly = monthly.sort_values("month_order")
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=monthly["month_name"], y=monthly["Total_Spend"],
                name="Ad Spend", fill="tozeroy",
                line=dict(color="#388bfd", width=2),
                fillcolor="rgba(56,139,253,0.15)"
            ))
            
            fig.add_trace(go.Scatter(
                x=monthly["month_name"], y=monthly["Total_Revenue"],
                name="Revenue", fill="tozeroy",
                line=dict(color="#3fb950", width=2),
                fillcolor="rgba(63,185,80,0.15)"
            ))
            
            dark_layout(fig, "Monthly Ad Spend vs Revenue", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            # Quarterly ROAS trend
            
            qtr_data = filtered.groupby(["quarter", "campaign_objective"]).agg(
                Avg_ROAS = ("ROAS", "mean")
            ).reset_index()
            
            qtr_data["Avg_ROAS"] = qtr_data["Avg_ROAS"].round(2)
            qtr_data["Quarter"]  = "Q" + qtr_data["quarter"].astype(str)
            
            fig2 = px.line(
                qtr_data,
                x="Quarter", y="Avg_ROAS",
                color="campaign_objective",
                markers=True,
                line_shape="spline"
            )
            
            dark_layout(fig2, "Quarterly ROAS by Campaign Objective", height=450)
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("---")
            
        col3, col4 = st.columns(2)
        
        with col3:
            # Day of Week performance
            dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday","Friday", "Saturday", "Sunday"]
            
            dow_data = filtered.groupby("day_of_week").agg(
                Avg_CTR   = ("CTR", "mean"),
                Avg_ROAS  = ("ROAS", "mean"),
                Total_Conv = ("conversions", "sum")
            ).reset_index()
            
            
            dow_data["Avg_CTR"] = (dow_data["Avg_CTR"]).round(2)
            dow_data["day_order"] = dow_data["day_of_week"].apply(
                lambda x: dow_order.index(x) if x in dow_order else 9
            )
            
            dow_data = dow_data.sort_values("day_order")
            
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=dow_data["day_of_week"], y=dow_data["Avg_CTR"],
                name="Avg CTR %", marker_color="#6d28d9"
            ))
            
            fig3.add_trace(go.Scatter(
                x=dow_data["day_of_week"], y=dow_data["Avg_ROAS"],
                name="Avg ROAS", yaxis="y2",
                mode="lines+markers",
                marker=dict(color="#3fb950", size=8),
                line=dict(color="#3fb950", width=2)
            ))
            
            fig3.update_layout(
                yaxis2=dict(
                    overlaying="y", side="right",
                    gridcolor="#21262d", linecolor="#30363d",
                    tickfont=dict(color="#8b949e")
                )
            )
            
            dark_layout(fig3, "Day-of-Week: CTR & ROAS", height=450)
            st.plotly_chart(fig3, use_container_width=True)

        # Weekend vs Weekday
            
        with col4:
            wk_data = filtered.groupby("is_weekend").agg(
                Avg_CTR       = ("CTR", "mean"),
                Avg_ROAS      = ("ROAS", "mean"),
                Avg_Conv_Rate = ("conversion_rate", "mean"),
                Total_Conv    = ("conversions", "sum"),
                Total_Spend   = ("ad_spend", "sum")
            ).reset_index()
            
            
            wk_data["label"]         = wk_data["is_weekend"].map({True: "Weekend 🏖️", False: "Weekday 💼"})
            wk_data["Avg_CTR"]       = (wk_data["Avg_CTR"]).round(2)
            wk_data["Avg_Conv_Rate"] = (wk_data["Avg_Conv_Rate"]).round(2)
            wk_data["Avg_ROAS"]      = wk_data["Avg_ROAS"].round(2)
            
            fig4 = go.Figure()
            metrics = ["Avg_CTR", "Avg_Conv_Rate", "Avg_ROAS"]
            labels  = ["CTR %", "Conv Rate %", "ROAS"]
            
            for i, row in wk_data.iterrows():
                fig4.add_trace(go.Bar(
                    name=row["label"],
                    x=labels,
                    y=[row[m] for m in metrics],
                    marker_color=["#f85149", "#3fb950"][i % 2]
                ))
                
                
            fig4.update_layout(barmode="group")
            dark_layout(fig4, "Weekend vs Weekday Performance", height=450)
            st.plotly_chart(fig4, use_container_width=True)
            
        st.markdown("---")
        
        # Hour of Day heatmap — CTR
            
        hour_plat = filtered.groupby(["hour_of_day", "platform"])["CTR"].mean().reset_index()
        hour_pivot = hour_plat.pivot(
            index="platform", columns="hour_of_day", values="CTR"
        ).round(4)
            
        fig5 = px.imshow(
            hour_pivot,
            text_auto=".1f",
            color_continuous_scale="Blues",
            aspect="auto"
        )
        
        fig5.update_traces(
            hovertemplate="Platform: %{y}<br>" + 
            "Hour of day: %{x}<br>" + 
            "CTR: %{z:.2f}%<extra></extra>"
        )

        dark_layout(fig5, "Hour-of-Day CTR Heatmap by Platform", height=450)
        st.plotly_chart(fig5, use_container_width=True)
        
    
    elif selected == "Advanced Insight Assistant":
        
        section_header("🧠", "Advanced Insight Assistant", "Missed insights + hidden opportunities")

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        query = st.selectbox("Choose a Strategic Question:", [
            
            # 🔍 MISSED INSIGHTS (USED DATA)
            "Which platform is profitable but underutilized?",
            "High CTR but low conversion — where is the problem?",
            "Which campaigns look successful but are actually inefficient?",
            "Where are we overspending without proportional returns?",
            "Which audience segment is most valuable overall?",
            
            # 🧠 DEEP ANALYSIS
            
            "Do high engagement campaigns actually generate revenue?",
            "Which device-platform combo is secretly outperforming?",
            "Are we targeting the right users at the right time?",
            
            # 💎 HIDDEN (UNUSED / UNDERUSED)
            
            "Does user behavior (session + pages) impact conversions?",
            "Does purchase intent really drive revenue?"
        ])
        
        if query:
            
            # 1️⃣ Underutilized profitable platform
            
            if query == "Which platform is profitable but underutilized?":
                res = filtered.groupby("platform").agg(
                    ROAS=("ROAS", "mean"),
                    Spend=("ad_spend", "sum")
                ).reset_index()
                
                fig = px.bar(res, x="platform", y=["ROAS", "Spend"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("💡 High ROAS but low spend = scaling opportunity")
                
                
            # 2️⃣ High CTR but low conversion
            elif query == "High CTR but low conversion — where is the problem?":
                filtered["conv_rate"] = filtered["conversions"] / filtered["clicks"]
                
                
                res = filtered.groupby("platform").agg(
                    CTR=("CTR", "mean"),
                    Conv_Rate=("conv_rate", "mean")
                ).reset_index()
                
                
                fig = px.bar(res, x="platform", y=["CTR", "Conv_Rate"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)
                
                st.warning("⚠️ High CTR + low conversion = landing page or targeting issue")
                
            # 3️⃣ Fake success campaigns
            
            elif query == "Which campaigns look successful but are actually inefficient?":
                res = filtered.groupby("campaign_objective").agg(
                    CTR=("CTR", "mean"),
                    ROAS=("ROAS", "mean")
                ).reset_index()
                
                fig = px.bar(res, x="campaign_objective", y=["CTR", "ROAS"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)
                
                st.warning("⚠️ High CTR doesn’t always mean high returns")
                
            # 4️⃣ Overspending
            
            elif query == "Where are we overspending without proportional returns?":
                res = filtered.groupby("platform").agg(
                    Spend=("ad_spend", "sum"),
                    Revenue=("revenue", "sum")
                ).reset_index()
                
                
                fig = px.bar(res, x="platform", y=["Spend", "Revenue"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)
                
                st.error("⚠️ Spend > Revenue gap = optimization needed")
                
            # 5️⃣ Most valuable audience
            elif query == "Which audience segment is most valuable overall?":
                res = filtered.groupby("target_audience_age").agg(
                    Revenue=("revenue", "sum"),
                    Conversions=("conversions", "sum")
                ).reset_index()
                
                fig = px.bar(res, x="target_audience_age", y=["Revenue", "Conversions"], barmode="group")
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("🎯 Focus on segments with both high revenue & conversions")
                
            # 6️⃣ Engagement vs Revenue
            
            elif query == "Do high engagement campaigns actually generate revenue?":
                
                temp = filtered.copy()  # 🔥 IMPORTANT
                
                temp["engagement_bucket"] = pd.cut(
                    temp["engagement_score"],
                    bins=4,
                    labels=["Low", "Medium", "High", "Very High"]
                )
                
                res = temp.groupby("engagement_bucket")["revenue"].mean().reset_index()
                
                fig = px.bar(res, x="engagement_bucket", y="revenue",
                             title="Engagement vs Revenue")
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("💡 High engagement doesn’t always mean high revenue → optimize conversion funnel")
                
            # 7️⃣ Device + Platform combo
            
            elif query == "Which device-platform combo is secretly outperforming?":
                res = filtered.groupby(["platform", "device_type"])["ROAS"].mean().reset_index()
                
                fig = px.bar(res, x="platform", y="ROAS", color="device_type")
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("📱 Hidden winners exist → scale these combos")
                
                
            # 8️⃣ Right time targeting
            
            elif query == "Are we targeting the right users at the right time?":
                res = filtered.groupby("hour_of_day").agg(
                    CTR=("CTR", "mean"),
                    Conv=("conversions", "sum")
                ).reset_index()
                
                fig = px.bar(res, x="hour_of_day", y="Conv")
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("⏰ Focus on high conversion hours")
                
                
            # 9️⃣ User behavior impact (UNUSED GOLD)
            
            elif query == "Does user behavior (session + pages) impact conversions?":
                temp = filtered.copy()  # 🔥 IMPORTANT
                
                temp["behavior_score"] = (
                    temp["pages_per_session"] + temp["avg_session_duration_seconds"] / 60
                )
                
                temp["behavior_bucket"] = pd.cut(
                    temp["behavior_score"],
                    bins=4,
                    labels=["Low", "Medium", "High", "Very High"]
                )
                
                res = temp.groupby("behavior_bucket")["conversions"].mean().reset_index()
                
                fig = px.bar(res, x="behavior_bucket", y="conversions", 
                             title="User Behavior Impact on Conversions")
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("🧠 More engaged users (more pages + time) convert better")
                
            # 🔟 Purchase intent
            
            elif query == "Does purchase intent really drive revenue?":
                res = filtered.groupby("purchase_intent_score")["revenue"].mean().reset_index()
                
                fig = px.line(res, x="purchase_intent_score", y="revenue", markers=True)
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.success("💰 Higher intent = higher revenue → target smarter")


    elif selected == "Dataset Explorer":
        section_header("🧾", "Dataset Explorer", "Explore raw & filtered dataset dynamically")
        
        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        # ── Row Selector Slider ──
        max_rows = min(len(filtered), 5000)
        
        rows_to_show = st.slider(
            "Select number of rows to display",
            min_value=10,
            max_value=max_rows,
            value=min(20, max_rows),
            step=10
        )
        
        st.caption(f"Showing {rows_to_show} rows out of {len(filtered):,} filtered records")
        st.markdown("---")
        
        # ── Column Selector ---
        
        selected_columns = st.multiselect(
            "Select columns to display (optional)",
            options=filtered.columns.tolist(),
            default=filtered.columns.tolist()
        )
        
        display_df = filtered[selected_columns].head(rows_to_show)

        st.markdown("<div style='margin-top:15px'></div>", unsafe_allow_html=True)
        
        # ── Data Table ──
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500
        )
        
        # st.markdown("---")
        
        # ── Download Button ──
        
        csv = display_df.to_csv(index=False).encode("utf-8")
        
        st.download_button(
            label="⬇️ Download Data as CSV",
            data=csv,
            file_name="filtered_data.csv",
            mime="text/csv"
        )
    
    st.markdown("""
                <div style="text-align:center; padding:12px 0; border-top:1px solid #30363d; color:#8b949e; font-size:0.85rem;">
                <b style="color:#58a6ff;">Enterprise Performance Dashboard</b><br>
                
                📊 Data Analytics Project | Built using Streamlit & Plotly <br>
                💡 Insights on Campaign Performance, ROI & Audience Behavior <br>
                
                <span style="color:#6e7681;">
                © 2026 | Designed & Developed by Dhruv Patel
                </span></div>
                """, unsafe_allow_html=True)


if st.session_state.logged_in:
    dashboard()
else:
    # layout of signup login page

    st.markdown("""
<style>
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.stApp {
    background: linear-gradient(-45deg, #020617, #0d1117, #0a192f, #020617);
    background-size: 400% 400%;
    animation: gradientShift 10s ease infinite;
}
.block-container { max-width: 520px; margin: auto; padding-top: 40px; }
.form-card {
    background: rgba(22, 27, 34, 0.6); backdrop-filter: blur(18px);
    border: 1px solid rgba(88, 166, 255, 0.2); border-radius: 18px;
    padding: 35px; box-shadow: 0px 8px 40px rgba(0,0,0,0.7); transition: 0.3s;
}
.form-card:hover { transform: translateY(-4px); box-shadow: 0px 12px 50px rgba(0,0,0,0.9); }
.form-title { text-align: center; font-size: 30px; font-weight: 700; color: #58a6ff; margin-bottom: 5px; }
.form-sub   { text-align: center; color: #8b949e; font-size: 14px; margin-bottom: 25px; }
.stTextInput input {
    background: rgba(13,17,23,0.8) !important; border: 1px solid #30363d !important;
    border-radius: 10px !important; color: #c9d1d9 !important; padding: 10px !important;
}
.stTextInput input:focus { border: 1px solid #58a6ff !important; box-shadow: 0 0 8px #58a6ff55 !important; outline: none !important; }
.stTextInput [data-baseweb="base-input"] { border-color: #30363d !important; }
.stTextInput [data-baseweb="base-input"]:focus-within { border-color: #58a6ff !important; box-shadow: 0 0 0 2px #58a6ff55 !important; }
.stButton>button, .stFormSubmitButton>button {
    width: 100%; background: linear-gradient(90deg, #1f6feb, #58a6ff);
    border: none; border-radius: 10px; padding: 12px; font-weight: 600; color: white; transition: 0.3s;
}
.stButton>button:hover, .stFormSubmitButton>button:hover { transform: scale(1.03); background: linear-gradient(90deg, #58a6ff, #1f6feb); }
.stTabs [data-baseweb="tab"] { font-size: 15px !important; font-weight: 600 !important; padding: 10px 30px !important; color: #8b949e !important; }
.stTabs [aria-selected="true"] { color: #58a6ff !important; background: rgba(88,166,255,0.08) !important; border-radius: 8px 8px 0 0 !important; }
.stTabs [data-baseweb="tab-highlight"] { background-color: #58a6ff !important; }
.stTabs [data-baseweb="tab-border"]    { background-color: transparent !important; }
input[type="password"]::-ms-reveal, input[type="password"]::-ms-clear { display: none; }
button[title="Show password"] { display: none !important; }
.stTextInput [data-baseweb="input"] { border: none !important; box-shadow: none !important; }
.stTextInput div { border-right: none !important; }
.stTextInput [data-baseweb="base-input"]:focus-within { box-shadow: none !important; border: none !important; }
</style>
""", unsafe_allow_html=True)
    
    # set sign up / login page width
    st.markdown("""
    <style>
    .block-container {
        max-width: 600px;
        margin: auto;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # set particles in background theme
    
    st.markdown("""
    <style>
    @keyframes float {
        0%   { transform: translateY(0px);   opacity: 0.3; }
        50%  { transform: translateY(-20px); opacity: 0.8; }
        100% { transform: translateY(0px);   opacity: 0.3; }
    }
    .particle {
        position: fixed;
        width: 4px;
        height: 4px;
        background: #58a6ff;
        border-radius: 50%;
        animation: float linear infinite;
    }
    .p1 { left: 10%; top: 20%; animation-duration: 4s;   }
    .p2 { left: 25%; top: 60%; animation-duration: 6s;   }
    .p3 { left: 50%; top: 30%; animation-duration: 5s;   }
    .p4 { left: 75%; top: 70%; animation-duration: 7s;   }
    .p5 { left: 90%; top: 40%; animation-duration: 4.5s; }
    </style>

    <div class="particle p1"></div>
    <div class="particle p2"></div>
    <div class="particle p3"></div>
    <div class="particle p4"></div>
    <div class="particle p5"></div>
    """, unsafe_allow_html=True)


    tab1, tab2 = st.tabs(["Signup", "Login"])

    with tab1:
        signup_page()

    with tab2:
        login_page()