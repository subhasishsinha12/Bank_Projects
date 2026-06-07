"""
Azure Functions entry point.
Wraps the FastAPI app using azure-functions ASGI integration.
"""
import azure.functions as func
from src.main import app

# Azure Functions ASGI wrapper
azure_app = func.AsgiFunctionApp(
    app=app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)
