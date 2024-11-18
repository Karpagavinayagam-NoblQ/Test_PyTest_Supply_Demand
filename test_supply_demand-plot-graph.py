import streamlit as st
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import plotly.graph_objects as go
import pyodbc  # To interact with MS SQL
import warnings
warnings.filterwarnings('ignore')
#import Demo1 as td

import pytest
from sklearn.metrics import r2_score

def Create_DataFrame():
    # Supply data
    df_supply = {
        'ds': ['01-12-2024', '12-12-2024','15-12-2024', '18-12-2024','21-12-2024', '22-12-2024','25-12-2024', '26-12-2024'],
        'y': [71835.71, 86449.29,70005.61, 86409.22,81835.71, 86949.29,51835.71, 87449.29]
    }

    # Create DataFrame for supply
    df_supply = pd.DataFrame(df_supply)

    # Convert 'ds' column to datetime format
    df_supply['ds'] = pd.to_datetime(df_supply['ds'], format='%d-%m-%Y')

    # Demand data
    df_demand = {
        'ds': ['03-12-2024', '08-12-2024','10-12-2024', '12-12-2024','16-12-2024', '17-12-2024','19-12-2024', '21-12-2024'],
        'y': [93.12, 97.43, 89.89,87.67,94.34,88.45,90.30,97.23]
    }

    # Create DataFrame for demand
    df_demand = pd.DataFrame(df_demand)

    # Convert 'ds' column to datetime format
    df_demand['ds'] = pd.to_datetime(df_demand['ds'], format='%d-%m-%Y')

    return df_supply, df_demand


