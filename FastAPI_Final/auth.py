# auth.py
import json
from typing import Dict, List

import httpx
from fastapi import Depends, FastAPI, HTTPException, Security, APIRouter
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, jwk
from jose.exceptions import JWTError
from pydantic import BaseModel
import schemas
from sqlalchemy.orm import Session
import models
from database import get_db


# Configuration (These should ideally be environment variables, but are hardcoded here for your request)
KEYCLOAK_URL = "http://localhost:8080"
REALM_NAME = "fastapi-realm"
KEYCLOAK_CLIENT_ID = "fastapi-client"

# JWKs URL
JWKS_URL = f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/certs"

# OAuth2 scheme
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/realms/{REALM_NAME}/protocol/openid-connect/token",
    auto_error=False
)

# Models
class TokenData(BaseModel):
    username: str
    email: str
    roles: List[str]
    token: str  # ADDED: Include the raw token string


# --- Router for Authentication Endpoints ---
router = APIRouter()


# Token validation function
async def validate_token(token: str) -> TokenData:
    try:
        # Fetch JWKS (same as before)
        async with httpx.AsyncClient() as client:
            response = await client.get(JWKS_URL)
            response.raise_for_status()
            jwks = response.json()

        # Decode the token headers to get the key ID (kid) (same as before)
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing 'kid' header")

        # Find the correct key in the JWKS (same as before)
        key_data = next((key for key in jwks["keys"] if key["kid"] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Matching key not found in JWKS")

        # Convert JWK to RSA public key (same as before)
        public_key = jwk.construct(key_data).public_key()

        # --- Modified jwt.decode() call (Simplified) ---
        payload = jwt.decode(
            token,
            key=public_key,
            algorithms=["RS256"],
            audience="account"
        )
        # --- End of Modified section ---

        # Extract username and roles (same as before)
        username = payload.get("preferred_username")
        roles = payload.get("realm_access", {}).get("roles", [])
        email = payload.get("email")
        if not username or not roles or not email:
            raise HTTPException(status_code=401, detail="Token missing required claims")

        # --- Return TokenData WITH the token ---
        return TokenData(username=username, roles=roles, email=email, token=token) # Include the token here


    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

# Dependency to get the current user (Modified to return TokenData with token)
async def get_current_user(token: str = Depends(oauth2_scheme)): # 'token' parameter now receives the raw token string
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await validate_token(token) # Pass the raw token to validate_token


# Role-Based Access Control (RBAC) (remains the same)
def has_role(required_role: str):
    def role_checker(token_data: TokenData = Depends(get_current_user)) -> TokenData:
        if required_role not in token_data.roles:
            raise HTTPException(status_code=403, detail="Not authorized")
        return token_data
    return role_checker

def get_current_user_local_db(current_user_token: TokenData, db: Session):
    """
    Retrieves the user from the local database based on the username in the token.
    """
    db_user = db.query(models.User).filter(models.User.username == current_user_token.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found in local database") # Or handle as needed
    return db_user


# --- Customer Registration Endpoint (Public) ---
@router.post("/register/customer/", status_code=201)
async def register_customer(registration_request: schemas.CustomerRegistrationRequest): # Use schemas.CustomerRegistrationRequest
    """
    Public endpoint to register a new customer user in Keycloak.
    """
    keycloak_admin_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}"
    admin_client = httpx.AsyncClient(auth=('admin', 'admin')) # Use your Keycloak admin credentials securely

    user_data = {
        "username": registration_request.username,
        "email": registration_request.email,
        "firstName": registration_request.firstName,
        "lastName": registration_request.lastName,
        "enabled": True,
        "emailVerified": True,
        "credentials": [{"type": "password", "value": registration_request.password, "temporary": False}],
        "realmRoles": ["customer"] # Assign "customer" realm role
    }

    try:
        response = await admin_client.post(
            f"{keycloak_admin_url}/users",
            headers={"Content-Type": "application/json"},
            json=user_data
        )
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return {"message": "Customer registered successfully"}
    except httpx.HTTPError as e:
        error_detail = f"Keycloak user creation failed: {e.response.status_code} - {e.response.text}"
        print(error_detail) # Log the error for debugging
        raise HTTPException(status_code=500, detail=error_detail) # Return a 500 error to the client


# --- Admin User Registration Endpoint (Admin-Only) ---
@router.post("/admin/register/admin/", status_code=201, dependencies=[Security(has_role("admin"))])
async def register_admin_user(registration_request: schemas.AdminRegistrationRequest, current_user: TokenData = Depends(get_current_user)): # Use schemas.AdminRegistrationRequest
    """
    Protected endpoint (admin role required) to register a new admin user in Keycloak.
    """
    keycloak_admin_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}"
    admin_client = httpx.AsyncClient(auth=('admin', 'admin')) # Use your Keycloak admin credentials securely

    user_data = {
        "username": registration_request.username,
        "email": registration_request.email,
        "firstName": registration_request.firstName,
        "lastName": registration_request.lastName,
        "enabled": True,
        "emailVerified": True,
        "credentials": [{"type": "password", "value": registration_request.password, "temporary": False}],
        "realmRoles": ["admin"] # Assign "admin" realm role
    }

    try:
        response = await admin_client.post(
            f"{keycloak_admin_url}/users",
            headers={"Content-Type": "application/json"},
            json=user_data
        )
        response.raise_for_status()
        return {"message": "Admin user registered successfully"}
    except httpx.HTTPError as e:
        error_detail = f"Keycloak admin user creation failed: {e.response.status_code} - {e.response.text}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)
def is_admin(user_roles: List[str]) -> bool:
    # Checks if the user has the 'admin' role.
    return "admin" in user_roles