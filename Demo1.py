import streamlit as st
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import plotly.graph_objects as go
import pyodbc  # To interact with MS SQL
import warnings
warnings.filterwarnings('ignore')


st.set_page_config(page_title="Supply and Demand Forecasting", page_icon="📈", layout="wide")
st.title('Supply and Demand Forecasting App')
#st.sidebar.image("E:\\Adarsh\\AI\\Recco_Demo\\Supply_Demand_Forecasting\\AllBatteryArrow-removebg-preview.png", use_column_width=True)

# Database connection details (adjust with your own credentials)
server = 'iallombardia.database.windows.net'  # e.g., 'localhost\\SQLEXPRESS'
database = 'IAL_Lombardia_DB'
username = 'dbuser2'
password = 'Welcome@12345'

def insert_to_db(forecast_df):
    try:
        # Establish connection to MS SQL
        conn = pyodbc.connect(f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}')
        cursor = conn.cursor()
        
        # Create table if not exists (adjust columns according to your needs)
        cursor.execute('''
        IF OBJECT_ID('ForecastResults', 'U') IS NULL
        CREATE TABLE ForecastResults (
            ForecastDate DATE,
            SupplyForecast FLOAT,
            DemandForecast FLOAT
        )
        ''')

        # Insert rows
        for _, row in forecast_df.iterrows():
            cursor.execute('''
                INSERT INTO ForecastResults (ForecastDate, SupplyForecast, DemandForecast)
                VALUES (?, ?, ?)
            ''', row['Forecast Date'], row['Supply Forecast (USD)'], row['Demand Forecast (%)'])

        conn.commit()  # Commit the transaction
        st.success("Predicted values have been stored in the database!")
    except Exception as e:
        st.error(f"Error storing data in the database: {e}")
    finally:
        conn.close()  # Close the connection

uploaded_file = st.file_uploader("Upload your Excel file for forecasting", type=["xlsx"])

if uploaded_file is not None:
    with st.spinner('Loading your data...'):
        try:
            df = pd.read_excel(uploaded_file, sheet_name='Sheet1')
            st.success('Your data loaded successfully!')
        except Exception as e:
            st.error(f"Error loading data: {e}")
    st.markdown("### Accuracy Metrics")
    try:
        df['Date of Extraction Process'] = pd.to_datetime(df['Date of Extraction Process'])

        # Prepare the data for Prophet for both supply and demand forecasts
        df_supply = df[['Date of Extraction Process', 'Cobalt Market Value (USD)']].rename(columns={'Date of Extraction Process': 'ds', 'Cobalt Market Value (USD)': 'y'})
        df_demand = df[['Date of Extraction Process', 'Recycled Content (%)']].rename(columns={'Date of Extraction Process': 'ds', 'Recycled Content (%)': 'y'})

        data_points = len(df_supply)
        print("value of df_supply")
        print(df_supply)
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