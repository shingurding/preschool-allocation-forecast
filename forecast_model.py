"""
forecast_model.py

This script contains functions to forecast preschool demand over the next five years. It includes:

1. Forecasting demand for each subzone and the entire country.
2. Generating overview summaries and visualizations of current and forecasted data.
"""
import numpy as np
import pandas as pd
import altair as alt
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA

from utils import (
    load_data,
    clean_table
)

# Load data
annual_birth_and_fertility_rates, \
bto_mapping, list_of_centres, \
table_2000, table_2001_2010, \
table_2011_2019, table_2020, \
master_plan, sg_postal = load_data()

# Clean and Merge data
table_2000_filtered = clean_table(table_2000)
table_2001_2010_filtered = clean_table(table_2001_2010)
table_2011_2019_filtered = clean_table(table_2011_2019)
table_2020_filtered = clean_table(table_2020)

merged_df = table_2000_filtered.merge(table_2001_2010_filtered, on=["Planning Area", "Subzone", "Age", "Sex"], how="outer") \
                               .merge(table_2011_2019_filtered, on=["Planning Area", "Subzone", "Age", "Sex"], how="outer") \
                               .merge(table_2020_filtered, on=["Planning Area", "Subzone", "Age", "Sex"], how="outer")
merged_df_filtered = merged_df[(merged_df["Age"] > 1) & (merged_df["Age"] <= 6)].drop(columns = ["Planning Area", "Sex"])
merged_df_filtered = merged_df_filtered[~merged_df_filtered.isin(['Total', 'None']).any(axis=1)]
columns_to_sum = [str(year) for year in range(2000, 2021)]

for column in columns_to_sum:
    # Replace commas with empty strings
    merged_df_filtered[column] = merged_df_filtered[column].replace({',': ''}, regex=True)
    # Convert to numeric, setting errors='coerce' will convert non-numeric values to NaN
    merged_df_filtered[column] = pd.to_numeric(merged_df_filtered[column], errors='coerce')
    # Fill nan values with 0 or another placeholder
    merged_df_filtered[column] = merged_df_filtered[column].fillna(0).astype(int)

subzones_df = merged_df_filtered.groupby("Subzone")[columns_to_sum].sum().reset_index()

def get_curr_year_demand(subzone):
    """
    Retrieves the current demand for the specified subzone.

    Args:
    - subzone (str): Name of the subzone

    Returns:
    - pd.DataFrame: Data about the current demand for the specified subzone
    """
    # Get the data for the specified subzone
    bto_mapping_subzone = bto_mapping[bto_mapping["Subzone"] == subzone]
    # For each subzone, group by the year of completion
    total_units_by_year = bto_mapping_subzone.groupby("Estimated completion year")["Total number of units"].sum()
    return pd.DataFrame(total_units_by_year)

def get_overview(subzone_long, curr_year_demand, future_predictions, future_years):
    """
    Provides an overview of current demand, forecasted demand, and upcoming demand based on BTO projects.

    Args:
    - subzone_long (pd.DataFrame): DataFrame containing subzone details
    - curr_year_demand (pd.DataFrame): DataFrame with the current BTO projects for the specified subzone
    - future_predictions (np.ndarray): Array of forecasted demand values for the future years
    - future_years (np.ndarray): Array of future years to be forecasted

    Returns:
    - pd.DataFrame: DataFrame summarizing the current and forecasted demand
    """
    forecast_df = pd.DataFrame({
        'Year': future_years.flatten(),
        'Count': future_predictions.values
    })
    forecasted_df = pd.concat([subzone_long.drop(columns="Subzone"), forecast_df])
    forecasted_df["Count"] = forecasted_df["Count"].astype(int)
    forecasted_df_wide = forecasted_df.pivot_table(values='Count', columns='Year')

    if not curr_year_demand.empty:
        curr_year_demand_wide = curr_year_demand.pivot_table(values='Total number of units', columns='Estimated completion year')
        common_years = forecasted_df_wide.columns.intersection(curr_year_demand_wide.columns)
        merged_df = pd.merge(forecasted_df_wide, curr_year_demand_wide, on=list(common_years), how='outer')

        total_demand_list = merged_df.iloc[1].tolist()  # Saving all the current demand in here
        for idx, col in enumerate(merged_df.columns):
            current_year = int(col)

            # Get the upcoming demand two years ago
            two_years_before = current_year - 2
            if two_years_before in merged_df.columns:
                two_years_before_demand = merged_df[two_years_before].iloc[0]
            else:
                two_years_before_demand = np.nan

            # Get the index for the next five years
            next_five_years = list(range(idx, idx + 6)) if (idx + 5) < len(merged_df.columns) else list(range(idx, len(merged_df.columns)))

            # If there was an upcoming demand 2 years ago
            if not pd.isna(two_years_before_demand):
                two_years_before_demand_med = int(two_years_before_demand / 5)
                # Add the upcoming median demand to current year and 5 years later
                for year_idx in next_five_years:
                    total_demand_list[year_idx] = int(total_demand_list[year_idx]) + two_years_before_demand_med

        total_demand_df = pd.DataFrame([total_demand_list], columns=merged_df.columns).astype(int)
        overview_df = pd.concat([merged_df, total_demand_df], ignore_index=True)

        first_column = pd.DataFrame({
            "Year": ["Upcoming Demand", "Current Demand", "Total Demand"]
        })
        overview = pd.concat([first_column, overview_df], axis=1).reindex([1, 0, 2])

        return overview

    first_column = pd.DataFrame({
        "Year": ["Current Demand"]
    })
    merged_df = pd.concat([first_column, forecasted_df_wide.reset_index(drop=True)], axis=1)

    return merged_df

