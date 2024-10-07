from datetime import datetime
from zoneinfo import ZoneInfo

import awswrangler as wr
import pandas as pd
import requests
import streamlit as st

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


with histDataTab:
    st.header("Historical Data")
    st.write("This is the Historical Data tab.")

    # Read the Parquet data from S3
    def load_data():
        s3_path = f"s3://{BUCKET}/{PREFIX}/properties/*/*/*/data.parquet"
        df = wr.s3.read_parquet(path=s3_path)
        return df

    # Load the data
    data = load_data()

    # Display the data in Streamlit
    st.write(data)


with liveDataTab:
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
