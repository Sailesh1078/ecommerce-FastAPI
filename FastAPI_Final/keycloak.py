# keycloak.py (Placed in the same directory as auth.py - root directory)
import httpx
from fastapi import HTTPException, status


# --- Keycloak Configuration
KEYCLOAK_URL = "http://localhost:8080"
REALM_NAME = "fastapi-realm" # Please replace "fastapi-realm" with your actual realm name if different
KEYCLOAK_CLIENT_ID = "fastapi-client" # Please replace "fastapi-client" with your actual client ID if different

# --- Admin Credentials
KEYCLOAK_ADMIN_USERNAME = "admin"      # Please replace "admin" with your actual admin username
KEYCLOAK_ADMIN_PASSWORD = "admin"      # Please replace "password" with your actual admin password
KEYCLOAK_ADMIN_CLIENT_ID = "admin-cli" # Please replace "admin-cli" if you are using a different admin client ID


async def get_keycloak_admin_token():
    """
    Retrieves an admin access token from Keycloak using hardcoded admin credentials.
    WARNING: THIS METHOD USES HARDCODED CREDENTIALS AND IS INSECURE.
    DO NOT USE IN PRODUCTION.
    """
    token_url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token" # Targets master realm as in your snippet
    client = httpx.AsyncClient()

    try:
        response = await client.post(
            token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "password",
                "client_id": KEYCLOAK_ADMIN_CLIENT_ID,
                "username": KEYCLOAK_ADMIN_USERNAME,
                "password": KEYCLOAK_ADMIN_PASSWORD,
            },
        )
        response.raise_for_status()
        token_data = response.json()
        return token_data["access_token"]
    except httpx.HTTPError as e:
        error_detail = f"Failed to retrieve Keycloak admin token: {e.response.status_code} - {e.response.text}"
        print(error_detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)
