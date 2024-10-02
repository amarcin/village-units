import streamlit as st  
import pandas as pd  
import requests  
  
st.title("Village Unit Analysis")  
  
# Define the base API endpoint  
api_url = "https://api.thevillagedallas.com/units/search"  
  
# Function to fetch data from the API with caching  
@st.cache_data(show_spinner=True)  
def fetch_units():  
    unit_array = []  
    page = 1  
    limit = 10  
  
    while True:  
        response = requests.get(api_url, params={"page": page, "limit": limit})  
  
        if response.status_code != 200:  
            st.error(f"Failed to get data. Status code: {response.status_code}")  
            return None  
  
        data = response.json()  
        units = data.get("units", [])  
  
        for unit in units:  
            selected_unit = {  
                "Rent": unit.get("rent"),  
                "Building": unit.get("building"),  
                "Unit": unit.get("unit_number"),  
                "Available": unit.get("availability"),  
                "Property": unit.get("property", {}).get("name"),  
                "Size": unit.get("floorplan", {}).get("name"),  
                "Floorplan": unit.get("floorplan", {}).get("media", [{}])[0].get("url"),  
                "Amenities": ", ".join(unit.get("amenities", []))  
            }  
            unit_array.append(selected_unit)  
  
        if len(units) < limit:  
            break  
  
        page += 1  
  
    return unit_array  
  
# Automatically fetch data when the app loads  
unit_data = fetch_units()  
  
# Check if data is fetched successfully  
if unit_data:  
    # Convert the list of units to a DataFrame  
    df = pd.DataFrame(unit_data)  
  
    # Reset the index  
    df = df.reset_index(drop=True)  
  
    # Reorder the columns  
    df = df[["Unit", "Rent", "Building", "Available", "Property", "Size", "Floorplan", "Amenities"]]
  
    # Turn the amenities column into a list  
    df["Amenities"] = df["Amenities"].str.split(", ")  
  
    # Turn the floorplan to a clickable link  
    df["Floorplan"] = df["Floorplan"].apply(lambda x: f"[View]({x})" if x else "")  
  
    # Display the DataFrame in a sortable table  
    st.dataframe(df, hide_index=True)  # This will provide inline sorting and filtering  
else:  
    st.warning("No data available.")  