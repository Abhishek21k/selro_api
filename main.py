import os
import requests
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Header, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API credentials from environment variables
SELRO_KEY = os.getenv("SELRO_KEY")
SELRO_SECRET = os.getenv("SELRO_SECRET")
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")  # Custom token for this API

# Initialize FastAPI
app = FastAPI(title="Selro Orders API", description="API to fetch all Selro orders")

# API key security scheme
api_key_header = APIKeyHeader(name="Authorization", auto_error=True)


# Pydantic models
class SelroOrder(BaseModel):
    id: int
    orderId: str
    orderStatus: str
    channel: str
    totalPrice: float
    currencyCode: str
    # Add other fields as needed


class SelroOrderResponse(BaseModel):
    orders: List[Dict[str, Any]]
    message: Optional[str] = None
    order: Optional[Dict[str, Any]] = None


# Authentication dependency
async def verify_api_key(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization.replace("Bearer ", "")
    if token != API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )
    return token


# Selro API client
class SelroClient:
    def __init__(self, key: str, secret: str):
        self.key = key
        self.secret = secret
        self.base_url = "https://api.selro.com/8/orders"

    def fetch_all_orders(self, status: str, max_pages: int = 100) -> Dict[str, Any]:
        """
        Fetch all orders with the specified status, handling pagination
        """
        page = 1
        page_size = 100
        all_orders = []
        has_more_orders = True

        while has_more_orders and page <= max_pages:
            url = f"{self.base_url}?key={self.key}&secret={self.secret}&page={page}&pagesize={page_size}&status={status}"

            try:
                response = requests.get(url)
                response.raise_for_status()

                data = response.json()

                if data and "orders" in data and len(data["orders"]) > 0:
                    orders = data["orders"]
                    all_orders.extend(orders)

                    # Check if we need to fetch more pages
                    if len(orders) < page_size:
                        has_more_orders = False
                    else:
                        page += 1
                        # Add a small delay to prevent API rate limiting
                        time.sleep(1)
                else:
                    has_more_orders = False

            except requests.exceptions.RequestException as e:
                # Log the error
                print(f"Error fetching data from Selro API: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error communicating with Selro API: {str(e)}",
                )

        return {"orders": all_orders, "message": None, "order": None}


# Create Selro client
selro_client = SelroClient(SELRO_KEY, SELRO_SECRET)


# API endpoints
@app.get("/api/orders/unshipped", response_model=SelroOrderResponse)
async def get_unshipped_orders(api_key: str = Depends(verify_api_key)):
    """
    Get all unshipped orders from Selro
    """
    try:
        result = selro_client.fetch_all_orders(status="Unshipped")
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


# @app.get("/api/orders/{status}", response_model=SelroOrderResponse)
# async def get_orders_by_status(status: str, api_key: str = Depends(verify_api_key)):
#     """
#     Get all orders with a specific status from Selro
#     """
#     valid_statuses = [
#         "Shipped",
#         "Canceled",
#         "Pending",
#         "Unshipped",
#         "Draft",
#         "Processing",
#         "Unconfirmed",
#     ]
#     if status not in valid_statuses:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
#         )

#     try:
#         result = selro_client.fetch_all_orders(status=status)
#         return result
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"An error occurred: {str(e)}",
#         )


if __name__ == "__main__":
    import uvicorn

    # Load configurations from environment or use defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # Check if API credentials are set
    if not SELRO_KEY or not SELRO_SECRET or not API_AUTH_TOKEN:
        print(
            "ERROR: Missing required environment variables. Please set SELRO_KEY, SELRO_SECRET, and API_AUTH_TOKEN."
        )
        exit(1)

    # Run the FastAPI app
    uvicorn.run("main:app", host=host, port=port, reload=True)
