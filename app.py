import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import datetime

import io
from data_loader import DELHI_DISTRICTS_PLACES, generate_delhi_traffic_dataset, generate_full_year_2024_dataset
from emission_model import (
    EMISSION_FACTORS, DEFAULT_FUEL_MIX, DEFAULT_VEHICLE_SPLIT, 
    calculate_emissions_for_dataframe, calculate_aqi_from_emissions, 
    calculate_sub_index, get_aqi_category
)

# Page Configuration
st.set_page_config(
    page_title="Delhi Traffic & Vehicle Emission Probe 2024",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #3B82F6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-card-emissions {
        background-color: #FEF2F2;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #EF4444;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-card-aqi {
        background-color: #F0FDF4;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #10B981;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0F172A;
    }
    .metric-lbl {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Title Header
st.markdown('<div class="main-header">🚗 Delhi Traffic, Emission & AQI Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Comprehensive Probe Analytics: District & Place Level Vehicle Counting, Fuel Breakdown, Per-Vehicle Tailpipe Emissions, and CPCB Air Quality Index (AQI) Calculation</div>', unsafe_allow_html=True)

# Sidebar Filters
st.sidebar.header("🗓️ Calendar & Interval Settings")

# Date Interval Picker Button / Widget
today = datetime.date(2024, 1, 1)
default_end = datetime.date(2024, 1, 7)

date_range = st.sidebar.date_input(
    "Set Date Interval Range:",
    value=(today, default_end),
    min_value=datetime.date(2024, 1, 1),
    max_value=datetime.date(2024, 12, 31),
    key="date_range_picker"
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
elif isinstance(date_range, tuple) and len(date_range) == 1:
    start_d = end_d = date_range[0]
else:
    start_d = end_d = today

# Hourly Filter
hour_slot = st.sidebar.slider("Select Hour Slot (0-23 hrs):", 0, 23, (0, 23))

st.sidebar.markdown("---")
st.sidebar.header("📍 District & Location Filters")

all_districts = list(DELHI_DISTRICTS_PLACES.keys())
selected_districts = st.sidebar.multiselect("Select Delhi District(s):", all_districts, default=all_districts)

if selected_districts:
    available_places = []
    for d in selected_districts:
        for p in DELHI_DISTRICTS_PLACES[d]:
            available_places.append(p['name'])
    selected_places = st.sidebar.multiselect("Select Specific Place / Hotspot:", available_places, default=available_places)
else:
    selected_places = []

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Vehicle Trip Parameters")
avg_trip_km = st.sidebar.number_input("Avg Trip Distance per Vehicle (km):", min_value=1.0, max_value=50.0, value=5.0, step=0.5)

# Load / Cached Data Generation
@st.cache_data(show_spinner="Loading Delhi Traffic Probe Data...")
def get_base_traffic_data(s_date, e_date):
    return generate_delhi_traffic_dataset(s_date, e_date)

raw_df = get_base_traffic_data(start_d, end_d)

# Filter Data
filtered_raw = raw_df[
    (pd.to_datetime(raw_df['date']).dt.date >= start_d) &
    (pd.to_datetime(raw_df['date']).dt.date <= end_d) &
    (raw_df['hour'] >= hour_slot[0]) &
    (raw_df['hour'] <= hour_slot[1]) &
    (raw_df['district'].isin(selected_districts)) &
    (raw_df['place'].isin(selected_places))
]

if filtered_raw.empty:
    st.warning("⚠️ No traffic probe data matches the selected filters. Please adjust the sidebar settings.")
    st.stop()

# Compute Emissions Dataframe
emissions_df = calculate_emissions_for_dataframe(filtered_raw, avg_trip_km=avg_trip_km)

# --- KPI METRICS ---
total_vehicle_count = emissions_df['vehicle_count'].sum()
total_co2_tonnes = emissions_df['co2_kg'].sum() / 1000.0
total_nox_kg = emissions_df['nox_g'].sum() / 1000.0
total_pm25_kg = emissions_df['pm25_g'].sum() / 1000.0

# Estimate ambient pollutant concentration (micrograms / m3 for PM2.5 & NO2, mg/m3 for CO)
# Model assumption: Traffic emissions disperse into an urban mixing box volume over the selected hours/places
num_places = max(1, len(filtered_raw['place'].unique()))
num_hours = max(1, len(filtered_raw['date'].unique()) * (hour_slot[1] - hour_slot[0] + 1))
estimated_pm25_ug_m3 = min(450.0, 35.0 + (total_pm25_kg * 1000.0 / (num_places * num_hours * 15.0)))
estimated_no2_ug_m3 = min(350.0, 25.0 + (total_nox_kg * 1000.0 / (num_places * num_hours * 25.0)))
estimated_co_mg_m3 = min(25.0, 0.8 + ((emissions_df['co_g'].sum() / 1000.0) / (num_places * num_hours * 100.0)))

aqi_res = calculate_aqi_from_emissions(estimated_pm25_ug_m3, estimated_no2_ug_m3, estimated_co_mg_m3)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-lbl">Total Vehicle Count</div>
        <div class="metric-val">{total_vehicle_count:,.0f}</div>
        <div style="font-size:0.75rem; color:#64748B;">Across Selected Interval</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card-emissions">
        <div class="metric-lbl">Total CO₂ Emissions</div>
        <div class="metric-val">{total_co2_tonnes:,.2f} <span style="font-size:1rem;">Tonnes</span></div>
        <div style="font-size:0.75rem; color:#EF4444;">Tailpipe Total</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card-emissions">
        <div class="metric-lbl">Total NOₓ Pollutants</div>
        <div class="metric-val">{total_nox_kg:,.1f} <span style="font-size:1rem;">kg</span></div>
        <div style="font-size:0.75rem; color:#EF4444;">Nitrogen Oxides</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card-emissions">
        <div class="metric-lbl">Total PM₂.₅ Particulate</div>
        <div class="metric-val">{total_pm25_kg:,.2f} <span style="font-size:1rem;">kg</span></div>
        <div style="font-size:0.75rem; color:#EF4444;">Fine Particulate Matter</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card-aqi" style="border-left-color: {aqi_res['color']};">
        <div class="metric-lbl">Estimated AQI (CPCB)</div>
        <div class="metric-val" style="color: {aqi_res['color']};">{aqi_res['aqi']}</div>
        <div style="font-size:0.75rem; font-weight:700; color:{aqi_res['color']};">{aqi_res['category']}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_map, tab_emissions, tab_aqi, tab_district, tab_dataset = st.tabs([
    "🗺️ Delhi Map & Hotspots", 
    "📊 Per-Vehicle & Fuel Emissions Breakdown", 
    "🍃 Air Quality Index (AQI) Calculator",
    "🏙️ District & Place Counts Table",
    "📁 Dataset Inspector / Custom Upload"
])


# ---------------- TAB 1: MAP ----------------
with tab_map:
    st.subheader("Interactive Delhi Traffic Probe & Emission Map")
    
    place_agg = filtered_raw.groupby(['district', 'place', 'lat', 'lon']).agg({
        'vehicle_count': 'sum',
        'congestion_level': 'mean'
    }).reset_index()
    
    # Calculate emissions per place
    place_emissions = emissions_df.groupby(['district', 'place']).agg({
        'co2_kg': 'sum',
        'nox_g': 'sum',
        'pm25_g': 'sum'
    }).reset_index()
    
    map_data = pd.merge(place_agg, place_emissions, on=['district', 'place'])
    map_data['co2_tonnes'] = map_data['co2_kg'] / 1000.0
    
    map_view = st.radio("Map Display Mode:", ["Vehicle Count Density Heatmap", "CO2 Emission Hotspot Bubbles"], horizontal=True)
    
    scatter_fn = getattr(px, 'scatter_map', px.scatter_mapbox)
    style_param = {'map_style': 'open-street-map'} if hasattr(px, 'scatter_map') else {'mapbox_style': 'carto-positron'}
    
    if map_view == "Vehicle Count Density Heatmap":
        fig_map = scatter_fn(
            map_data,
            lat="lat",
            lon="lon",
            size="vehicle_count",
            color="vehicle_count",
            color_continuous_scale=px.colors.cyclical.IceFire,
            size_max=35,
            zoom=10.5,
            center={"lat": 28.6139, "lon": 77.2090},
            hover_name="place",
            hover_data={"district": True, "vehicle_count": ":,", "congestion_level": ":.2f", "lat": False, "lon": False},
            title="Vehicle Traffic Volume across Delhi Places",
            **style_param
        )
    else:
        fig_map = scatter_fn(
            map_data,
            lat="lat",
            lon="lon",
            size="co2_tonnes",
            color="co2_tonnes",
            color_continuous_scale=px.colors.sequential.Reds,
            size_max=35,
            zoom=10.5,
            center={"lat": 28.6139, "lon": 77.2090},
            hover_name="place",
            hover_data={"district": True, "co2_tonnes": ":.2f", "lat": False, "lon": False},
            title="CO2 Emission Hotspots across Delhi Places (Tonnes)",
            **style_param
        )
        
    fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=550)
    st.plotly_chart(fig_map, use_container_width=True)

# ---------------- TAB 2: PER-VEHICLE EMISSIONS ----------------
with tab_emissions:
    st.subheader("🔥 Per-Vehicle & Fuel Category Emission Intensity")
    st.markdown("Detailed breakdown of emission factors, per-vehicle emission rates, and total cumulative tailpipe emissions.")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### 1. Emission Factor Rates per Vehicle (g/km)")
        
        # Per vehicle emission rate summary table
        per_veh_rates = []
        for vtype, fuels in EMISSION_FACTORS.items():
            for ftype, rates in fuels.items():
                per_veh_rates.append({
                    "Vehicle Category": vtype,
                    "Fuel Type": ftype,
                    "CO₂ (g/km)": rates["CO2"],
                    "NOₓ (g/km)": rates["NOx"],
                    "PM₂.₅ (g/km)": rates["PM2.5"],
                    "CO (g/km)": rates["CO"]
                })
        rates_df = pd.DataFrame(per_veh_rates)
        st.dataframe(rates_df, hide_index=True, use_container_width=True)
        
    with c2:
        st.markdown("### 2. Vehicle Category Share vs Emission Share")
        veh_summary = emissions_df.groupby('vehicle_type').agg({
            'vehicle_count': 'sum',
            'co2_kg': 'sum'
        }).reset_index()
        veh_summary['co2_tonnes'] = veh_summary['co2_kg'] / 1000.0
        
        fig_donut = px.pie(
            veh_summary, 
            names='vehicle_type', 
            values='co2_tonnes',
            title='CO2 Share by Vehicle Category',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        
    st.markdown("---")
    st.markdown("### 3. Total Emission Breakdown by Fuel Category & Vehicle Type")
    
    fuel_v_agg = emissions_df.groupby(['vehicle_type', 'fuel_type']).agg({
        'vehicle_count': 'sum',
        'co2_kg': 'sum',
        'nox_g': 'sum',
        'pm25_g': 'sum'
    }).reset_index()
    fuel_v_agg['co2_tonnes'] = fuel_v_agg['co2_kg'] / 1000.0
    fuel_v_agg['nox_kg'] = fuel_v_agg['nox_g'] / 1000.0
    
    fig_bar = px.bar(
        fuel_v_agg,
        x='vehicle_type',
        y='co2_tonnes',
        color='fuel_type',
        title='Total CO2 Emissions (Tonnes) by Vehicle Category and Fuel Type',
        labels={'co2_tonnes': 'CO2 Emissions (Tonnes)', 'vehicle_type': 'Vehicle Category', 'fuel_type': 'Fuel Type'},
        barmode='stack'
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# ---------------- TAB 3: AQI CALCULATOR & BREAKPOINTS ----------------
with tab_aqi:
    st.subheader("🍃 Indian CPCB Air Quality Index (AQI) Estimator & Formula")
    st.markdown("""
    The **Air Quality Index (AQI)** transforms complex air pollutant concentration data into a single numerical index and color-coded health warning.
    """)
    
    col_aqi1, col_aqi2 = st.columns([1, 1])
    
    with col_aqi1:
        st.markdown("### 🧮 Interactive AQI Sub-Index Calculator")
        st.caption("Input ambient pollutant concentrations to calculate sub-indices and overall AQI:")
        
        user_pm25 = st.slider("PM2.5 Concentration (µg/m³ - 24hr avg):", 0.0, 500.0, float(round(estimated_pm25_ug_m3, 1)), step=1.0)
        user_no2 = st.slider("NO2 Concentration (µg/m³ - 24hr avg):", 0.0, 500.0, float(round(estimated_no2_ug_m3, 1)), step=1.0)
        user_co = st.slider("CO Concentration (mg/m³ - 8hr avg):", 0.0, 50.0, float(round(estimated_co_mg_m3, 1)), step=0.1)
        
        calc_res = calculate_aqi_from_emissions(user_pm25, user_no2, user_co)
        
        st.markdown(f"""
        <div style="background-color: {calc_res['color']}22; border-left: 6px solid {calc_res['color']}; padding: 15px; border-radius: 8px; margin-top: 15px;">
            <h2 style="margin: 0; color: {calc_res['color']};">Calculated AQI: {calc_res['aqi']}</h2>
            <h4 style="margin: 5px 0 0 0; color: {calc_res['color']};">Category: {calc_res['category']}</h4>
            <p style="margin: 5px 0 0 0; color: #475569; font-size: 0.9rem;">
                <b>Prominent Pollutant:</b> {calc_res['prominent_pollutant']}<br>
                <b>Sub-Indices:</b> PM2.5 = {calc_res['sub_pm25']} | NO2 = {calc_res['sub_no2']} | CO = {calc_res['sub_co']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_aqi2:
        st.markdown("### 📐 The AQI Formula (CPCB Piecewise Linear Interpolation)")
        st.latex(r"I_p = I_{\text{low}} + \left( \frac{I_{\text{high}} - I_{\text{low}}}{B_{\text{high}} - B_{\text{low}}} \right) \times (C_p - B_{\text{low}})")
        st.markdown("""
        **Where:**
        - **$C_p$**: Input concentration of pollutant $p$
        - **$B_{\text{low}}, B_{\text{high}}$**: Breakpoint concentrations containing $C_p$
        - **$I_{\text{low}}, I_{\text{high}}$**: AQI index values corresponding to $B_{\text{low}}, B_{\text{high}}$
        
        **Final AQI Determination:**
        """)
        st.latex(r"\text{AQI} = \max(I_{\text{PM2.5}}, I_{\text{PM10}}, I_{\text{NO2}}, I_{\text{SO2}}, I_{\text{CO}}, I_{\text{O3}}, I_{\text{NH3}}, I_{\text{Pb}})")
        st.caption("Overall AQI equals the MAXIMUM of all calculated pollutant sub-indices.")

    st.markdown("---")
    st.markdown("### 📋 CPCB Indian National Air Quality Index (NAQI) Breakpoints Table")
    
    breakdown_data = [
        {"Category": "Good (0–50)", "PM2.5 (µg/m³)": "0 – 30", "NO2 (µg/m³)": "0 – 40", "CO (mg/m³)": "0 – 1.0", "Health Impact": "Minimal impact"},
        {"Category": "Satisfactory (51–100)", "PM2.5 (µg/m³)": "31 – 60", "NO2 (µg/m³)": "41 – 80", "CO (mg/m³)": "1.1 – 2.0", "Health Impact": "Minor breathing discomfort to sensitive people"},
        {"Category": "Moderate (101–200)", "PM2.5 (µg/m³)": "61 – 90", "NO2 (µg/m³)": "81 – 180", "CO (mg/m³)": "2.1 – 10.0", "Health Impact": "Breathing discomfort to people with lungs/heart disease"},
        {"Category": "Poor (201–300)", "PM2.5 (µg/m³)": "91 – 120", "NO2 (µg/m³)": "181 – 280", "CO (mg/m³)": "10.1 – 17.0", "Health Impact": "Breathing discomfort to most people on prolonged exposure"},
        {"Category": "Very Poor (301–400)", "PM2.5 (µg/m³)": "121 – 250", "NO2 (µg/m³)": "281 – 400", "CO (mg/m³)": "17.1 – 34.0", "Health Impact": "Respiratory illness on prolonged exposure"},
        {"Category": "Severe (401–500)", "PM2.5 (µg/m³)": "> 250", "NO2 (µg/m³)": "> 400", "CO (mg/m³)": "> 34.0", "Health Impact": "Affects healthy people and seriously impacts those with existing diseases"}
    ]
    st.dataframe(pd.DataFrame(breakdown_data), hide_index=True, use_container_width=True)

# ---------------- TAB 4: DISTRICT & PLACE COUNTS ----------------
with tab_district:
    st.subheader("🏙️ Delhi District & Place Level Vehicle & Emission Summary")
    
    district_agg = emissions_df.groupby(['district', 'place']).agg({
        'vehicle_count': 'sum',
        'co2_kg': 'sum',
        'nox_g': 'sum',
        'pm25_g': 'sum'
    }).reset_index()
    
    district_agg['co2_tonnes'] = (district_agg['co2_kg'] / 1000.0).round(2)
    district_agg['nox_kg'] = (district_agg['nox_g'] / 1000.0).round(2)
    district_agg['pm25_kg'] = (district_agg['pm25_g'] / 1000.0).round(2)
    
    table_view = district_agg[['district', 'place', 'vehicle_count', 'co2_tonnes', 'nox_kg', 'pm25_kg']].rename(columns={
        'district': 'District',
        'place': 'Place / Hotspot',
        'vehicle_count': 'Total Vehicle Count',
        'co2_tonnes': 'CO₂ (Tonnes)',
        'nox_kg': 'NOₓ (kg)',
        'pm25_kg': 'PM₂.₅ (kg)'
    })
    
    st.dataframe(
        table_view.sort_values(by='Total Vehicle Count', ascending=False),
        hide_index=True,
        use_container_width=True
    )
    
    csv_bytes = table_view.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Download District Emission & Count Report (CSV)",
        data=csv_bytes,
        file_name="delhi_traffic_emission_report.csv",
        mime="text/csv"
    )

# ---------------- TAB 4: DATASET INSPECTOR ----------------
with tab_dataset:
    st.subheader("📁 Dataset Inspector & Upload")
    st.markdown("""
    You can analyze the built-in Delhi Traffic Probe 2024 dataset, or upload your own Kaggle CSV dataset below:
    """)
    
    uploaded_file = st.file_uploader("Upload New Delhi Traffic Probe CSV File (Kaggle Dataset):", type=['csv'])
    
    if uploaded_file is not None:
        try:
            user_df = pd.read_csv(uploaded_file)
            st.success("✅ File uploaded successfully!")
            st.dataframe(user_df.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
    else:
        st.info("Showing raw preview of current probe dataset (Top 50 records):")
        st.dataframe(filtered_raw.head(50), hide_index=True, use_container_width=True)
        
    st.markdown("---")
    st.subheader("📥 Download Full Year 2024 Dataset (365 Days)")
    st.markdown("""
    Download the complete annual Delhi dataset covering **Jan 1, 2024 to Dec 31, 2024** across all 11 districts and locations.  
    **Columns Included:** `Date`, `District`, `Location`, `Vehicle Count`, `Congestion`, `AQI`, `AQI Category`.
    """)
    
    @st.cache_data(show_spinner="Generating full 365-Day Delhi 2024 Traffic & AQI Dataset...")
    def load_full_year_data():
        return generate_full_year_2024_dataset()
        
    full_year_df = load_full_year_data()
    
    col_dl1, col_dl2 = st.columns(2)
    
    # Excel export
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        full_year_df.to_excel(writer, index=False, sheet_name='Delhi_2024_Traffic_AQI')
    excel_bytes = excel_buffer.getvalue()
    
    # CSV export
    csv_365_bytes = full_year_df.to_csv(index=False).encode('utf-8')
    
    with col_dl1:
        st.download_button(
            label="📊 Download Full 365-Day Excel File (.xlsx)",
            data=excel_bytes,
            file_name="Delhi_Traffic_AQI_365Days_2024.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        
    with col_dl2:
        st.download_button(
            label="📄 Download Full 365-Day CSV File (.csv)",
            data=csv_365_bytes,
            file_name="Delhi_Traffic_AQI_365Days_2024.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    st.caption("Dataset Preview (14,600 total daily records for all 40 locations in 2024):")
    st.dataframe(full_year_df.head(100), hide_index=True, use_container_width=True)

