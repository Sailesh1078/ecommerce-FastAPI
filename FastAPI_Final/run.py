# run.py
import uvicorn

def start_app():
    """Start the FastAPI application with Uvicorn."""
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True) # Changed to "main:app"

if __name__ == "__main__":
    start_app()