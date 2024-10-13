import os
import streamlit as st
from dotenv import load_dotenv
import requests
import base64
import json

# Module implemented from blog: https://datagraphi.com/blog/post/2022/9/24/user-authentication-and-page-wise-authorization-in-a-streamlit-multi-page-app-using-aws-cognito

# ------------------------------------
# Read constants from environment file
# ------------------------------------
load_dotenv()
COGNITO_DOMAIN = os.environ.get("COGNITO_DOMAIN")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
APP_URI = os.environ.get("APP_URI")


# ------------------------------------
# Initialise Streamlit state variables
# ------------------------------------
def initialise_st_state_vars():
    if "auth_code" not in st.session_state:
        st.session_state["auth_code"] = ""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_cognito_groups" not in st.session_state:
        st.session_state["user_cognito_groups"] = []


# ----------------------------------
# Get authorization code after login
# ----------------------------------
def get_auth_code():
    """
    Sets the auth_code state variable.
    """
    auth_query_params = st.query_params()
    try:
        auth_code = dict(auth_query_params)["code"][0]
    except (KeyError, TypeError):
        auth_code = ""

    return auth_code


# ----------------------------------
# Set authorization code after login
# ----------------------------------
def set_auth_code():
    """
    Sets auth_code state variable.

    Returns:
        Nothing.
    """
    initialise_st_state_vars()
    auth_code = get_auth_code()
    st.session_state["auth_code"] = auth_code


# -------------------------------------------------------
# Use authorization code to get user access and id tokens
# -------------------------------------------------------
def get_user_tokens(auth_code):
    """
    Gets user tokens by making a post request call.

    Args:
        auth_code: Authorization code from cognito server.

    Returns:
        {
        'access_token': access token from cognito server if user is successfully authenticated.
        'id_token': access token from cognito server if user is successfully authenticated.
        }

    """

    # Variables to make a post request
    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_secret_encoded = str(
        base64.b64encode(client_secret_string.encode("utf-8")), "utf-8"
    )
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

    token_response = requests.post(token_url, headers=headers, data=body)
    try:
        access_token = token_response.json()["access_token"]
        id_token = token_response.json()["id_token"]
    except (KeyError, TypeError):
        access_token = ""
        id_token = ""

    return access_token, id_token


# ---------------------------------------------
# Use access token to retrieve user information
# ---------------------------------------------
def get_user_info(access_token):
    """
    Gets user info from aws cognito server.

    Args:
        access_token: string access token from the aws cognito user pool
        retrieved using the access code.

    Returns:
        userinfo_response: json object.
    """
    userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {access_token}",
    }

    userinfo_response = requests.get(userinfo_url, headers=headers)

    return userinfo_response.json()


# -------------------------------------------------------
# Decode access token to JWT to get user's cognito groups
# -------------------------------------------------------
# Ref - https://gist.github.com/GuillaumeDerval/b300af6d4f906f38a051351afab3b95c
def pad_base64(data):
    """
    Makes sure base64 data is padded.

    Args:
        data: base64 token string.

    Returns:
        data: padded token string.
    """
    missing_padding = len(data) % 4
    if missing_padding != 0:
        data += "=" * (4 - missing_padding)
    return data


# -----------------------------
# Set Streamlit state variables
# -----------------------------
def set_st_state_vars():
    """
    Sets the streamlit state variables after user authentication.
    """
    try:
        initialise_st_state_vars()
        auth_code = get_auth_code()
        access_token, id_token = get_user_tokens(auth_code)

        if access_token and id_token:
            st.session_state["auth_code"] = auth_code
            st.session_state["authenticated"] = True
            # Optionally, get and store user info
            # user_info = get_user_info(access_token)
            # st.session_state["user_info"] = user_info
        else:
            st.session_state["authenticated"] = False
    except Exception as e:
        st.error(f"An error occurred during authentication: {str(e)}")
        st.session_state["authenticated"] = False

# -----------------------------
# Login/ Logout components
# -----------------------------
login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
logout_link = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"

def button_login():
    """
    Returns:
        A Streamlit button for login.
    """
    st.page_link(page=login_link, label="Log In", icon="🔗")

def button_logout():
    """
    Returns:
        A Streamlit button for logout.
    """
    st.page_link(page=logout_link, label="Log Out", icon="🔗")