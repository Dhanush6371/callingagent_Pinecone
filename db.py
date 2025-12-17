# Import OS module for environment variable access
import os

# Load environment variables from a .env file
from dotenv import load_dotenv

# MongoDB client and error classes
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Typing helper for optional return values
from typing import Optional, List, Dict, Any
import logging

# Import datetime for timestamps
from datetime import datetime

# Import Clover integration
CLOVER_ENABLED = False
_clover_import_error = None

try:
    from clover import get_clover_client
    CLOVER_ENABLED = True
except Exception as e:
    _clover_import_error = str(e)
    # Don't log here - will log later when actually used

# ---------- Load .env file and initialize MongoDB URI ----------

# Load environment variables from the .env file into the environment
load_dotenv()

# Retrieve MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")

# ---------- MongoDB Connection Setup ----------

try:
    # Initialize MongoDB client with the URI
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable not set.")
    
    # Disable MongoDB logs by setting logging level
    import logging
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("pymongo.connection").setLevel(logging.WARNING)
    logging.getLogger("pymongo.pool").setLevel(logging.WARNING)
    logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)
    
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    # Access the 'restaurant' database
    db = client["bhawarchi"]

    # Access the 'orders' collection within the 'restaurant' database
    orders_collection = db["orders"]

except (PyMongoError, ValueError) as e:
    # Re-raise, but also log for visibility
    logging.getLogger("realtime_restaurant_agent").error(f"Mongo init failed: {e}")
    raise

# ---------- Order Database Driver Class ----------