class Test_supply_demand():
    try:
        df_supply, df_demand = Create_DataFrame()      

        data_points = len(df_supply)
        forecast_horizon = min(365, int(data_points * 0.7))  # Ensure we forecast no more than 70% of historical data
        if forecast_horizon < 1:
            st.error("Not enough data for forecasting. Please upload more historical data.")
        else:
            supply_model = Prophet(yearly_seasonality=True, weekly_seasonality=True, seasonality_mode='multiplicative')
            supply_model.fit(df_supply)

            demand_model = Prophet(yearly_seasonality=True, weekly_seasonality=True, seasonality_mode='multiplicative')
            demand_model.fit(df_demand)

            future_supply = supply_model.make_future_dataframe(periods=forecast_horizon)
            supply_forecast = supply_model.predict(future_supply)

            future_demand = demand_model.make_future_dataframe(periods=forecast_horizon)
            demand_forecast = demand_model.predict(future_demand)

            merged_supply = pd.merge(df_supply, supply_forecast[['ds', 'yhat']], on='ds', how='left')
            merged_demand = pd.merge(df_demand, demand_forecast[['ds', 'yhat']], on='ds', how='left')

            supply_mae = mean_absolute_error(merged_supply['y'], merged_supply['yhat'])
            supply_rmse = mean_squared_error(merged_supply['y'], merged_supply['yhat'], squared=False)
            supply_r2 = r2_score(merged_supply['y'], merged_supply['yhat'])

            # Assert that the R² score is between 0 and 1
            assert 0 <= supply_r2 <= 1, f"R² score is out of range: {supply_r2}"
            # Optionally, you could test for values greater than 0 (e.g., for a good model)
            # You could adjust the lower bound depending on the expected performance of your model
            # For example, if you want to ensure that your model performs at least as well as random guessing:
            assert supply_r2 >= 0, f"R² score is negative, indicating poor model performance: {supply_r2}"

            demand_mae = mean_absolute_error(merged_demand['y'], merged_demand['yhat'])
            demand_rmse = mean_squared_error(merged_demand['y'], merged_demand['yhat'], squared=False)
            demand_r2 = r2_score(merged_demand['y'], merged_demand['yhat'])

            st.write(f"**Supply Forecast (Prophet) - MAE:** {supply_mae:.2f}, **RMSE:** {supply_rmse:.2f}, **R²:** {supply_r2:.2f}")
            st.write(f"**Demand Forecast (Prophet) - MAE:** {demand_mae:.2f}, **RMSE:** {demand_rmse:.2f}, **R²:** {demand_r2:.2f}")

            forecast_df = pd.DataFrame({
                'Forecast Date': future_supply['ds'],
                'Supply Forecast (USD)': supply_forecast['yhat'],
                'Demand Forecast (%)': demand_forecast['yhat']
            })

            st.subheader(f"Forecasted Supply and Demand Values ")
            st.dataframe(forecast_df)

            st.download_button(
                label="Download Forecasted Supply and Demand Data",
                data=forecast_df.to_csv(index=False),
                file_name="forecasted_supply_demand.csv",
                mime="text/csv"
            )

            # Button to store the predicted values in MS SQL database
            if st.button('Store Predicted Values in Database'):
                insert_to_db(forecast_df)

            # ========== Actual vs Predicted Supply Area Plot ========== 
            st.subheader("Actual vs Predicted Supply Area Plot")
            supply_fig = go.Figure()

            supply_fig.add_trace(go.Scatter(
                x=merged_supply['ds'], 
                y=merged_supply['y'],
                mode='lines', name='Actual Supply (USD)',
                fill='tozeroy', line=dict(color='blue')
            ))

            supply_fig.add_trace(go.Scatter(
                x=merged_supply['ds'], 
                y=merged_supply['yhat'],
                mode='lines', name='Predicted Supply (USD)',
                fill='tozeroy', line=dict(color='red')
            ))

            supply_fig.update_layout(
                title='Actual vs Predicted Supply (Area Plot)',
                xaxis_title='Date',
                yaxis_title='Supply Value (USD)',
                legend_title='Supply',
            )

            st.plotly_chart(supply_fig)

            # ========== Actual vs Predicted Demand ========== 
            st.subheader("Actual vs Predicted Demand Area Plot")
            demand_fig = go.Figure()

            demand_fig.add_trace(go.Scatter(
                x=merged_demand['ds'], 
                y=merged_demand['y'],
                mode='lines', name='Actual Demand (%)',
                fill='tozeroy', line=dict(color='green')
            ))

            demand_fig.add_trace(go.Scatter(
                x=merged_demand['ds'], 
                y=merged_demand['yhat'],
                mode='lines', name='Predicted Demand (%)',
                fill='tozeroy', line=dict(color='orange')
            ))

            demand_fig.update_layout(
                title='Actual vs Predicted Demand (Area Plot)',
                xaxis_title='Date',
                yaxis_title='Demand Value (%)',
                legend_title='Demand',
            )

            st.plotly_chart(demand_fig)

            # ========== Forecasted Supply (Bar Plot) ========== 
            st.subheader(f"Forecasted Supply Bar Plot")
            supply_forecast_bar_fig = go.Figure()

            supply_forecast_bar_fig.add_trace(go.Bar(
                x=forecast_df['Forecast Date'], 
                y=forecast_df['Supply Forecast (USD)'],
                name='Supply Forecast (USD)',
                marker=dict(color='red')
            ))

            supply_forecast_bar_fig.update_layout(
                title=f'Forecasted Supply ',
                xaxis_title='Date',
                yaxis_title='Supply Value (USD)',
                legend_title='Forecasts',
            )

            st.plotly_chart(supply_forecast_bar_fig)

            # ========== Forecasted Demand ========== 
            st.subheader(f"Forecasted Demand Bar Plot ")
            demand_forecast_bar_fig = go.Figure()

            demand_forecast_bar_fig.add_trace(go.Bar(
                x=forecast_df['Forecast Date'], 
                y=forecast_df['Demand Forecast (%)'],
                name='Demand Forecast (%)',
                marker=dict(color='green')
            ))

            demand_forecast_bar_fig.update_layout(
                title=f'Forecasted Demand ',
                xaxis_title='Date',
                yaxis_title='Demand Value (%)',
                legend_title='Forecasts',
            )

            st.plotly_chart(demand_forecast_bar_fig)

    except Exception as e:
            st.error(f"Error during processing: {e}")
    else:
        st.write("Please upload an Excel file to proceed.")
