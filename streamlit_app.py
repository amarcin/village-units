import logging
import os
import base64
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import awswrangler as wr
import boto3
import botocore
import pandas as pd
import plotly.express as px
import pytz
import requests
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_URL = os.environ.get("API_URL")
BUCKET = os.environ.get("BUCKET")
PREFIX = os.environ.get("PREFIX")
AWS_REGION = os.environ.get("AWS_REGION")
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
APP_URI = os.getenv("APP_URI")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_IDENTITY_POOL_ID = os.getenv("COGNITO_IDENTITY_POOL_ID")

st.set_page_config(page_title="Village Data", page_icon=":bar_chart:", layout="centered")

# Authentication functions

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "auth_state" not in st.session_state:
        st.session_state.auth_state = {
            "authenticated": False,
            "user_cognito_groups": [],
            "aws_credentials": None,
            "credentials_expiration": None,
        }
    logger.info("Session state initialized")

# Call initialize_session_state at the start of the script
initialize_session_state()

def get_auth_code():
    """Get authorization code from query parameters."""
    try:
        return st.query_params.get("code", "")
    except Exception as e:
        logger.error(f"Error getting auth code: {e}")
        return ""

def get_user_tokens(auth_code):
    """Get user tokens from Cognito server."""
    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_secret_encoded = base64.b64encode(
        client_secret_string.encode("utf-8")
    ).decode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {client_secret_encoded}",
    }
    body = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": auth_code,
        "redirect_uri": APP_URI,
    }

    try:
        response = requests.post(token_url, headers=headers, data=body, timeout=10)
        response.raise_for_status()
        tokens = response.json()
        return tokens.get("access_token"), tokens.get("id_token")
    except requests.RequestException as e:
        logger.error(f"Error getting user tokens: {e}")
        return "", ""

def get_user_info(access_token):
    """Get user info from Cognito server."""
    userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    try:
        response = requests.get(userinfo_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error getting user info: {e}")
        return {}

def get_aws_credentials(id_token):
    """Get AWS credentials using Cognito Identity Pool."""
    client = boto3.client("cognito-identity", region_name=AWS_REGION)

    try:
        response = client.get_id(
            IdentityPoolId=COGNITO_IDENTITY_POOL_ID,
            Logins={
                f"cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}": id_token
            },
        )
        identity_id = response["IdentityId"]

        response = client.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins={
                f"cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}": id_token
            },
        )

        credentials = response["Credentials"]
        return {
            "AccessKeyId": credentials["AccessKeyId"],
            "SecretKey": credentials["SecretKey"],
            "SessionToken": credentials["SessionToken"],
            "Expiration": credentials["Expiration"].replace(tzinfo=pytz.UTC),
        }
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error getting AWS credentials: {e}")
        return None

def set_auth_session():
    """Set authentication session state."""
    # Check if already authenticated and credentials are still valid
    if (
        st.session_state.auth_state["authenticated"]
        and st.session_state.auth_state["credentials_expiration"]
    ):
        now = datetime.now(pytz.UTC)
        if now < st.session_state.auth_state["credentials_expiration"]:
            logger.info("Using cached authentication")
            return

    auth_code = get_auth_code()

    if auth_code:
        logger.info("Auth code received, attempting to get tokens")
        access_token, id_token = get_user_tokens(auth_code)

        if access_token and id_token:
            logger.info("Tokens received, setting session state")
            user_info = get_user_info(access_token)

            # Get AWS credentials
            aws_credentials = get_aws_credentials(id_token)
            if aws_credentials:
                st.session_state.auth_state["authenticated"] = True
                st.session_state.auth_state["user_info"] = user_info
                st.session_state.auth_state["aws_credentials"] = aws_credentials
                st.session_state.auth_state["credentials_expiration"] = aws_credentials[
                    "Expiration"
                ]
                logger.info("Authentication successful")
            else:
                logger.warning("Failed to obtain AWS credentials")
                st.session_state.auth_state["authenticated"] = False
        else:
            logger.warning("Failed to get tokens")
            st.session_state.auth_state["authenticated"] = False
    else:
        logger.info("No auth code present")
        st.session_state.auth_state["authenticated"] = False

    # Clear the code from query params to avoid reprocessing
    st.query_params.clear()

def login_button():
    """Create login button."""
    login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
    st.page_link(page=login_link, label="Log In", icon="🔑")

def logout_button():
    """Create logout button."""
    if st.button("Log Out", key="logout_button"):
        st.session_state.auth_state = {
            "authenticated": False,
            "user_cognito_groups": [],
            "aws_credentials": None,
            "credentials_expiration": None,
        }
        st.rerun()

# Main application functions

def title():
    col1, col2 = st.columns([6, 1])
    col1.title("Village Data")
    with col2:
        if st.session_state.auth_state["authenticated"]:
            logout_button()
        else:
            login_button()

