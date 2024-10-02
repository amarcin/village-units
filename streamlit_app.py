import streamlit as st  
import pandas as pd  
import requests  
  
st.title("Village Unit Analysis")  
  
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
                "Unit #": unit.get("unit_number"),  
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
  
# Sidebar filters  
st.sidebar.header("Filters")  
min_rent = st.sidebar.number_input("Min Rent", min_value=0, value=1000)  
max_rent = st.sidebar.number_input("Max Rent", min_value=0, value=3000)  
property_filter = st.sidebar.text_input("Filter by Property Name", "")  
  
# Button to fetch data  
if st.button("Fetch Unit Data"):  
    # Fetch data and store it in session state  
    unit_data = fetch_units()  
    if unit_data:  
        st.session_state["unit_data"] = unit_data  
  
# Check if data is already fetched and stored in session state  
if "unit_data" in st.session_state:  
    unit_data = st.session_state["unit_data"]  
      
    # Convert the list of units to a DataFrame  
    df = pd.DataFrame(unit_data)  
  
    # Apply filters  
    df = df[(df["Rent"] >= min_rent) & (df["Rent"] <= max_rent)]  
    if property_filter:  
        df = df[df["Property"].str.contains(property_filter, case=False, na=False)]  
  
    if df.empty:  
        st.warning("No units match the selected criteria.")  
    else:  
        # Reset the index  
        df = df.reset_index(drop=True)  
  
        # Reorder the columns  
        df = df[["Rent", "Building", "Available", "Property", "Size", "Floorplan", "Amenities"]]  
  
        # Turn the amenities column into a list  
        df["Amenities"] = df["Amenities"].str.split(", ")  
  
        # Turn the floorplan to a clickable link  
        df["Floorplan"] = df["Floorplan"].apply(lambda x: f"[View]({x})" if x else "")  
  
        # Display the DataFrame in a sortable table  
        st.dataframe(df)  
  
        # Show amenities in an expander for each unit  
        for index, row in df.iterrows():  
            with st.expander(f"Unit {index + 1}: {row['Property']} - {row['Size']}"):  
                st.write(f"**Rent**: ${row['Rent']}")  
                st.write(f"**Available**: {row['Available']}")  
                st.write(f"**Building**: {row['Building']}")  
                st.write(f"**Amenities**: {', '.join(row['Amenities'])}")  
                if row["Floorplan"]:  
                    st.markdown(f"[View Floorplan]({row['Floorplan']})")  
else:  
    st.info("Click 'Fetch Unit Data' to load data.")  