import streamlit as st

st.title("Village Unit Analysis")

# import requests
# import time

# Define the base API endpoint  
api_url = "https://api.thevillagedallas.com/units/search"

# Initialize variables  
unit_array = []  # To store only the required fields from each unit  
page = 1             # Start from the first page  
limit = 10           # Adjust this if the API allows larger batch sizes

while True:  
    # Make the GET request with pagination parameters  
    response = requests.get(api_url, params={"page": page, "limit": limit})  
      
    if response.status_code != 200:  
        print(f"Failed to get data. Status code: {response.status_code}")  
        break  
      
    data = response.json()  # Parse the response as JSON  
      
    # Process each unit and extract the required fields  
    units = data.get("units", [])  
    for unit in units:  
        selected_unit = {  
            "rent": unit.get("rent"),  
            "building": unit.get("building"),  
            "unit_number": unit.get("unit_number"),  
            "availability": unit.get("availability"),  
            "property_name": unit.get("property", {}).get("name"),  # Safely get nested property name  
            "floorplan_name": unit.get("floorplan", {}).get("name"),  # Safely get nested floorplan name  
            "floorplan_media_url": unit.get("floorplan", {}).get("media", [{}])[0].get("url"),  # Get the first media's URL if available  
            "amenities": unit.get("amenities", [])  # Get amenities (default to empty list if missing)  
        }  
        unit_array.append(selected_unit)  # Append the selected data to the list  
      
    # Check if there are more units to fetch (depends on the API's response structure)  
    if len(units) < limit:  
        # Stop if fewer units are returned than the limit, indicating no more data  
        print(f"Loaded all units. Total count: {len(unit_array)}")  
        break  
      
    # Increment the page number for the next request  
    page += 1 

# Save the selected units data to JSON format (this is the data you need)  
json_output = json.dumps(unit_array, indent=4)

#print json_output
st.write(json_output)