# Clover POS Integration Module
import os
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logger
log = logging.getLogger("realtime_restaurant_agent")


class CloverClient:
    """
    Clover POS API Client for restaurant order integration.
    
    Handles creating orders and adding line items to Clover POS system.
    """
    
    def __init__(
        self,
        merchant_id: str = None,
        access_token: str = None,
        base_url: str = None
    ):
        """
        Initialize Clover API client.
        
        Args:
            merchant_id: Clover merchant ID (defaults to env var)
            access_token: Clover API access token (defaults to env var)
            base_url: Clover API base URL (defaults to env var or sandbox)
        """
        self.merchant_id = merchant_id or os.getenv("CLOVER_MERCHANT_ID")
        self.access_token = access_token or os.getenv("CLOVER_ACCESS_TOKEN")
        self.base_url = base_url or os.getenv(
            "CLOVER_BASE_URL",
            "https://sandbox.dev.clover.com"
        )
        
        if not self.merchant_id:
            log.error("🔍 DEBUG: CLOVER_MERCHANT_ID not found in environment")
            raise ValueError("CLOVER_MERCHANT_ID environment variable not set")
        if not self.access_token:
            log.error("🔍 DEBUG: CLOVER_ACCESS_TOKEN not found in environment")
            raise ValueError("CLOVER_ACCESS_TOKEN environment variable not set")
        
        log.info(f"🔍 DEBUG: Clover client initialized - merchant: {self.merchant_id}, base_url: {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_order(
        self,
        phone: str,
        items: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Create a complete order in Clover POS with items.
        
        Args:
            phone: Customer phone number
            items: List of items [{"name": str, "price": float, "quantity": int}]
        
        Returns:
            Clover order ID if successful, None if failed
        """
        try:
            # 🔍 DEBUG: Entry point
            log.info(f"🔍 DEBUG: Clover create_order - phone={phone}, items={items}")
            
            # Step 1: Create the order (simplified - only phone needed)
            log.info(f"🔍 DEBUG: Creating base order...")
            order_id = await self._create_order_base(phone)
            if not order_id:
                log.error("Failed to create base order in Clover")
                return None
            
            log.info(f"🔍 DEBUG: Base order created: {order_id}")
            
            # Step 2: Add line items to the order
            log.info(f"🔍 DEBUG: Adding {len(items)} items to order...")
            success = await self._add_line_items(order_id, items)
            if not success:
                log.error(f"Failed to add items to Clover order {order_id}")
                return None
            
            log.info(f"🔍 DEBUG: Items added successfully")
            log.info(f"✅ Clover order complete: {order_id}")
            
            # Step 3: (Optional) Fire order to kitchen - uncomment if needed
            # await self._fire_order(order_id)
            
            return order_id
            
        except Exception as e:
            log.error(f"Clover order creation failed: {e}")
            import traceback
            log.error(f"🔍 DEBUG: Clover traceback: {traceback.format_exc()}")
            return None
    
    async def _create_order_base(
        self,
        phone: str
    ) -> Optional[str]:
        """
        Create base order in Clover (optimized - only phone number).
        
        Args:
            phone: Customer phone number
        
        Returns:
            Order ID if successful, None otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}/orders"
        
        # Simple order title - just "Phone Order"
        title = "Phone Order"
        
        # Phone number in note
        note = f"Phone: {phone}"
        
        payload = {
            "state": "open",
            "title": title,
            "note": note
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("id")
                    else:
                        error_text = await response.text()
                        log.error(f"Clover API error ({response.status}): {error_text}")
                        return None
        except Exception as e:
            log.error(f"Error creating Clover order: {e}")
            return None
    
    async def _add_line_items(
        self,
        order_id: str,
        items: List[Dict[str, Any]]
    ) -> bool:
        """
        Add line items (dishes) to an existing order.
        
        Args:
            order_id: Clover order ID
            items: List of items with name, price, quantity
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}/orders/{order_id}/bulk_line_items"
        
        # Convert items to Clover format
        # Clover expects:
        # - Prices in CENTS (multiply by 100)
        # - Quantities in units of 1000 (multiply by 1000)
        clover_items = []
        for item in items:
            clover_items.append({
                "name": item["name"],
                "price": int(item["price"] * 100),  # Convert dollars to cents
                "unitQty": int(item["quantity"] * 1000)  # Convert to Clover unit format
            })
        
        payload = {"items": clover_items}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        log.error(f"Clover add items error ({response.status}): {error_text}")
                        return False
        except Exception as e:
            log.error(f"Error adding items to Clover order: {e}")
            return False
    
    async def _fire_order(self, order_id: str) -> bool:
        """
        Fire order to kitchen (optional - sends order to kitchen display).
        
        Args:
            order_id: Clover order ID
        
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}/orders/{order_id}/fire"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        log.info(f"Order {order_id} fired to kitchen")
                        return True
                    else:
                        error_text = await response.text()
                        log.warning(f"Failed to fire order ({response.status}): {error_text}")
                        return False
        except Exception as e:
            log.warning(f"Error firing order to kitchen: {e}")
            return False
    
    async def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Search for a customer by phone number in Clover.
        
        Args:
            phone: Customer phone number to search for
        
        Returns:
            Customer data (including name) if found, None otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}/customers"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search customers with phone number filter
                params = {"filter": f"phoneNumber={phone}"}
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Clover returns a list of customers
                        customers = data.get("elements", [])
                        if customers:
                            # Return the first matching customer
                            customer = customers[0]
                            log.info(f"✅ Found customer in Clover: {customer.get('firstName', '')} {customer.get('lastName', '')}")
                            return customer
                        else:
                            log.info(f"No customer found in Clover with phone: {phone}")
                            return None
                    else:
                        error_text = await response.text()
                        log.warning(f"Clover customer search error ({response.status}): {error_text}")
                        return None
        except Exception as e:
            log.warning(f"Error searching for customer in Clover: {e}")
            return None
    
    async def create_customer(
        self,
        phone: str,
        name: str
    ) -> Optional[str]:
        """
        Create a new customer in Clover's customer database.
        
        Args:
            phone: Customer phone number
            name: Customer full name (will be split into first/last)
        
        Returns:
            Customer ID if successful, None otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}/customers"
        
        # Split name into first and last name
        name_parts = name.strip().split(maxsplit=1)
        first_name = name_parts[0] if len(name_parts) > 0 else name
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "phoneNumbers": [
                {
                    "phoneNumber": phone
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        customer_id = data.get("id")
                        log.info(f"✅ Created customer in Clover: {first_name} {last_name} (ID: {customer_id})")
                        return customer_id
                    else:
                        error_text = await response.text()
                        log.error(f"Clover customer creation error ({response.status}): {error_text}")
                        return None
        except Exception as e:
            log.error(f"Error creating customer in Clover: {e}")
            return None
    
    async def get_or_create_customer(
        self,
        phone: str,
        name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get customer by phone, or create if doesn't exist (and name is provided).
        
        Args:
            phone: Customer phone number
            name: Customer name (required for creation if customer doesn't exist)
        
        Returns:
            Customer data if found or created, None otherwise
        """
        # First, try to get existing customer
        customer = await self.get_customer_by_phone(phone)
        
        if customer:
            return customer
        
        # If not found and name is provided, create new customer
        if name:
            customer_id = await self.create_customer(phone, name)
            if customer_id:
                # Fetch the newly created customer to return full data
                return await self.get_customer_by_phone(phone)
        
        return None
    
    async def get_merchant_info(self) -> Optional[Dict[str, Any]]:
        """
        Get merchant information (useful for testing connection).
        
        Returns:
            Merchant data if successful, None otherwise
        """
        url = f"{self.base_url}/v3/merchants/{self.merchant_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        log.error(f"Failed to get merchant info ({response.status}): {error_text}")
                        return None
        except Exception as e:
            log.error(f"Error getting merchant info: {e}")
            return None


# Singleton instance (optional - for easy access)
_clover_client = None


def get_clover_client() -> CloverClient:
    """
    Get or create singleton Clover client instance.
    
    Returns:
        CloverClient instance
    """
    global _clover_client
    if _clover_client is None:
        _clover_client = CloverClient()
    return _clover_client

