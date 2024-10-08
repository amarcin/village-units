import boto3
import awswrangler as wr
import pandas as pd
import requests
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
import plotly.express as px

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
    s3_path = f"s3://{BUCKET}/{PREFIX}/property-a/*/data.parquet"
    try:
        df = wr.s3.read_parquet(path=s3_path, boto3_session=boto3_session)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def get_properties(df):
    return sorted(df['Property'].unique())

def calculate_price_changes(df):
    df_sorted = df.sort_values(['Unit', 'date'])
    df_sorted['PriceChange'] = df_sorted.groupby('Unit')['Rent'].diff()
    return df_sorted

def plot_rent_history(df, property, time_range):
    df_filtered = df[df['Property'] == property]
    if time_range != 'MAX':
        end_date = df_filtered['date'].max()
        start_date = end_date - pd.Timedelta(time_range)
        df_filtered = df_filtered[df_filtered['date'] >= start_date]
    
    fig = px.line(df_filtered, x='date', y='Rent', color='Unit', title=f'Rent History for {property}')
    return fig

with histDataTab:
    st.header("Historical Data")
    
    data = load_historical_data()
    
    if data is not None:
        properties = get_properties(data)
        selected_property = st.selectbox("Select a property", properties)
        
        if st.button("Load Data"):
            filtered_data = data[data['Property'] == selected_property]
            
            st.subheader("Price Changes")
            price_changes = calculate_price_changes(filtered_data)
            st.dataframe(price_changes[['date', 'Unit', 'Rent', 'PriceChange']].dropna())
            
            st.subheader("Rent History")
            time_range = st.selectbox("Select time range", ['1mo', '3mo', '6mo', '1yr', 'MAX'])
            fig = plot_rent_history(filtered_data, selected_property, time_range)
            st.plotly_chart(fig)
            
            st.subheader("Specific Unit Price History")
            units = sorted(filtered_data['Unit'].unique())
            selected_unit = st.selectbox("Select a unit", units)
            unit_data = filtered_data[filtered_data['Unit'] == selected_unit]
            st.line_chart(unit_data.set_index('date')['Rent'])
    else:
        st.warning("Failed to load data. Please check your AWS credentials and permissions.")

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
                    "Floorplan": st.column_config.LinkColumn(
                        "Floorplan", display_text="View"
                    ),
                },
            )

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
        - Rent history visualization
        - Specific unit price history
        - Live data fetching
        - Property-based filtering

        ##  Upcoming features
        - Price drop notifications
        - Advanced filtering options
    """
    )