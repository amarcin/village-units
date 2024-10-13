import boto3
import awswrangler as wr
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from authenticate import set_auth_session, login_button, logout_button
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="Village Unit Analysis",
    page_icon=":bar_chart:",
    layout="wide"
)

# Initialize the session
set_auth_session()

if st.session_state.authenticated:
    logout_button()
else:
    login_button()

# Define constants
URL = "https://api.thevillagedallas.com/units/search"
BUCKET = "am-apartment-data"
PREFIX = "lambda-fetch"
AWS_REGION = "us-east-1"  # Replace with your AWS region

@st.cache_data(show_spinner=True, ttl=21600)
def fetch_units():
    """Fetch units data from API."""
    session = requests.Session()
    page = 1
    unit_array = []

    while True:
        try:
            r = session.get(URL, params={"page": page})
            r.raise_for_status()
            data = r.json()
            units = data.get("units", [])
            if not units:
                break
            unit_array.extend([
                {
                    "Unit": unit.get("unit_number"),
                    "Rent": unit.get("rent"),
                    "Property": unit.get("property", {}).get("name"),
                    "Beds": unit.get("floorplan", {}).get("beds"),
                    "Sqft": unit.get("floorplan", {}).get("sqft"),
                    "Floorplan": unit.get("floorplan", {}).get("media", [{}])[0].get("url"),
                    "Available": unit.get("availability"),
                    "Building": unit.get("building"),
                    "Amenities": ", ".join(unit.get("amenities", [])),
                }
                for unit in units
            ])
            page += 1
        except requests.RequestException as e:
            st.error(f"Failed to fetch data: {e}")
            return None, None

    return pd.DataFrame(unit_array), datetime.now(ZoneInfo("America/Chicago"))

def list_parquet_files(_boto3_session):
    """List all Parquet files in S3 bucket."""
    s3_path = f"s3://{BUCKET}/{PREFIX}/"
    try:
        return wr.s3.list_objects(path=s3_path, suffix='.parquet', boto3_session=_boto3_session)
    except Exception as e:
        logger.error(f"Error listing Parquet files: {e}")
        raise

@st.cache_data(ttl=3600, show_spinner=True)
def load_historical_data(_boto3_session):
    """Load historical data from S3."""
    try:
        parquet_files = list_parquet_files(_boto3_session)
        
        all_data = []
        for file in parquet_files:
            try:
                df = wr.s3.read_parquet(path=file, boto3_session=_boto3_session)
                all_data.append(df)
            except Exception as e:
                logger.warning(f"Error reading file {file}: {e}")
        
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            combined_data['fetch_datetime'] = pd.to_datetime(combined_data['fetch_datetime'])
            return combined_data
        else:
            logger.error("No data could be loaded.")
            return None
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        raise

def main():
    """Main application logic."""
    st.title("Village Unit Analysis")
    
    # Create AWS session
    if st.session_state.authenticated and 'aws_credentials' in st.session_state:
        credentials = st.session_state.aws_credentials
        boto3_session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=AWS_REGION
        )
        logger.info("AWS session created successfully")
    else:
        st.error("AWS credentials not available. Please log in again.")
        return
    
    histDataTab, liveDataTab, trackerTab, aboutTab = st.tabs(
        ["Historical Data", "Live Data", "Tracker", "About"]
    )

    with histDataTab:
        st.header("Historical Data")
        if 'historical_data' not in st.session_state:
            st.session_state.historical_data = None

        if st.button("Load Historical Data") or st.session_state.historical_data is None:
            try:
                st.session_state.historical_data = load_historical_data(boto3_session)
                if st.session_state.historical_data is None:
                    st.warning("No historical data available.")
                else:
                    st.success("Historical data loaded successfully.")
            except Exception as e:
                st.error(f"Failed to load historical data: {e}")

        if st.session_state.historical_data is not None:
            properties = st.session_state.historical_data['property_name'].unique()
            selected_property = st.selectbox("Select Property", properties)
            property_data = st.session_state.historical_data[st.session_state.historical_data['property_name'] == selected_property]

            st.subheader("Price Changes")
            price_changes = property_data.groupby('unit_number').agg({
                'rent': ['first', 'last', lambda x: x.diff().sum()]
            })
            price_changes.columns = ['Initial Rent', 'Current Rent', 'Total Change']
            price_changes['Percent Change'] = (price_changes['Total Change'] / price_changes['Initial Rent']) * 100
            st.dataframe(price_changes)

            st.subheader("Rent History")
            time_periods = {
                "1 Month": 30,
                "3 Months": 90,
                "6 Months": 180,
                "1 Year": 365,
                "Max": None
            }
            selected_period = st.selectbox("Select Time Period", list(time_periods.keys()))
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_periods[selected_period]) if time_periods[selected_period] else property_data['fetch_datetime'].min()

            filtered_data = property_data[(property_data['fetch_datetime'] >= start_date) & (property_data['fetch_datetime'] <= end_date)]
            
            fig = px.line(filtered_data, x='fetch_datetime', y='rent', color='unit_number', title=f"Rent History - {selected_property}")
            st.plotly_chart(fig)

            st.subheader("Specific Unit Price History")
            selected_unit = st.selectbox("Select Unit", property_data['unit_number'].unique())
            unit_data = property_data[property_data['unit_number'] == selected_unit]
            
            fig_unit = px.line(unit_data, x='fetch_datetime', y='rent', title=f"Price History - Unit {selected_unit}")
            st.plotly_chart(fig_unit)
        else:
            st.warning("No historical data available. Please load the data first.")

    with liveDataTab:
        st.header("Today's Rates")
        if st.button("Fetch Live Data"):
            df, last_updated = fetch_units()
            if df is not None and not df.empty:
                df["Amenities"] = df["Amenities"].str.split(", ")
                st.dataframe(
                    df,
                    hide_index=True,
                    column_config={
                        "Floorplan": st.column_config.LinkColumn("Floorplan", display_text="View"),
                    },
                )
                st.caption(f"Last updated: {last_updated.strftime('%B %d, %Y at %I:%M %p')}")
            else:
                st.warning("No data available.")

    with aboutTab:
        st.markdown(
            """
            This app allows you to view and analyze unit data from the Village Dallas API. 
            The data is fetched from the API and stored in a DataFrame for easy manipulation and display. 
            The app is built using Streamlit, a popular Python library for creating data apps.

            ## Features
            - Historical data analysis
            - Live data fetching
            - Price change tracking
            - Rent history visualization
            - Specific unit price history

            ## Upcoming features
            - Price drop notifications
            - Advanced filtering options
            - "New units added" section
            """
        )

if st.session_state.authenticated:
    main()
else:
    st.warning("Please log in to access the application.")