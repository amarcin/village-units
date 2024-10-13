import os
import streamlit as st
from dotenv import load_dotenv
import requests
import base64
import logging
import boto3
import botocore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
COGNITO_DOMAIN = os.getenv("COGNITO_DOMAIN")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
APP_URI = os.getenv("APP_URI")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_IDENTITY_POOL_ID = os.getenv("COGNITO_IDENTITY_POOL_ID")
AWS_REGION = os.getenv("AWS_REGION")

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "auth_code" not in st.session_state:
        st.session_state.auth_code = ""
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "id_token" not in st.session_state:
        st.session_state.id_token = ""
    if "user_cognito_groups" not in st.session_state:
        st.session_state.user_cognito_groups = []
    if "aws_credentials" not in st.session_state:
        st.session_state.aws_credentials = None
    logger.info("Session state initialized")

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
    client_secret_encoded = base64.b64encode(client_secret_string.encode("utf-8")).decode("utf-8")
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
        response = requests.post(token_url, headers=headers, data=body)
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
        response = requests.get(userinfo_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error getting user info: {e}")
        return {}

def get_aws_credentials(id_token):
    """Get AWS credentials using Cognito Identity Pool."""
    client = boto3.client('cognito-identity', region_name=AWS_REGION)
    
    try:
        # Get ID from Cognito Identity Pool
        response = client.get_id(
            IdentityPoolId=COGNITO_IDENTITY_POOL_ID,
            Logins={
                f'cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}': id_token
            }
        )
        identity_id = response['IdentityId']
        
        # Get credentials for the identity
        response = client.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins={
                f'cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}': id_token
            }
        )
        
        credentials = response['Credentials']
        return {
            'AccessKeyId': credentials['AccessKeyId'],
            'SecretKey': credentials['SecretKey'],
            'SessionToken': credentials['SessionToken'],
            'Expiration': credentials['Expiration']
        }
    except botocore.exceptions.ClientError as e:
        logger.error(f"Error getting AWS credentials: {e}")
        return None

def set_auth_session():
    """Set authentication session state."""
    initialize_session_state()
    
    if not st.session_state.authenticated:
        auth_code = get_auth_code()
        
        if auth_code and auth_code != st.session_state.auth_code:
            logger.info("New auth code received, attempting to get tokens")
            access_token, id_token = get_user_tokens(auth_code)
            
            if access_token and id_token:
                logger.info("Tokens received, setting session state")
                st.session_state.auth_code = auth_code
                st.session_state.access_token = access_token
                st.session_state.id_token = id_token
                st.session_state.authenticated = True
                user_info = get_user_info(access_token)
                st.session_state.user_info = user_info
                
                # Get AWS credentials
                aws_credentials = get_aws_credentials(id_token)
                if aws_credentials:
                    st.session_state.aws_credentials = aws_credentials
                    logger.info("AWS credentials obtained successfully")
                else:
                    logger.warning("Failed to obtain AWS credentials")
                
                logger.info("Authentication successful")
                st.rerun()
            else:
                logger.warning("Failed to get tokens")
                st.session_state.authenticated = False
        elif st.session_state.access_token and st.session_state.id_token:
            logger.info("Using existing tokens")
            st.session_state.authenticated = True
        else:
            logger.info("No valid auth code or tokens present")
            st.session_state.authenticated = False

def login_button():
    """Create login button."""
    login_link = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
    st.page_link(page=login_link, label="Log In", icon="🔑")

def logout_button():
    """Create logout button."""
    logout_link = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"
    st.page_link(page=logout_link, label="Log Out", icon="🚪")