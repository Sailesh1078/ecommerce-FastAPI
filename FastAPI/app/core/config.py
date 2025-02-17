# app/core/config.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "f27c9e2d5a6b8c3e1f4d9b7a6e5c8f2a4d7e3b6c1a8f9e2d5b7c4a1f8d3e6c2b")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
