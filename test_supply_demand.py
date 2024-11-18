import pytest
import pandas as pd
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.metrics import root_mean_squared_error  # Updated import
import logging

# Configure logging
logger = logging.getLogger('ProphetLogger')
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('prophet_log.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# Function to create data
def create_data():
    logger.info("Creating data")
    df_supply = {
        'ds': ['01-12-2024', '12-12-2024', '15-12-2024', '18-12-2024', '21-12-2024', '22-12-2024', '25-12-2024', '26-12-2024'],
        'y': [71835.71, 86449.29, 70005.61, 86409.22, 81835.71, 86949.29, 51835.71, 87449.29]
    }
    df_supply = pd.DataFrame(df_supply)
    df_supply['ds'] = pd.to_datetime(df_supply['ds'], format='%d-%m-%Y')

    df_demand = {
        'ds': ['03-12-2024', '08-12-2024', '10-12-2024', '12-12-2024', '16-12-2024', '17-12-2024', '19-12-2024', '21-12-2024'],
        'y': [93.12, 97.43, 89.89, 87.67, 94.34, 88.45, 90.30, 97.23]
    }
    df_demand = pd.DataFrame(df_demand)
    df_demand['ds'] = pd.to_datetime(df_demand['ds'], format='%d-%m-%Y')

    logger.info("Data creation complete")
    return df_supply, df_demand


# Function to fit the Prophet models
def fit_prophet_models(df_supply, df_demand):
    logger.info("Fitting Prophet models")
    supply_model = Prophet(yearly_seasonality=True, weekly_seasonality=True, seasonality_mode='multiplicative')
    supply_model.fit(df_supply)

    demand_model = Prophet(yearly_seasonality=True, weekly_seasonality=True, seasonality_mode='multiplicative')
    demand_model.fit(df_demand)

    logger.info("Prophet models fitting complete")
    return supply_model, demand_model


# Function to make predictions
def make_predictions(supply_model, demand_model, forecast_horizon):
    logger.info(f"Making predictions for forecast horizon: {forecast_horizon}")
    future_supply = supply_model.make_future_dataframe(periods=forecast_horizon)
    supply_forecast = supply_model.predict(future_supply)

    future_demand = demand_model.make_future_dataframe(periods=forecast_horizon)
    demand_forecast = demand_model.predict(future_demand)

    logger.info("Predictions complete")
    return supply_forecast, demand_forecast


# Function to calculate metrics
def calculate_metrics(merged_supply, merged_demand):
    logger.info("Calculating metrics")
    supply_mae = mean_absolute_error(merged_supply['y'], merged_supply['yhat'])
    supply_rmse = root_mean_squared_error(merged_supply['y'], merged_supply['yhat'])  # Updated RMSE calculation
    supply_r2 = r2_score(merged_supply['y'], merged_supply['yhat'])

    demand_mae = mean_absolute_error(merged_demand['y'], merged_demand['yhat'])
    demand_rmse = root_mean_squared_error(merged_demand['y'], merged_demand['yhat'])  # Updated RMSE calculation
    demand_r2 = r2_score(merged_demand['y'], merged_demand['yhat'])

    logger.info("Metrics calculation complete")
    return supply_mae, supply_rmse, supply_r2, demand_mae, demand_rmse, demand_r2


# Test case for checking the creation of data
def test_create_data():
    logger.info("Testing data creation")
    df_supply, df_demand = create_data()
    assert df_supply.shape == (8, 2), "Supply data frame shape mismatch"
    assert df_demand.shape == (8, 2), "Demand data frame shape mismatch"
    logger.info("Data creation test passed")


# Test case for checking the Prophet model fitting
def test_fit_prophet_models():
    logger.info("Testing Prophet model fitting")
    df_supply, df_demand = create_data()
    supply_model, demand_model = fit_prophet_models(df_supply, df_demand)

    assert supply_model is not None, "Supply model fitting failed"
    assert demand_model is not None, "Demand model fitting failed"
    logger.info("Prophet model fitting test passed")


# Test case for checking the forecasting and metrics calculation
def test_make_predictions_and_metrics():
    logger.info("Testing forecasting and metrics calculation")
    df_supply, df_demand = create_data()
    supply_model, demand_model = fit_prophet_models(df_supply, df_demand)

    forecast_horizon = min(365, int(len(df_supply) * 0.7))
    supply_forecast, demand_forecast = make_predictions(supply_model, demand_model, forecast_horizon)

    merged_supply = pd.merge(df_supply, supply_forecast[['ds', 'yhat']], on='ds', how='left')
    merged_demand = pd.merge(df_demand, demand_forecast[['ds', 'yhat']], on='ds', how='left')

    supply_mae, supply_rmse, supply_r2, demand_mae, demand_rmse, demand_r2 = calculate_metrics(merged_supply, merged_demand)

    assert 0 <= supply_mae <= 1, f"Supply MAE out of range: {supply_mae}"
    assert 0 <= supply_rmse <= 1, f"Supply RMSE out of range: {supply_rmse}"
    assert 0 <= supply_r2 <= 1, f"Supply R2 out of range: {supply_r2}"
    assert 0 <= demand_mae <= 1, f"Demand MAE out of range: {demand_mae}"
    assert 0 <= demand_rmse <= 1, f"Demand RMSE out of range: {demand_rmse}"
    assert 0 <= demand_r2 <= 1, f"Demand R2 out of range: {demand_r2}"
    logger.info("Forecasting and metrics calculation test passed")


# Run tests with pytest
if __name__ == "__main__":
    pytest.main()