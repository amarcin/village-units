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
import os
from datetime import datetime, timedelta
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Village Data", page_icon=":bar_chart:", layout="wide")

set_auth_session()

API_URL = os.environ.get("API_URL")
BUCKET = os.environ.get("BUCKET")
PREFIX = os.environ.get("PREFIX")
AWS_REGION = os.environ.get("AWS_REGION")

def title():
    col1, col2 = st.columns([6, 1])
    col1.title("Village Data")
    with col2:
        if st.session_state.auth_state["authenticated"]:
            logout_button()
        else:
            login_button()


@st.cache_data(show_spinner=True, ttl=21600)
def fetch_units():
    session = requests.Session()
    page = 1
    unit_array = []

    while True:
        try:
            r = session.get(API_URL, params={"page": page})
            r.raise_for_status()
            units = r.json().get("units", [])
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

@st.cache_data(ttl=3600, show_spinner=True)
def load_historical_data(_boto3_session):
    s3_path = f"s3://{BUCKET}/{PREFIX}/"
    try:
        parquet_files = wr.s3.list_objects(path=s3_path, suffix='.parquet', boto3_session=_boto3_session)
        all_data = pd.concat([wr.s3.read_parquet(path=file, boto3_session=_boto3_session) for file in parquet_files], ignore_index=True)
        all_data['fetch_datetime'] = pd.to_datetime(all_data['fetch_datetime'])
        return all_data
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return None

def display_historical_data(historical_data):
    properties = historical_data['property_name'].unique()
    property_filter = st.selectbox("Select Property", properties)
    property_data = historical_data[historical_data['property_name'] == property_filter]

    st.subheader("Rent Summary")
    property_summary = property_data.groupby('unit_number').agg({
        'rent': ['last', 'mean', 'min', 'max']
    })
    property_summary.columns = ['Current', 'Avg', 'Min', 'Max']
    st.dataframe(property_summary)

    st.subheader("Price Changes")
    price_changes = property_data.groupby('unit_number').agg({
        'rent': ['first', 'last', lambda x: x.diff().sum()]
    })
    price_changes.columns = ['Initial Rent', 'Current Rent', 'Total Change']
    price_changes['Percent Change'] = (price_changes['Total Change'] / price_changes['Initial Rent']) * 100
    st.dataframe(price_changes)

    st.subheader("Rent History")
    time_periods = {"1 Month": 30, "3 Months": 90, "6 Months": 180, "1 Year": 365, "Max": None}
    selected_period = st.selectbox("Select Time Period", list(time_periods.keys()))

    # Ensure end_date is timezone-aware
    end_date = datetime.now(pytz.UTC)
    if time_periods[selected_period]:
        start_date = end_date - timedelta(days=time_periods[selected_period])
    else:
        start_date = property_data['fetch_datetime'].min().replace(tzinfo=pytz.UTC)

    # Ensure property_data['fetch_datetime'] is timezone-aware
    if property_data['fetch_datetime'].dt.tz is None:
        property_data['fetch_datetime'] = property_data['fetch_datetime'].dt.tz_localize(pytz.UTC)

    filtered_data = property_data[(property_data['fetch_datetime'] >= start_date) & (property_data['fetch_datetime'] <= end_date)]

    fig = px.line(filtered_data, x='fetch_datetime', y='rent', color='unit_number', title=f"Rent History - {property_filter}")
    st.plotly_chart(fig)

    st.subheader("Specific Unit Price History")
    selected_unit = st.selectbox("Select Unit", property_data['unit_number'].unique())
    unit_data = property_data[property_data['unit_number'] == selected_unit]

    fig_unit = px.line(unit_data, x='fetch_datetime', y='rent', title=f"Price History - Unit {selected_unit}")
    st.plotly_chart(fig_unit)

def main():
    if not st.session_state.auth_state["authenticated"]:
        st.warning("Please log in to access the application.")
        return

    credentials = st.session_state.auth_state["aws_credentials"]
    if not credentials:
        st.error("AWS credentials not available. Please log in again.")
        return

    boto3_session = boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretKey'],
        aws_session_token=credentials['SessionToken'],
        region_name=AWS_REGION
    )
  
    trackerTab, liveDataTab, aboutTab = st.tabs(["Historical Data", "Live Data", "About"])

    with trackerTab:
        st.header("Price Tracker")
        if 'historical_data' not in st.session_state:
            st.session_state.historical_data = load_historical_data(boto3_session)
      
        if st.session_state.historical_data is not None:
            display_historical_data(st.session_state.historical_data)
        else:
            st.warning("No historical data available.")

    with liveDataTab:
        st.header("Today's Rates")
        if st.button("Fetch Live Data"):
            df, last_updated = fetch_units()
            if df is not None and not df.empty:
                df["Amenities"] = df["Amenities"].str.split(", ")
                st.dataframe(
                    df,
                    hide_index=True,
                    column_config={"Floorplan": st.column_config.LinkColumn("Floorplan", display_text="View")},
                )
                st.caption(f"Last updated: {last_updated.strftime('%B %d, %Y at %I:%M %p')}")
            else:
                st.warning("No data available.")

    with aboutTab:
        st.markdown("""
        ## Upcoming features
        - Price drop notifications
        - Advanced filtering options
        - New units added section
        - Price changes by number of bedrooms
        """)

title()
main()