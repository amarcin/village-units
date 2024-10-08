import boto3
import awswrangler as wr
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from authenticate import (
    set_st_state_vars,
    button_login,
    button_logout,
    get_user_info,
    initialise_st_state_vars,
)

# Initialize session
initialise_st_state_vars()
set_st_state_vars()

if st.session_state["authenticated"]:
    button_logout()
else:
    button_login()

# Define the base API endpoint
url = "https://api.thevillagedallas.com/units/search"
BUCKET = "am-apartment-data"
PREFIX = "lambda-fetch"

if st.session_state["authenticated"]:
    # Your existing app code goes here
    st.set_page_config(layout="wide")
    st.title("Village Unit Analysis")
    
    # Function to fetch data from the API with caching
    @st.cache_data(show_spinner=True, ttl=21600)  # Cache for 6 hours
    def fetch_units():
        session = requests.Session()
        page = 1
        unit_array = []
        units = ["placeholder"]

        while units:
            r = session.get(url, params={"page": page})
            if r.status_code != 200:
                st.error(f"Failed to get data. Status code: {r.status_code}")
                return None
            data = r.json()
            units = data.get("units", [])
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

        return pd.DataFrame(unit_array), datetime.now(ZoneInfo("America/Chicago"))

    # Function to list all Parquet files in the S3 bucket
    @st.cache_data(ttl=3600, show_spinner=True)
    def list_parquet_files():
        boto3_session = boto3.Session()
        s3_path = f"s3://{BUCKET}/{PREFIX}/"
        try:
            objects = wr.s3.list_objects(path=s3_path, suffix='.parquet', boto3_session=boto3_session)
            return objects
        except Exception as e:
            st.error(f"Error listing Parquet files: {str(e)}")
            return []

    # Function to load historical data
    @st.cache_data(ttl=3600, show_spinner=True)
    def load_historical_data():
        boto3_session = boto3.Session()
        parquet_files = list_parquet_files()
        
        all_data = []
        for file in parquet_files:
            try:
                df = wr.s3.read_parquet(path=file, boto3_session=boto3_session)
                all_data.append(df)
            except Exception as e:
                st.warning(f"Error reading file {file}: {str(e)}")
        
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            # Convert fetch_datetime to datetime type
            combined_data['fetch_datetime'] = pd.to_datetime(combined_data['fetch_datetime'])
            return combined_data
        else:
            st.error("No data could be loaded.")
            return None

    # Main app layout
    histDataTab, liveDataTab, trackerTab, aboutTab = st.tabs(
        ["Historical Data", "Live Data", "Tracker", "About"]
    )

    # Historical Data Tab
    with histDataTab:
        st.header("Historical Data")

        # Load historical data
        if 'historical_data' not in st.session_state:
            st.session_state.historical_data = None

        if st.button("Load Historical Data") or st.session_state.historical_data is None:
            st.session_state.historical_data = load_historical_data()

        if st.session_state.historical_data is not None:
            # Property filter
            properties = st.session_state.historical_data['property_name'].unique()
            selected_property = st.selectbox("Select Property", properties)

            # Filter data based on selected property
            property_data = st.session_state.historical_data[st.session_state.historical_data['property_name'] == selected_property]

            # Display price changes
            st.subheader("Price Changes")
            price_changes = property_data.groupby('unit_number').agg({
                'rent': ['first', 'last', lambda x: x.diff().sum()]
            })
            price_changes.columns = ['Initial Rent', 'Current Rent', 'Total Change']
            price_changes['Percent Change'] = (price_changes['Total Change'] / price_changes['Initial Rent']) * 100
            st.dataframe(price_changes)

            # Rent history graph
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

            # Specific unit price history
            st.subheader("Specific Unit Price History")
            selected_unit = st.selectbox("Select Unit", property_data['unit_number'].unique())
            unit_data = property_data[property_data['unit_number'] == selected_unit]
            
            fig_unit = px.line(unit_data, x='fetch_datetime', y='rent', title=f"Price History - Unit {selected_unit}")
            st.plotly_chart(fig_unit)
        else:
            st.warning("No historical data available. Please load the data first.")

    # Live Data Tab
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

    # About Tab
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

else:
    st.warning("Please log in to access the application.")
