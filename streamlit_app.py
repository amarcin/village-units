import streamlit as st  
import pandas as pd  
import requests  

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

    return unit_array  # Return the list directly

# Function to display the data
def display_data(container):
    unit_data = fetch_units()

    if unit_data:
        # Convert the list of units to a DataFrame
        df = pd.DataFrame(unit_data)

        # Reset the index
        df = df.reset_index(drop=True)

        # Turn the amenities column into a list
        df["Amenities"] = df["Amenities"].str.split(", ")

        # Clear the container and display the new dataframe
        container.dataframe(df, hide_index=True,
            column_config={
                "Floorplan": st.column_config.LinkColumn("Floorplan", display_text="View"),
            }
        )
    else:
        container.warning("No data available.")

# Display the data when the app first loads
with dataTab:
    st.header("Current Data")
  
    # Create the container outside the function
    data_container = st.empty()
  
    display_data(data_container)

    # Add a refresh button at the bottom of the chart
    if st.button("Refresh", icon="🔄"):
        # Clear the cache and fetch the data again
        fetch_units.clear()
        display_data(data_container)

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


# Storage brainstorm: SQL() PostgreSQL, DynamoDB, Aurora (serverless SQL), S3, 

