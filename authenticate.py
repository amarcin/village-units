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
    for key in ["auth_code", "authenticated", "user_cognito_groups"]:
        if key not in st.session_state:
            st.session_state[key] = "" if key == "auth_code" else ([] if key == "user_cognito_groups" else False)

def get_auth_code():
    return st.query_params.get("code", [""])[0]

def get_user_tokens(auth_code):
    token_url = f"{COGNITO_DOMAIN}/oauth2/token"
    client_secret_encoded = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")).decode("utf-8")
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
    response = requests.post(token_url, headers=headers, data=body).json()
    return response.get("access_token", ""), response.get("id_token", "")

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
            st.session_state.update({
                "auth_code": auth_code,
                "authenticated": True,
                # Uncomment the next line if you want to store user info
                # "user_info": get_user_info(access_token)
            })
        else:
            st.session_state["authenticated"] = False
    else:
        st.session_state["authenticated"] = False

login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
logout_link = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"

def button_login():
    st.page_link(login_link, label="Log In", icon="🔗")

def button_logout():
    st.page_link(logout_link, label="Log Out", icon="🔗")