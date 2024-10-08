import boto3
import awswrangler as wr
import pandas as pd
import requests
import streamlit as st
import plotly.express as px
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Define the base API endpoint
url = "https://api.thevillagedallas.com/units/search"
BUCKET = "am-apartment-data"
PREFIX = "lambda-fetch"

st.title("Village Unit Analysis")

histDataTab, liveDataTab, trackerTab, aboutTab = st.tabs(
    ["Historical Data", "Live Data", "Tracker", "About"]
)

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

        unit_array.extend(
            [
                {
                    "Unit": unit.get("unit_number"),
                    "Rent": unit.get("rent"),
                    "Property": unit.get("property", {}).get("name"),
                    "Beds": unit.get("floorplan", {}).get("beds"),
                    "Sqft": unit.get("floorplan", {}).get("sqft"),
                    "Floorplan": unit.get("floorplan", {})
                    .get("media", [{}])[0]
                    .get("url"),
                    "Available": unit.get("availability"),
                    "Building": unit.get("building"),
                    "Amenities": ", ".join(unit.get("amenities", [])),
                }
                for unit in units
            ]
        )

        page += 1

    return pd.DataFrame(unit_array), datetime.now(ZoneInfo("America/Chicago"))

@st.cache_data(ttl=3600, show_spinner=True)
def load_historical_data():
    boto3_session = boto3.Session()
    s3_path = f"s3://{BUCKET}/{PREFIX}/properties/*/*/*/data.parquet"
    try:
        df = wr.s3.read_parquet(path=s3_path, boto3_session=boto3_session)
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def analyze_price_changes(df):
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Unit', 'Date'])
    df['PreviousRent'] = df.groupby('Unit')['Rent'].shift(1)
    df['PriceChange'] = df['Rent'] - df['PreviousRent']
    df['PercentageChange'] = (df['PriceChange'] / df['PreviousRent']) * 100
    return df[df['PriceChange'] != 0].dropna()

def plot_rent_history(df, time_range):
    end_date = df['Date'].max()
    if time_range == '1mo':
        start_date = end_date - timedelta(days=30)
    elif time_range == '3mo':
        start_date = end_date - timedelta(days=90)
    elif time_range == '6mo':
        start_date = end_date - timedelta(days=180)
    elif time_range == '1yr':
        start_date = end_date - timedelta(days=365)
    else:  # MAX
        start_date = df['Date'].min()

    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    fig = px.line(filtered_df, x='Date', y='Rent', color='Unit', title=f'Rent History - {time_range}')
    return fig

with histDataTab:
    st.header("Historical Data")

    if st.button("Load Historical Data"):
        data = load_historical_data()

        if data is not None:
            # Property filter
            properties = sorted(data['Property'].unique())
            selected_property = st.selectbox("Select Property", properties)
            filtered_data = data[data['Property'] == selected_property]

            # Analyze price changes
            price_changes = analyze_price_changes(filtered_data)
            st.subheader("Price Changes")
            st.dataframe(price_changes[['Date', 'Unit', 'Rent', 'PreviousRent', 'PriceChange', 'PercentageChange']])

            # Rent history graph
            st.subheader("Rent History")
            time_range = st.selectbox("Select Time Range", ['1mo', '3mo', '6mo', '1yr', 'MAX'])
            fig = plot_rent_history(filtered_data, time_range)
            st.plotly_chart(fig)

            # Specific unit's price history
            st.subheader("Unit Price History")
            units = sorted(filtered_data['Unit'].unique())
            selected_unit = st.selectbox("Select Unit", units)
            unit_data = filtered_data[filtered_data['Unit'] == selected_unit]
            unit_fig = px.line(unit_data, x='Date', y='Rent', title=f'Price History for Unit {selected_unit}')
            st.plotly_chart(unit_fig)
        else:
            st.warning("Failed to load data. Please check your AWS credentials and permissions.")

with liveDataTab:
    st.header("Today's Rates")

    if st.button("Fetch Live Data"):
        df, last_updated = fetch_units()

        if df is not None and not df.empty:
            # Property filter
            properties = sorted(df['Property'].unique())
            selected_property = st.selectbox("Select Property", properties)
            filtered_df = df[df['Property'] == selected_property]

            # Turn the amenities column into a list
            filtered_df["Amenities"] = filtered_df["Amenities"].str.split(", ")

            st.dataframe(
                filtered_df,
                hide_index=True,
                column_config={
                    "Floorplan": st.column_config.LinkColumn(
                        "Floorplan", display_text="View"
                    ),
                },
            )

            # Display the timestamp after the DataFrame
            st.caption(
                f"Last updated: {last_updated.strftime('%B %d, %Y at %I:%M %p')}"
            )
        else:
            st.warning("No data available.")

with aboutTab:
    st.markdown(
        """
        This app allows you to view and analyze unit data from the Village Dallas API. 
        The data is fetched from the API and stored in a DataFrame for easy manipulation and display. 
        The app is built using Streamlit, a popular Python library for creating data apps.

        ##  Features
        - Historical data analysis with price change tracking
        - Rent history graphs with customizable time ranges
        - Specific unit price history visualization
        - Live data fetching with property filtering
        - Easy-to-use interface with data refresh options

        ##  Upcoming features
        - Better filters
        - Price drop notifications
        - Enhanced data visualization options
    """
    )

# Tracker tab can be implemented in the future if needed
# with trackerTab:
#     st.header("Tracker")