@st.cache_data(show_spinner=True, ttl=21600)
def fetch_units():
    session = requests.Session()
    page = 1
    unit_array = []

    while True:
        try:
            r = session.get(API_URL, params={"page": page})
            r.raise_for_status()
            units = r.json().get("units", [])
            if not units:
                break
            unit_array.extend(
                [
                    {
                        "Unit": unit.get("unit_number"),
                        "Rent": unit.get("rent"),
                        "Property": unit.get("property", {}).get("name"),
                        "beds": unit.get("floorplan", {}).get("beds"),
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
        except requests.RequestException as e:
            st.error(f"Failed to fetch data: {e}")
            return None, None

    return pd.DataFrame(unit_array), datetime.now(ZoneInfo("America/Chicago"))

@st.cache_data(ttl=3600, show_spinner=True)
def load_historical_data(_boto3_session):
    s3_path = f"s3://{BUCKET}/{PREFIX}/"
    try:
        parquet_files = wr.s3.list_objects(
            path=s3_path, suffix=".parquet", boto3_session=_boto3_session
        )
        all_data = pd.concat(
            [
                wr.s3.read_parquet(path=file, boto3_session=_boto3_session)
                for file in parquet_files
            ],
            ignore_index=True,
        )
        all_data.columns = all_data.columns.str.lower()  # Convert all column names to lowercase
        all_data["fetch_datetime"] = pd.to_datetime(all_data["fetch_datetime"])
        return all_data
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return None

def display_historical_data(historical_data):
    properties = historical_data["property_name"].unique()
    property_filter = st.selectbox("Select Property", ["All"] + list(properties))
    
    filtered_data = historical_data
    if property_filter != "All":
        filtered_data = filtered_data[filtered_data["property_name"] == property_filter]

    if "beds" in filtered_data.columns:
        beds_filter = st.selectbox("Select Number of beds", ["All"] + sorted(filtered_data["beds"].unique()))
        if beds_filter != "All":
            filtered_data = filtered_data[filtered_data["beds"] == beds_filter]
    else:
        st.warning("Column 'beds' not found in the dataset.")

    unit_filter = st.selectbox("Select Unit", ["All"] + sorted(filtered_data["unit_number"].unique()))
    if unit_filter != "All":
        filtered_data = filtered_data[filtered_data["unit_number"] == unit_filter]

    rent_filter = st.slider("Select Rent Price Range", int(filtered_data["rent"].min()), int(filtered_data["rent"].max()), (int(filtered_data["rent"].min()), int(filtered_data["rent"].max())))
    filtered_data = filtered_data[(filtered_data["rent"] >= rent_filter[0]) & (filtered_data["rent"] <= rent_filter[1])]

    st.subheader("Rent Summary")
    property_summary = filtered_data.groupby("unit_number").agg(
        {"rent": ["last", "mean", "min", "max"]}
    )
    property_summary.columns = ["Current", "Avg", "Min", "Max"]
    st.dataframe(property_summary)

    st.subheader("Price Changes")
    price_changes = filtered_data.groupby("unit_number").agg(
        {"rent": ["first", "last", lambda x: x.diff().sum()]}
    )
    price_changes.columns = ["Initial Rent", "Current Rent", "Total Change"]
    price_changes["Percent Change"] = (
        price_changes["Total Change"] / price_changes["Initial Rent"]
    ) * 100
    st.dataframe(price_changes)

    st.subheader("Rent History")
    time_periods = {
        "1 Month": 30,
        "3 Months": 90,
        "6 Months": 180,
        "1 Year": 365,
        "Max": None,
    }
    selected_period = st.selectbox("Select Time Period", list(time_periods.keys()))

    # Ensure end_date is timezone-aware
    end_date = datetime.now(pytz.UTC)
    if time_periods[selected_period]:
        start_date = end_date - timedelta(days=time_periods[selected_period])
    else:
        start_date = filtered_data["fetch_datetime"].min().replace(tzinfo=pytz.UTC)

    # Ensure filtered_data['fetch_datetime'] is timezone-aware
    if filtered_data["fetch_datetime"].dt.tz is None:
        filtered_data["fetch_datetime"] = filtered_data[
            "fetch_datetime"
        ].dt.tz_localize(pytz.UTC)

    filtered_data = filtered_data[
        (filtered_data["fetch_datetime"] >= start_date)
        & (filtered_data["fetch_datetime"] <= end_date)
    ]

    fig = px.line(
        filtered_data,
        x="fetch_datetime",
        y="rent",
        color="unit_number",
        title=f"Rent History - {property_filter if property_filter != 'All' else 'All Properties'}",
    )
    st.plotly_chart(fig)

    if unit_filter == "All":
        st.subheader("Specific Unit Price History")
        selected_unit = st.selectbox("Select Unit for Detailed History", filtered_data["unit_number"].unique())
        unit_data = filtered_data[filtered_data["unit_number"] == selected_unit]

        fig_unit = px.line(
            unit_data,
            x="fetch_datetime",
            y="rent",
            title=f"Price History - Unit {selected_unit}",
        )
        st.plotly_chart(fig_unit)

def main():
    set_auth_session()

    if not st.session_state.auth_state["authenticated"]:
        st.warning("Please log in to access the application.")
        return

    credentials = st.session_state.auth_state["aws_credentials"]
    if not credentials:
        st.error("AWS credentials not available. Please log in again.")
        return

    boto3_session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=AWS_REGION,
    )

    trackerTab, liveDataTab, aboutTab = st.tabs(["Price Tracker", "Live Data", "About"])

    with trackerTab:
        if "historical_data" not in st.session_state:
            st.session_state.historical_data = load_historical_data(boto3_session)

        if st.session_state.historical_data is not None:
            display_historical_data(st.session_state.historical_data)
        else:
            st.warning("No historical data available.")

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
                        )
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
        ## Upcoming features
        - Price drop notifications
        - Advanced filtering options
        - New units added section
        - Price changes by number of bedrooms
        """
        )

if __name__ == "__main__":
    title()
    main()