class DatabaseDriver:
    def __init__(self):
        # Initialize the collection reference to use in other methods
        self.collection = orders_collection
        self.log = logging.getLogger("realtime_restaurant_agent")
        self._indexes_created = False
        
        # Don't create indexes here - do it lazily on first use to avoid blocking
    
    def _ensure_indexes(self):
        """Create indexes lazily (only once, non-blocking)"""
        if not self._indexes_created:
            try:
                # Create indexes in background (non-blocking)
                self.collection.create_index("phone", background=True)
                self.collection.create_index("created_at", background=True)
                self._indexes_created = True
            except Exception:
                # Silently ignore - indexes are optional optimization
                pass

    # Create a new order in the MongoDB collection
    def create_order(self, phone: str, items: List[Dict[str, Any]], name: str = None, address: str = None, caller_phone: str = None) -> Optional[dict]:
        # Ensure indexes exist (lazy, non-blocking)
        self._ensure_indexes()
        
        self.log.info(f"Database: Received phone parameter: {phone}")
        self.log.info(f"Database: Phone parameter type: {type(phone)}")
        self.log.info(f"Database: Phone parameter is None: {phone is None}")
        self.log.info(f"Database: Phone parameter == 'unknown': {phone == 'unknown'}")
        
        # NEVER allow "unknown" phone numbers - always use a fallback
        if not phone or phone == "unknown":
            import time
            phone = f"call_{int(time.time())}"
            self.log.info(f"Database: Replaced 'unknown' with fallback phone: {phone}")
        
        self.log.info(f"Database: Final phone number for order: {phone}")
        
        order = {
            "phone": phone,
            "items": items,
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "order_type": "phone_only"  # Indicates this is a phone-only order
        }
        
        # Add optional fields if provided
        if name:
            order["name"] = name
        if address:
            order["address"] = address
        
        # Add caller phone number if available
        if caller_phone:
            order["caller_phone"] = caller_phone
            order["phone_source"] = "extracted_from_call"
        else:
            order["phone_source"] = "provided_by_customer"
        
        try:
            self.log.info(f"Database: Inserting order with phone: {order.get('phone')}")
            self.log.info(f"Database: Full order document: {order}")
            # Insert the order document into the MongoDB collection
            result = self.collection.insert_one(order)
            self.log.info(f"Database: Insert result: {result.inserted_id}")
            
            # Add MongoDB ID to order for reference
            order["_id"] = str(result.inserted_id)
            
            return order
        except PyMongoError as e:
            self.log.error(f"Database: Insert failed: {e}")
            return None
    
    # Create order and sync to Clover POS (async version)
    async def create_order_with_clover(self, phone: str, items: List[Dict[str, Any]], name: str = None, address: str = None, caller_phone: str = None) -> Optional[dict]:
        """
        Create order in MongoDB and sync to Clover POS.

        This is an async wrapper that:
        1. Saves order to MongoDB (your database)
        2. Sends order to Clover POS (restaurant system)

        NOTE:
        - The `name` field is only stored in MongoDB for your own records.
        - Clover POS orders are created with **phone + items only**; the
          customer name is NOT sent as part of the Clover order payload.
        - Customer creation/updates in Clover (for greetings, etc.) are
          handled separately at the agent level after the order is placed.
        
        Args:
            phone: Customer phone number
            items: List of order items
            name: Customer name (optional – stored only in MongoDB)
            address: Delivery address (optional – stored only in MongoDB)
            caller_phone: Extracted caller phone (optional)
        
        Returns:
            Order document if successful, None otherwise
        """
        # 🔍 DEBUG: Entry point
        self.log.info(f"🔍 DEBUG: create_order_with_clover called - phone={phone}, name={name}, items_count={len(items)}")
        
        # Step 1: Save to MongoDB (always do this)
        order = self.create_order(phone, items, name, address, caller_phone)
        
        if not order:
            self.log.error("Failed to save order to MongoDB")
            return None
        
        # 🔍 DEBUG: MongoDB save status
        self.log.info(f"🔍 DEBUG: MongoDB save OK, order_id={order.get('_id')}")
        
        # Step 2: Sync to Clover POS (don't fail if this doesn't work)
        # 🔍 DEBUG: Check if Clover is enabled
        if CLOVER_ENABLED:
            self.log.info(f"🔍 DEBUG: ✅ Clover integration ENABLED")
        else:
            self.log.warning(f"🔍 DEBUG: ⚠️ Clover integration DISABLED - {_clover_import_error or 'check .env file'}")
        
        if CLOVER_ENABLED:
            try:
                self.log.info(f"🔍 DEBUG: Getting Clover client...")
                clover_client = get_clover_client()
                
                self.log.info(f"🔍 DEBUG: Calling clover_client.create_order...")
                clover_order_id = await clover_client.create_order(
                    phone=phone,
                    items=items
                )
                
                self.log.info(f"🔍 DEBUG: Clover API returned: {clover_order_id}")
                
                if clover_order_id:
                    self.log.info(f"✅ Order synced to Clover POS: {clover_order_id}")
                    # Update MongoDB with Clover order ID
                    try:
                        from bson.objectid import ObjectId
                        self.collection.update_one(
                            {"_id": ObjectId(order["_id"])},
                            {"$set": {"clover_order_id": clover_order_id}}
                        )
                        order["clover_order_id"] = clover_order_id
                    except Exception as e:
                        self.log.warning(f"Could not update Clover order ID in MongoDB: {e}")
                else:
                    self.log.warning("⚠️ Failed to sync order to Clover (order saved in MongoDB)")
            except Exception as e:
                self.log.error(f"⚠️ Clover sync error: {e} (order saved in MongoDB)")
                import traceback
                self.log.error(f"🔍 DEBUG: Traceback: {traceback.format_exc()}")
        else:
            self.log.warning("🔍 DEBUG: Clover integration DISABLED - check .env file")
        
        return order
    
    # Get customer name by phone number from Clover only
    async def get_customer_name_by_phone(self, phone: str) -> Optional[str]:
        """
        Get customer name by phone number from Clover only.
        
        Args:
            phone: Customer phone number
        
        Returns:
            Customer name if found in Clover, None otherwise
        """
        # Check Clover customers database
        if CLOVER_ENABLED:
            try:
                clover_client = get_clover_client()
                customer = await clover_client.get_customer_by_phone(phone)
                if customer:
                    # Combine first and last name
                    first_name = customer.get("firstName", "")
                    last_name = customer.get("lastName", "")
                    full_name = f"{first_name} {last_name}".strip()
                    if full_name:
                        self.log.info(f"✅ Found customer name in Clover: {full_name}")
                        return full_name
            except Exception as e:
                self.log.warning(f"Error checking Clover for customer name: {e}")
        
        return None

    # Retrieve an order document by phone number
    def get_order_by_phone(self, phone: str) -> Optional[dict]:
        try:
            # Search for an order with the matching phone number, get the most recent one
            order = self.collection.find_one({"phone": phone}, sort=[("_id", -1)])
            return order
        except PyMongoError:
            return None
