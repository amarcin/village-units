import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# Define the base API endpoint
url = "https://api.thevillagedallas.com/units/search"

st.title("Village Unit Analysis")

dataTab, trackerTab, aboutTab = st.tabs(["Data", "Tracker", "About"])

# Function to fetch data from the API with caching
@st.cache_data(show_spinner=True)
def fetch_units():
    session = requests.Session()
    page = 1
    limit = 10
    unit_array = []
    
    units = ['placeholder']  # Initialize with a non-empty list to enter the loop

    while units:
        r = session.get(url, params={"page": page, "limit": limit})

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
                "Size": unit.get("floorplan", {}).get("name"),
                "Available": unit.get("availability"),
                "Floorplan": unit.get("floorplan", {}).get("media", [{}])[0].get("url"),
                "Building": unit.get("building"),
                "Amenities": ", ".join(unit.get("amenities", []))
            } for unit in units
        ])

        page += 1

    return pd.DataFrame(unit_array)

with dataTab:
    st.header("Today's Rates")
    st.caption(f"Last updated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")

    # Fetch and display data
    df = fetch_units()

    if df is not None and not df.empty:
        # Turn the amenities column into a list
        df["Amenities"] = df["Amenities"].str.split(", ")

        st.dataframe(df, hide_index=True,
            column_config={
                "Floorplan": st.column_config.LinkColumn("Floorplan", display_text="View"),
            }
        )
    else:
        st.warning("No data available.")

    # Add a refresh button at the bottom of the chart
    if st.button("Refresh", icon="🔄"):
        # Clear the cache and fetch the data again
        fetch_units.clear()
        st.rerun()

with aboutTab:
    st.markdown("""
        # About

        This app allows you to view and analyze unit data from the Village Dallas API. 
        The data is fetched from the API and stored in a DataFrame for easy manipulation and display. 
        The app is built using Streamlit, a popular Python library for creating data apps.

        ##  Upcoming features
        - Better sorts and filters
        - Price drop notifications
        - Price tracker
    """)

with trackerTab:
    st.header("Tracker")