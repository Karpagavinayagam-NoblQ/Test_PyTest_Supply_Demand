import streamlit as st
import pandas as pd
import time
from catboost import CatBoostRegressor, Pool, cv
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import plotly.graph_objects as go

st.set_page_config(page_title="Supply and Demand Forecasting with CatBoost", page_icon="📈", layout="wide")
st.title('Supply and Demand Forecasting ')

sample_csv_path = "E://Adarsh//AI//Recco_Demo//Supply_Demand_Forecasting//Supply_Demand_Forecasting.csv"

use_sample_data = st.checkbox("Use Sample Data")

if use_sample_data:
    with st.spinner('Loading sample data...'):
        time.sleep(2)
        sample_data = pd.read_csv(sample_csv_path)
        st.success('Sample data loaded successfully!')
    st.write("Here is a preview of the sample CSV:")
    st.dataframe(sample_data)
    
    data = sample_data
else:
    uploaded_file = st.file_uploader("Upload your CSV file for forecasting", type=["csv"])
    if uploaded_file is not None:
        with st.spinner('Loading your data...'):
            time.sleep(2)
            data = pd.read_csv(uploaded_file)
        st.success('Your data loaded successfully!')

if 'data' in locals():
    st.markdown("### Data Preview...")
    data_cleaned = data.drop(columns=['Unnamed: 11'], errors='ignore')
    data_cleaned = data_cleaned.dropna(subset=['Date'])

    data_cleaned['Date'] = pd.to_datetime(data_cleaned['Date'], format='%d-%m-%Y')

    data_cleaned.set_index('Date', inplace=True)

    st.write("Here is a preview of your data:")
    st.dataframe(data_cleaned.head())
    forecast_periods = st.slider('Select the number of periods to forecast:', min_value=1, max_value=36, value=12)

    # Split features and target for both supply and demand forecasting
    supply_target = data_cleaned['Debit EUR']
    demand_target = data_cleaned['Credit EUR']
    exogenous_features = data_cleaned[['Vendor Quality History', 'Vendor Consistency', 'Processing Efficiency (%)']]

    # Train-test split for metrics evaluation
    X_train_supply, X_test_supply, y_train_supply, y_test_supply = train_test_split(exogenous_features, supply_target, test_size=0.2, shuffle=False)
    X_train_demand, X_test_demand, y_train_demand, y_test_demand = train_test_split(exogenous_features, demand_target, test_size=0.2, shuffle=False)

    # Define cross-validation parameters
    cv_folds = st.number_input("Select number of CV folds:", min_value=2, max_value=10, value=5, step=1)

    # ========== CatBoost Regressor for Supply ========== 
    st.subheader('Cross-Validation and Training for Supply Forecasting...')

    supply_params = {
        'iterations': 500,
        'depth': 6,
        'learning_rate': 0.1,
        'loss_function': 'RMSE',
        'verbose': 0  # Silent training
    }

    supply_pool = Pool(data=X_train_supply, label=y_train_supply)

    # Perform cross-validation
    supply_cv_results = cv(
        params=supply_params,
        pool=supply_pool,
        fold_count=cv_folds,
        partition_random_seed=42,
        shuffle=False,
        stratified=False,
        verbose=False,
        plot=False
    )

    # Debug: Check available keys in the cross-validation results
    st.write("Cross-validation results for Supply Model:")
    st.write(supply_cv_results)

    # Train final model on entire training data for supply forecasting
    supply_model = CatBoostRegressor(**supply_params)
    supply_model.fit(X_train_supply, y_train_supply, eval_set=(X_test_supply, y_test_supply), use_best_model=True)

    # Forecast and calculate accuracy metrics for supply forecast
    supply_forecast = supply_model.predict(X_test_supply)
    supply_rmse = mean_squared_error(y_test_supply, supply_forecast, squared=False)
    supply_mae = mean_absolute_error(y_test_supply, supply_forecast)
    supply_r2 = r2_score(y_test_supply, supply_forecast)

    st.write(f"**Supply Forecast RMSE:** {supply_rmse:.2f}")
    st.write(f"**Supply Forecast MAE:** {supply_mae:.2f}")
    st.write(f"**Supply Forecast R²:** {supply_r2:.2f}")

    # ========== CatBoost Regressor for Demand ========== 
    st.subheader('Cross-Validation and Training for Demand Forecasting...')

    demand_params = {
        'iterations': 500,
        'depth': 6,
        'learning_rate': 0.1,
        'loss_function': 'RMSE',
        'verbose': 0  # Silent training
    }

    # Prepare Pool for cross-validation
    demand_pool = Pool(data=X_train_demand, label=y_train_demand)

    # Perform cross-validation
    demand_cv_results = cv(
        params=demand_params,
        pool=demand_pool,
        fold_count=cv_folds,
        partition_random_seed=42,
        shuffle=False,
        stratified=False,
        verbose=False,
        plot=False
    )

    # Debug: Check available keys in the cross-validation results
    st.write("Cross-validation results for Demand Model:")
    st.write(demand_cv_results)

    # Train final model on entire training data for demand forecasting
    demand_model = CatBoostRegressor(**demand_params)
    demand_model.fit(X_train_demand, y_train_demand, eval_set=(X_test_demand, y_test_demand), use_best_model=True)

    # Forecast and calculate accuracy metrics for demand forecast
    demand_forecast = demand_model.predict(X_test_demand)
    demand_rmse = mean_squared_error(y_test_demand, demand_forecast, squared=False)
    demand_mae = mean_absolute_error(y_test_demand, demand_forecast)
    demand_r2 = r2_score(y_test_demand, demand_forecast)

    st.write(f"**Demand Forecast RMSE:** {demand_rmse:.2f}")
    st.write(f"**Demand Forecast MAE:** {demand_mae:.2f}")
    st.write(f"**Demand Forecast R²:** {demand_r2:.2f}")

    # Prepare forecast data for plotting
    forecast_dates = pd.date_range(start=data_cleaned.index[-len(X_test_supply)], periods=forecast_periods, freq='D')

    forecast_df = pd.DataFrame({
        'Forecast Date': forecast_dates,
        'Supply Forecast': supply_forecast[:forecast_periods],
        'Demand Forecast': demand_forecast[:forecast_periods]
    })

    st.subheader("Forecasted Values Table")
    st.dataframe(forecast_df)

    st.download_button(
        label="Download Forecast Data",
        data=forecast_df.to_csv(index=False),
        file_name="forecast_values_catboost.csv",
        mime="text/csv"
    )

    # Visualization
    if st.button("Visualize Forecasting Graphs"):
        with st.spinner('Generating visualizations...'):
            time.sleep(1)

            # Supply Forecasting Plot
            st.subheader('Supply Forecasting')
            supply_fig = go.Figure()

            supply_fig.add_trace(go.Scatter(
                x=data_cleaned.index[:len(X_train_supply)], y=y_train_supply,
                mode='lines+markers', name='Training Data',
                line=dict(color='lightblue'), marker=dict(symbol='circle')
            ))
            supply_fig.add_trace(go.Scatter(
                x=data_cleaned.index[len(X_train_supply):], y=y_test_supply,
                mode='lines+markers', name='Actual Supply (Test Data)',
                line=dict(color='blue'), marker=dict(symbol='square')
            ))
            supply_fig.add_trace(go.Scatter(
                x=forecast_dates, y=supply_forecast[:forecast_periods],
                mode='lines+markers', name='Forecasted Supply',
                line=dict(color='red', dash='dash'), marker=dict(symbol='x')
            ))
            supply_fig.update_layout(
                title='Supply Forecasting',
                xaxis_title='Date',
                yaxis_title='Debit EUR (Supply)',
                legend_title='Legend'
            )
            st.plotly_chart(supply_fig)

            # Demand Forecasting Plot
            st.subheader('Demand Forecasting')
            demand_fig = go.Figure()

            demand_fig.add_trace(go.Scatter(
                x=data_cleaned.index[:len(X_train_demand)], y=y_train_demand,
                mode='lines+markers', name='Training Data',
                line=dict(color='lightgreen'), marker=dict(symbol='circle')
            ))
            demand_fig.add_trace(go.Scatter(
                x=data_cleaned.index[len(X_train_demand):], y=y_test_demand,
                mode='lines+markers', name='Actual Demand (Test Data)',
                line=dict(color='green'), marker=dict(symbol='square')
            ))
            demand_fig.add_trace(go.Scatter(
                x=forecast_dates, y=demand_forecast[:forecast_periods],
                mode='lines+markers', name='Forecasted Demand',
                line=dict(color='red', dash='dash'), marker=dict(symbol='x')
            ))
            demand_fig.update_layout(
                title='Demand Forecasting',
                xaxis_title='Date',
                yaxis_title='Credit EUR (Demand)',
                legend_title='Legend'
            )
            st.plotly_chart(demand_fig)
    else:
        st.error("Not enough data for forecasting.")
else:
    st.write("Please upload a CSV file to proceed or select to use the sample data.")
st.sidebar.image("https://cdn1.iconfinder.com/data/icons/market-research-astute-vol-2/512/Quantitative_Research-512.png", use_column_width=True)