def get_forecast_demand(data_long):
    """
    Forecasts the demand for preschool based on historical data and fertility rates.

    Args:
    - data_long (pd.DataFrame): DataFrame with historical preschool demand data

    Returns:
    - tuple: A tuple containing:
        - forecast (np.ndarray): Forecasted demand values for the next years
        - future_years (np.ndarray): Array of future years
    """
    fertility_rate = annual_birth_and_fertility_rates[:1]
    fertility_rate_long = fertility_rate.melt(id_vars=['DataSeries'],
                                              var_name='Year',
                                              value_name='Rate')
    fertility_rate_long['Year'] = fertility_rate_long['Year'].astype(int)
    filtered_fertility_rate_long = fertility_rate_long[fertility_rate_long['Year'] >= 2000]

    data_long['Year'] = data_long['Year'].astype(int)
    data_long_with_rates = data_long.merge(filtered_fertility_rate_long, on="Year", how="outer").drop(columns=["DataSeries"])
    data_long_with_rates.set_index('Year', inplace=True)
    data_long_with_rates.index.values

    # Create lagged feature of the fertility rate (lag of 2 years)
    data_long_with_rates['Rate_lagged'] = data_long_with_rates['Rate'].shift(2)
    data_long_with_rates.dropna(subset=['Rate', 'Rate_lagged'], inplace=True)

    # Known exog values and predict the next few years
    known_years = data_long_with_rates.index.values.reshape(-1, 1)
    known_exog = data_long_with_rates[['Rate', 'Rate_lagged']].astype(float)
    years_forecast = np.array([2024, 2025, 2026, 2027, 2028, 2029]).reshape(-1, 1)

    reg = LinearRegression()
    reg.fit(known_years, known_exog)
    exog_last_6_years = reg.predict(years_forecast)

    # Define the endogenous and exogenous variables
    data_long_until_2020 = data_long_with_rates[:19]

    endog = data_long_until_2020['Count'].astype(int)
    exog = data_long_until_2020[['Rate', 'Rate_lagged']].astype(float)

    # Fit the SARIMAX model with exogenous variables
    model = ARIMA(endog, exog=exog, order=(1, 1, 1))
    model_fit = model.fit()

    # Forecast
    forecast_periods = 9
    exog_future = data_long_with_rates[19:][['Rate', 'Rate_lagged']]
    years_last_6 = np.arange(data_long_with_rates.index.max() + 1, data_long_with_rates.index.max() + 7)
    exog_last_6_df = pd.DataFrame({
        'Rate': exog_last_6_years[:, 0],
        'Rate_lagged': exog_last_6_years[:, 1]
    }, index=years_last_6)
    exog_future_extended = pd.concat([exog_future, exog_last_6_df])
    exog_future_extended[['Rate', 'Rate_lagged']] = exog_future_extended[['Rate', 'Rate_lagged']].astype(float)

    forecast = model_fit.forecast(steps=forecast_periods, exog=exog_future_extended)
    future_years = np.arange(data_long['Year'].max() + 1, data_long['Year'].max() + 10).reshape(-1, 1)

    return forecast, future_years

def get_forecast_plot(data_long, future_predictions, placeholder):
    """
    Creates a plot showing both actual and forecasted preschool demand data.

    Args:
    - data_long (pd.DataFrame): DataFrame with historical preschool demand data
    - future_predictions (np.ndarray): Array of forecasted demand values
    - placeholder (st.empty): Streamlit placeholder to render the chart
    """
    future_years = np.arange(data_long['Year'].max() + 1, data_long['Year'].max() + 10).reshape(-1, 1)
    future_forecast_df = pd.DataFrame({
        'Year': future_years.flatten(),
        'Count': future_predictions.astype(int),
        'Type': 'Future Forecast'
    })

    data_long['Type'] = 'Actual'

    # Combine the dataframes
    combined_df = pd.concat([data_long, future_forecast_df])

    # Create Altair chart
    color_map = {
        'Actual': '#1f77b4',  # Blue
        'Future Forecast': 'red'
    }
    chart = alt.Chart(combined_df).mark_line().encode(
        x='Year:O',
        y='Count:Q',
        color=alt.Color('Type:N', scale=alt.Scale(domain=list(color_map.keys()), range=list(color_map.values()))),
        tooltip=['Year', 'Count', 'Type']
    ).properties(
        title='Forecast and Actual Data'
    )
    placeholder.empty()
    placeholder.altair_chart(chart, use_container_width=True)
