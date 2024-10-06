from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

# Define the base API endpoint
url = "https://api.thevillagedallas.com/units/search"

st.title("Village Unit Analysis")

dataTab, trackerTab, aboutTab = st.tabs(["Data", "Tracker", "About"])


# Function to fetch data from the API with caching
@st.cache_data(show_spinner=True, ttl=21600)  # Cache for 1 hour
def fetch_units():
    session = requests.Session()
    page = 1
    limit = 10
    unit_array = []

    units = ["placeholder"]  # Initialize with a non-empty list to enter the loop

    while units:
        r = session.get(url, params={"page": page, "limit": limit})

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


with dataTab:
    st.header("Today's Rates")

    # Fetch and display data
    df, last_updated = fetch_units()

    if df is not None and not df.empty:
        # Turn the amenities column into a list
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

        # Display the timestamp after the DataFrame
        col1, col2 = st.columns([5, 1])
        with col1:
            st.caption(
                f"Last updated: {last_updated.strftime('%B %d, %Y at %I:%M %p')}"
            )
        with col2:
            if st.button("Refresh", icon="🔄"):
                # Clear the cache and fetch the data again
                fetch_units.clear()
                st.rerun()
    else:
        st.warning("No data available.")

with aboutTab:
    st.markdown(
        """
        This app allows you to view and analyze unit data from the Village Dallas API. 
        The data is fetched from the API and stored in a DataFrame for easy manipulation and display. 
        The app is built using Streamlit, a popular Python library for creating data apps.

        ##  Upcoming features
        - Better filters
        - Price drop notifications
        - Price tracker over time
    """
    )

# with trackerTab:
#     st.header("Tracker")
