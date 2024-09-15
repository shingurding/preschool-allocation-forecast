"""
utils.py

This script manages data loading, cleaning, and visualization for preschool demand forecasting.
It includes functions for loading datasets, cleaning data, plotting trends, and creating interactive maps with Folium.
"""
import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster

# Read dataset
@st.cache_data
def load_data():
    """
    Loads and caches the datasets required for the application.

    Returns:
    - tuple: A tuple containing the following dataframes:
        - annual_birth_and_fertility_rates
        - bto_mapping
        - list_of_centres
        - table_2000
        - table_2001_2010
        - table_2011_2019
        - table_2020
        - master_plan
        - sg_postal
    """
    annual_birth_and_fertility_rates = pd.read_parquet("data/BirthsAndFertilityRatesAnnual.parquet")
    bto_mapping = pd.read_parquet("data/btomapping.parquet")
    list_of_centres = pd.read_parquet("data/ListingofCentres.parquet")
    table_2000 = pd.read_parquet("data/2000-Table.parquet")
    table_2001_2010 = pd.read_parquet("data/2001-2010-Table.parquet")
    table_2011_2019 = pd.read_parquet("data/2011-2019-Table.parquet")
    table_2020 = pd.read_parquet("data/2020-Table.parquet")
    master_plan = pd.read_parquet('data/MasterPlan2019SubzoneBoundaryNoSea.parquet')
    sg_postal = pd.read_parquet("data/SG_postal.parquet")
    return (
        annual_birth_and_fertility_rates,
        bto_mapping,
        list_of_centres,
        table_2000,
        table_2001_2010,
        table_2011_2019,
        table_2020,
        master_plan,
        sg_postal
    )

# Function to filter and clean dataframes
def convert_age(age):
    """
    Converts age values to integers, replacing "90 & Over" with 90.

    Args:
    - age (str): Age value to convert

    Returns:
    - int: Converted age value
    """
    if age == "90 & Over":
        return 90  # Replaces "90 & Over" values with 90
    return int(age)  # Convert other values to integers

def clean_table(table):
    """
    Cleans the provided dataframe by removing unnecessary entries and converting age values.

    Args:
    - table (pd.DataFrame): The dataframe to clean

    Returns:
    - pd.DataFrame: Cleaned dataframe
    """
    # Remove 'Total' and None in "Age" column
    table_filtered = table[~table["Age"].isin(['Total', None])]
    # Remove 'Males' and 'Females' in "Sex" column
    table_filtered = table_filtered[~table_filtered["Sex"].isin(['Males', 'Females'])].dropna()
    # Apply the convert_age function to the "Age" column
    table_filtered['Age'] = table_filtered['Age'].apply(convert_age)
    return table_filtered

def plot_trend(data_long, placeholder):
    """
    Plots the trend of the number of children aged 2 to 6 years over time.

    Args:
    - data_long (pd.DataFrame): DataFrame containing 'Year' and 'Count' columns
    - placeholder (streamlit.delta_generator.DeltaGenerator): Streamlit placeholder for rendering the chart
    """
    data_long = data_long.set_index('Year')
    df_plot = pd.DataFrame({
        'Count': data_long['Count']
    })
    placeholder.empty()
    placeholder.line_chart(df_plot, x_label="Year", y_label="Number of Children aged 2 to 6 years")
    st.warning("Please note that for newer subzones, data may not have been collected yet, so you might see values of 0.")

def get_preschool_latlong(list_of_centres, sg_postal):
    """
    Retrieves the latitude and longitude for each preschool based on postal code.

    Args:
    - list_of_centres (pd.DataFrame): DataFrame containing preschool details
    - sg_postal (pd.DataFrame): DataFrame containing postal code to latitude/longitude mapping

    Returns:
    - pd.DataFrame: DataFrame with preschool names, postal codes, addresses, and latitude/longitude
    """
    preschool_loc_df = pd.DataFrame({
        'centre_name': list_of_centres['centre_name'],
        'postal_code': list_of_centres['postal_code'],
        'centre_address': list_of_centres['centre_address']
    })
    preschool_latlong = preschool_loc_df.merge(sg_postal, on='postal_code', how='outer').dropna()
    return preschool_latlong

def get_subzone_latlong(subzone, master_plan):
    """
    Retrieves the latitude and longitude for the specified subzone.

    Args:
    - subzone (str): Name of the subzone
    - master_plan (pd.DataFrame): DataFrame containing subzone boundary information

    Returns:
    - tuple: Latitude and longitude of the subzone
    """
    subzone_uppercase = subzone.upper
    subzone_data = master_plan[master_plan["SUBZONE_N"] == subzone_uppercase]
    subzone_lat = subzone_data["X"].values
    subzone_lon = subzone_data["Y"].values
    return subzone_lat, subzone_lon

def create_map(preschool_latlong):
    """
    Creates a Folium map with markers for each preschool.

    Args:
    - preschool_latlong (pd.DataFrame): DataFrame containing preschool latitude and longitude

    Returns:
    - folium.Map: Folium map object with markers
    """
    m = folium.Map(location=[1.3521, 103.8198], zoom_start=13, tiles="Cartodb Positron")
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in preschool_latlong.iterrows():
        folium.Marker(
            location=[row['lat'], row['lon']],
            popup=row['centre_name'],  # Popup shows the center name
            tooltip=row['centre_name']  # Tooltip shows the center name when hovered
        ).add_to(marker_cluster)
    return m
