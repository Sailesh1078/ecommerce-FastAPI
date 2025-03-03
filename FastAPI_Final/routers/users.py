# routers/users.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import httpx
from database import get_db
import models
import schemas
import auth
import keycloak

router = APIRouter(
    prefix="/users",
    tags=["users"],
)

# --- Keycloak Configuration (from auth.py - assuming these are defined there) ---
KEYCLOAK_URL = auth.KEYCLOAK_URL
REALM_NAME = auth.REALM_NAME


# --- Public Customer User Creation Endpoint ---
@router.post("/create", response_model=schemas.UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user_request: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Public endpoint to create a new customer user in Keycloak and local database.
    Assigns the "customer" role by default.
    """
    token = await keycloak.get_keycloak_admin_token()  # Get admin token securely

    async with httpx.AsyncClient() as client:
        # Check if user already exists in Keycloak
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={"Authorization": f"Bearer {token}"},
            params={"username": user_request.username}
        )
        response.raise_for_status()
        if response.json():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists in Keycloak")

        # Create user in Keycloak
        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            json={
                "username": user_request.username,
                "enabled": True,
                "email": user_request.email,
                "firstName": user_request.firstname,
                "lastName": user_request.lastname,
                "credentials": [{"type": "password", "value": user_request.password, "temporary": False}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

        keycloak_user_id = response.headers["Location"].split("/")[-1]

        # Fetch the "customer" role ID
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        roles = response.json()
        customer_role = next((role for role in roles if role["name"] == "customer"), None) # Changed to "customer" role
        if not customer_role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer role not found in Keycloak")
        customer_role_id = customer_role["id"]

        # Assign the "customer" role to the newly created user
        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{keycloak_user_id}/role-mappings/realm",
            json=[{"id": customer_role_id, "name": "customer"}], # Changed to "customer" role
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

    # Create user in local database (after successful Keycloak creation)
    local_db_user = models.User(
        username=user_request.username,
        email=user_request.email,
        first_name=user_request.firstname, # Corrected to first_name
        last_name=user_request.lastname  # Corrected to last_name
    )
    db.add(local_db_user)
    db.commit()
    db.refresh(local_db_user)
    return schemas.UserSchema.from_orm(local_db_user) # Return serialized user


# --- Admin User Creation Endpoint (Admin Only) ---
@router.post("/admin/create-admin", response_model=schemas.UserSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(auth.has_role("admin"))])
async def create_admin_user(admin_request: schemas.AdminRegistrationRequest, db: Session = Depends(get_db)): # Using AdminRegistrationRequest schema
    """
    Admin-only endpoint to create a new admin user in Keycloak and local database.
    Assigns the "admin" role.
    """
    token = await keycloak.get_keycloak_admin_token()  # Get admin token securely

    async with httpx.AsyncClient() as client:
        # Check if admin user already exists in Keycloak
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            headers={"Authorization": f"Bearer {token}"},
            params={"username": admin_request.username}
        )
        response.raise_for_status()
        if response.json():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Admin user already exists in Keycloak")

        # Create admin user in Keycloak
        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users",
            json={
                "username": admin_request.username,
                "enabled": True,
                "email": admin_request.email,
                "firstName": admin_request.firstName, # Using AdminRegistrationRequest schema fields
                "lastName": admin_request.lastName,   # Using AdminRegistrationRequest schema fields
                "credentials": [{"type": "password", "value": admin_request.password, "temporary": False}],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

        keycloak_admin_user_id = response.headers["Location"].split("/")[-1]

        # Fetch the "admin" role ID
        response = await client.get(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/roles",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        roles = response.json()
        admin_role = next((role for role in roles if role["name"] == "admin"), None) # Get "admin" role
        if not admin_role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin role not found in Keycloak")
        admin_role_id = admin_role["id"]

        # Assign the "admin" role to the newly created admin user
        response = await client.post(
            f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}/users/{keycloak_admin_user_id}/role-mappings/realm",
            json=[{"id": admin_role_id, "name": "admin"}], # Assign "admin" role
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

    # Create admin user in local database
    local_db_admin_user = models.User(
        username=admin_request.username,
        email=admin_request.email,
        first_name=admin_request.firstName,
        last_name=admin_request.lastName
    )
    # Assign admin role in local DB (if needed - you might handle roles differently in local DB)
    admin_role_db = db.query(models.Role).filter(models.Role.name == "admin").first()
    if admin_role_db:
        local_db_admin_user.roles.append(admin_role_db)

    db.add(local_db_admin_user)
    db.commit()
    db.refresh(local_db_admin_user)
    return schemas.UserSchema.from_orm(local_db_admin_user) # Return serialized admin user


@router.delete("/admin/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(auth.has_role("admin"))])
async def delete_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_user),
):
    """
    Delete a user by ID (admin only) from both local DB and Keycloak, using a dedicated admin token for Keycloak API auth.
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in local database")

    keycloak_admin_url = f"{KEYCLOAK_URL}/admin/realms/{REALM_NAME}"
    admin_client = httpx.AsyncClient()  # Create client without basic auth - we'll use Bearer token

    keycloak_user_id_to_delete = None  # We need to fetch Keycloak User ID based on username

    # --- Get Dedicated Admin Token for Keycloak API calls ---
    keycloak_api_admin_token = await keycloak.get_keycloak_admin_token()

    # --- Step 1: Get Keycloak User ID by Username ---
    try:
        users_search_response = await admin_client.get(
            f"{keycloak_admin_url}/users",
            params={"username": db_user.username},
            headers={"Authorization": f"Bearer {keycloak_api_admin_token}"}  # Use dedicated admin token
        )
        users_search_response.raise_for_status()
        keycloak_users_list = users_search_response.json()
        if keycloak_users_list:
            keycloak_user_id_to_delete = keycloak_users_list[0].get("id")  # Assuming username is unique
        if not keycloak_user_id_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in Keycloak")

    except httpx.HTTPError as e:
        error_detail = f"Error searching for user in Keycloak: {e.response.status_code} - {e.response.text}"
        print(error_detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)

    # --- Step 2: Delete User from Keycloak ---
    try:
        delete_keycloak_response = await admin_client.delete(
            f"{keycloak_admin_url}/users/{keycloak_user_id_to_delete}",
            headers={"Authorization": f"Bearer {keycloak_api_admin_token}"}  # Use dedicated admin token
        )
        delete_keycloak_response.raise_for_status()  # Raise error for non-successful status codes

    except httpx.HTTPError as e:
        error_detail = f"Error deleting user from Keycloak: {e.response.status_code} - {e.response.text}"
        print(error_detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)

    # --- Step 3: Delete User from Local Database ---
    try:
        db.delete(db_user)
        db.commit()
    except Exception as e:  # Catch any potential DB errors
        db.rollback()  # Rollback in case of DB error
        error_detail = f"Error deleting user from local database: {str(e)}"
        print(error_detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)

    return {"message": "User deleted successfully from local database and Keycloak."}

# --- User Profile Endpoints (Customer/Admin - /users/me) - Keep these as they are ---
@router.get("/me/", response_model=schemas.UserSchema)
def read_current_user_profile(
    current_user_token: auth.TokenData = Depends(auth.get_current_user),  # Get TokenData
    db: Session = Depends(get_db)
):
    """
    Get the profile of the currently logged-in user (customer or admin).
    Performs "just-in-time" user creation in the local database if the user doesn't exist yet.
    """
    db_user = db.query(models.User).filter(models.User.username == current_user_token.username).first()
    if not db_user:
        # Just-in-time user creation in local DB
        db_user = models.User(username=current_user_token.username,
                              email=current_user_token.email)  # Basic info from token
        # Assign roles based on Keycloak roles (simple mapping - can be enhanced)
        if "admin" in current_user_token.roles:
            admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
            if admin_role:
                db_user.roles.append(admin_role)
        customer_role = db.query(models.Role).filter(
            models.Role.name == "customer").first()  # Ensure customer role exists (default)
        if customer_role and "customer" in current_user_token.roles and "admin" not in current_user_token.roles:  # Only assign customer role if not admin
            db_user.roles.append(customer_role)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return schemas.UserSchema.from_orm(db_user)


@router.get("/me/favorites/", response_model=List[schemas.ProductSchema])
def read_current_user_favorites(
    current_user: auth.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the list of favorite products for the current user (customer or admin).
    """
    local_db_user = auth.get_current_user_local_db(current_user, db)
    return [fav_product.product for fav_product in local_db_user.favorite_products]


@router.post("/me/favorites/{product_id}", response_model=schemas.ProductSchema)
def add_product_to_favorites(
    product_id: int,
    current_user: auth.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a product to the current user's favorites (customer or admin).
    """
    local_db_user = auth.get_current_user_local_db(current_user, db)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check if already in favorites (optional, but good practice)
    if any(fav_product.id == product.id for fav_product in local_db_user.favorite_products):  # Efficient check
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in favorites")

    # Create a new FavoriteProduct object and associate it
    favorite_product_entry = models.FavoriteProduct(
        user=local_db_user,  # Explicitly set the user relationship
        product=product  # Explicitly set the product relationship
    )
    db.add(favorite_product_entry)  # Add the FavoriteProduct entry to the session
    db.commit()
    db.refresh(product)  # Refresh to get updated favorite_products relationship (though might not be necessary now)
    return product


@router.delete("/me/favorites/{product_id}", response_model=schemas.ProductSchema)
def remove_product_from_favorites(
    product_id: int,
    current_user: auth.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a product from the current user's favorites (customer or admin).
    Returns the deleted product and a success message.
    """
    local_db_user = auth.get_current_user_local_db(current_user, db)
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Explicitly query for the FavoriteProduct entry
    favorite_product_entry = db.query(models.FavoriteProduct).filter(
        models.FavoriteProduct.user_id == local_db_user.id,
        models.FavoriteProduct.product_id == product_id
    ).first()

    if not favorite_product_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not in favorites")

    db.delete(favorite_product_entry)  # Delete the FavoriteProduct entry
    db.commit()

    return_product = schemas.ProductSchema.from_orm(product)  # Create ProductSchema for response
    return return_product


# --- Admin User Management Endpoints (Admin Only - /users/admin/) ---
@router.get("/admin/", response_model=List[schemas.UserSchema], dependencies=[Depends(auth.has_role("admin"))])
def read_all_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_user),
):
    """
    List all users (admin only).
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [schemas.UserSchema.from_orm(user) for user in users]  # Serialize each user


@router.get("/admin/{user_id}", response_model=schemas.UserSchema, dependencies=[Depends(auth.has_role("admin"))])
def read_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: auth.TokenData = Depends(auth.get_current_user),
):
    """
    Get user details by ID (admin only - can view any user).
    """
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return schemas.UserSchema.from_orm(db_user) # Serialize user