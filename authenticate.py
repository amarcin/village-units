# import base64
# import logging
# import os
# from datetime import datetime

# import boto3
# import botocore
# import pytz
# import requests
# import streamlit as st
# from dotenv import load_dotenv

# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Load environment variables
# load_dotenv()
# COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
# CLIENT_ID = os.getenv("CLIENT_ID")
# CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# APP_URI = os.getenv("APP_URI")
# COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
# COGNITO_IDENTITY_POOL_ID = os.getenv("COGNITO_IDENTITY_POOL_ID")
# AWS_REGION = os.getenv("AWS_REGION")


# def initialize_session_state():
#     """Initialize Streamlit session state variables."""
#     if "auth_state" not in st.session_state:
#         st.session_state.auth_state = {
#             "authenticated": False,
#             "user_cognito_groups": [],
#             "aws_credentials": None,
#             "credentials_expiration": None,
#         }
#     logger.info("Session state initialized")


# def get_auth_code():
#     """Get authorization code from query parameters."""
#     try:
#         return st.query_params.get("code", "")
#     except Exception as e:
#         logger.error(f"Error getting auth code: {e}")
#         return ""


# def get_user_tokens(auth_code):
#     """Get user tokens from Cognito server."""
#     token_url = f"{COGNITO_DOMAIN}/oauth2/token"
#     client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
#     client_secret_encoded = base64.b64encode(
#         client_secret_string.encode("utf-8")
#     ).decode("utf-8")
#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded",
#         "Authorization": f"Basic {client_secret_encoded}",
#     }
#     body = {
#         "grant_type": "authorization_code",
#         "client_id": CLIENT_ID,
#         "code": auth_code,
#         "redirect_uri": APP_URI,
#     }

#     try:
#         response = requests.post(token_url, headers=headers, data=body, timeout=10)
#         response.raise_for_status()
#         tokens = response.json()
#         return tokens.get("access_token"), tokens.get("id_token")
#     except requests.RequestException as e:
#         logger.error(f"Error getting user tokens: {e}")
#         return "", ""


# def get_user_info(access_token):
#     """Get user info from Cognito server."""
#     userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"
#     headers = {
#         "Authorization": f"Bearer {access_token}",
#     }

#     try:
#         response = requests.get(userinfo_url, headers=headers, timeout=10)
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         logger.error(f"Error getting user info: {e}")
#         return {}


# def get_aws_credentials(id_token):
#     """Get AWS credentials using Cognito Identity Pool."""
#     client = boto3.client("cognito-identity", region_name=AWS_REGION)

#     try:
#         response = client.get_id(
#             IdentityPoolId=COGNITO_IDENTITY_POOL_ID,
#             Logins={
#                 f"cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}": id_token
#             },
#         )
#         identity_id = response["IdentityId"]

#         response = client.get_credentials_for_identity(
#             IdentityId=identity_id,
#             Logins={
#                 f"cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}": id_token
#             },
#         )

#         credentials = response["Credentials"]
#         return {
#             "AccessKeyId": credentials["AccessKeyId"],
#             "SecretKey": credentials["SecretKey"],
#             "SessionToken": credentials["SessionToken"],
#             "Expiration": credentials["Expiration"].replace(tzinfo=pytz.UTC),
#         }
#     except botocore.exceptions.ClientError as e:
#         logger.error(f"Error getting AWS credentials: {e}")
#         return None


# def set_auth_session():
#     """Set authentication session state."""
#     initialize_session_state()

#     # Check if already authenticated and credentials are still valid
#     if (
#         st.session_state.auth_state["authenticated"]
#         and st.session_state.auth_state["credentials_expiration"]
#     ):
#         now = datetime.now(pytz.UTC)
#         if now < st.session_state.auth_state["credentials_expiration"]:
#             logger.info("Using cached authentication")
#             return

#     auth_code = get_auth_code()

#     if auth_code:
#         logger.info("Auth code received, attempting to get tokens")
#         access_token, id_token = get_user_tokens(auth_code)

#         if access_token and id_token:
#             logger.info("Tokens received, setting session state")
#             user_info = get_user_info(access_token)

#             # Get AWS credentials
#             aws_credentials = get_aws_credentials(id_token)
#             if aws_credentials:
#                 st.session_state.auth_state["authenticated"] = True
#                 st.session_state.auth_state["user_info"] = user_info
#                 st.session_state.auth_state["aws_credentials"] = aws_credentials
#                 st.session_state.auth_state["credentials_expiration"] = aws_credentials[
#                     "Expiration"
#                 ]
#                 logger.info("Authentication successful")
#             else:
#                 logger.warning("Failed to obtain AWS credentials")
#                 st.session_state.auth_state["authenticated"] = False
#         else:
#             logger.warning("Failed to get tokens")
#             st.session_state.auth_state["authenticated"] = False
#     else:
#         logger.info("No auth code present")
#         st.session_state.auth_state["authenticated"] = False

#     # Clear the code from query params to avoid reprocessing
#     st.query_params.clear()


# def login_button():
#     """Create login button."""
#     login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
#     st.page_link(page=login_link, label="Log In", icon="🔑")


# def logout_button():
#     """Create logout button."""
#     # logout_link = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"
#     if st.button("Log Out", key="logout_button"):
#         st.session_state.auth_state = {
#             "authenticated": False,
#             "user_cognito_groups": [],
#             "aws_credentials": None,
#             "credentials_expiration": None,
#         }
#         st.rerun()
