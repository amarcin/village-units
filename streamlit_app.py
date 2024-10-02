import streamlit as st  
import pandas as pd  
import requests  
  
st.title("Village Unit Analysis")  
  
# Define the base API endpoint  
api_url = "https://api.thevillagedallas.com/units/search"  
  
# Function to fetch data from the API  
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
                "rent": unit.get("rent"),  
                "building": unit.get("building"),  
                "unit_number": unit.get("unit_number"),  
                "availability": unit.get("availability"),  
                "property_name": unit.get("property", {}).get("name"),  
                "floorplan_name": unit.get("floorplan", {}).get("name"),  
                "floorplan_media_url": unit.get("floorplan", {}).get("media", [{}])[0].get("url"),  
                "amenities": ", ".join(unit.get("amenities", []))  # Join amenities list into a comma-separated string  
            }  
            unit_array.append(selected_unit)  
          
        # Check if there are no more units to fetch  
        if len(units) < limit:  
            break  
          
        # Increment page for next request  
        page += 1  
      
    return unit_array  
  
# Button to fetch data  
if st.button("Fetch Unit Data"):  
    unit_data = fetch_units()  
  
    if unit_data:  
        # Convert the list of units to a DataFrame  
        df = pd.DataFrame(unit_data)  
          
        # Display the DataFrame in a sortable table  
        st.dataframe(df)  # Streamlit's dataframe is sortable by default  