import os
import streamlit as st
from dotenv import load_dotenv
import requests
import base64

load_dotenv()
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
APP_URI = os.getenv("APP_URI")

def initialize_session_state():
    if "auth_code" not in st.session_state:
        st.session_state["auth_code"] = ""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if "user_cognito_groups" not in st.session_state:
        st.session_state["user_cognito_groups"] = []

def get_auth_code():
    auth_query_params = st.experimental_get_query_params()
    try:
        return auth_query_params["code"][0]
    except (KeyError, IndexError):
        return ""

def get_user_tokens(auth_code):
    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_secret_encoded = str(base64.b64encode(client_secret_string.encode("utf-8")), "utf-8")
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
        return token_response.json()["access_token"], token_response.json()["id_token"]
    except KeyError:
        return "", ""

def get_user_info(access_token):
    userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    return requests.get(userinfo_url, headers=headers).json()

def set_auth_state():
    initialize_session_state()
    auth_code = get_auth_code()
    if auth_code:
        access_token, id_token = get_user_tokens(auth_code)
        if access_token and id_token:
            st.session_state["auth_code"] = auth_code
            st.session_state["authenticated"] = True
            # Uncomment the next line if you want to store user info
            # st.session_state["user_info"] = get_user_info(access_token)
        else:
            st.session_state["authenticated"] = False
    else:
        st.session_state["authenticated"] = False

login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
logout_link = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"

def button_login():
    st.markdown(f"<a href='{login_link}' target='_self'>Log In</a>", unsafe_allow_html=True)

def button_logout():
    st.markdown(f"<a href='{logout_link}' target='_self'>Log Out</a>", unsafe_allow_html=True)