"""
app.py

This script is the main entry point for the Streamlit web application that aims to help users gain more insights about preschool demand.
It also aims to forecasts future preschool demand based on historical trends and future plans.
"""
import streamlit as st
from streamlit_folium import st_folium

# Configure Streamlit
st.set_page_config(
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto"
)

from utils import (
    load_data,
    plot_trend,
    get_preschool_latlong,
    create_map
)
from forecast_model import (
    subzones_df,
    get_curr_year_demand,
    get_forecast_demand,
    get_forecast_plot,
    get_overview
)

# Title
st.title("Preschool Demand Forecast")

# Load data
annual_birth_and_fertility_rates, \
bto_mapping, list_of_centres, \
table_2000, table_2001_2010, \
table_2011_2019, table_2020, \
master_plan, sg_postal = load_data()

# Sidebar - Data Selection
st.sidebar.header("Data Selection")
subzone = st.sidebar.selectbox("Select Subzone", subzones_df["Subzone"].unique())

# Tabs for Content
tab1, tab2 = st.tabs(["Current Preschools", "Forecast"])

# Preschool Heatmap
with tab1:
    st.subheader("Preschool Heatmap")
    st.markdown("This heatmap shows the **current** number and location of existing preschools in Singapore.")

    # Generate Heatmap
    preschool_latlong = get_preschool_latlong(list_of_centres, sg_postal)
    m = create_map(preschool_latlong)

    # Display Heatmap
    with st.form(key="map_form", clear_on_submit=False):
        st_folium(m, width=1500)
        st.form_submit_button(label="", disabled=True)

# Forecasting tab
with tab2:
    st.info("Please select a subzone you would like to explore in the sidebar.")

    # Data preparation for forecasting
    subzone_wide = subzones_df[subzones_df["Subzone"] == subzone]
    subzone_long = subzone_wide.melt(id_vars=['Subzone'], var_name='Year', value_name='Count')
    subzone_long['Year'] = subzone_long['Year'].astype(int)

    # Plot trend
    st.markdown(f'Number of Children Over Years in **{subzone}**')
    placeholder = st.empty()
    plot_trend(subzone_long, placeholder)

    # Show forecast plot
    future_predictions, future_years = get_forecast_demand(subzone_long)
    if st.button("Show Forecast"):
        get_forecast_plot(subzone_long, future_predictions, placeholder)

    col1, col2 = st.columns(2)

    # Upcoming BTO projects data
    with col1:
        st.subheader("Upcoming BTO Projects")
        total_units_by_year = get_curr_year_demand(subzone)

        if total_units_by_year.empty:
            st.info("There are no upcoming BTO projects in this area.")
        else:
            styled_df = total_units_by_year.style.format({
                'Year': '{:.0f}',
                'Units': '{:,.0f}'
            })
            st.dataframe(styled_df, width=800, height=200)

    # Overview of preschool demand
    with col2:
        st.subheader("Overview")
        overview_df = get_overview(subzone_long, total_units_by_year, future_predictions, future_years)

        styled_overview_df = overview_df.style.apply(
            lambda s: ['background-color: #ccffcc' if col in future_years else '' for col in s.index], axis=1
        ).format(precision=0)
        st.dataframe(styled_overview_df, width=800, height=200)
