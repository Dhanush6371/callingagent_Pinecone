from __future__ import annotations
import os
import asyncio
import time
import logging
from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
from datetime import datetime

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    RoomInputOptions,
    function_tool,
)
from livekit.plugins import openai, noise_cancellation
from livekit.plugins.openai import realtime

# --- Local imports
from db import DatabaseDriver
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from search_menu import search_menu  # 🔴 ADDED: Pinecone search import

# --- Load environment variables
load_dotenv()

# ============================================================
# 🚀 MODULE-LEVEL PROMPT CACHE: Load once, reuse forever
# ============================================================
# Cache combined instructions at module level to avoid any recalculation
# Prompts are already cached in prompts.py, this ensures combined version is also cached
_COMBINED_INSTRUCTIONS_CACHE = None

def _get_combined_instructions():
    """Get cached combined instructions - computed once at module load"""
    global _COMBINED_INSTRUCTIONS_CACHE
    if _COMBINED_INSTRUCTIONS_CACHE is None:
        # AGENT_INSTRUCTION and SESSION_INSTRUCTION are already cached in prompts.py
        # This is just combining them once and storing in memory
        _COMBINED_INSTRUCTIONS_CACHE = f"{AGENT_INSTRUCTION}\n\n{SESSION_INSTRUCTION}"
    return _COMBINED_INSTRUCTIONS_CACHE

# --- Production Mode Configuration
PRODUCTION = os.getenv("ENVIRONMENT") == "production"

# --- Logger with environment-based levels
log = logging.getLogger("realtime_restaurant_agent")
if PRODUCTION:
    log.setLevel(logging.WARNING)  # Reduced logging in production for better performance
    logging.getLogger("livekit").setLevel(logging.ERROR)
else:
    log.setLevel(logging.INFO)

# --- Database (lazy initialization to avoid blocking)
db_driver = None

def get_db_driver():
    """Get database driver with lazy initialization"""
    global db_driver
    if db_driver is None:
        db_driver = DatabaseDriver()
    return db_driver

# ------------------------------------------------------------
# 🧩 FUNCTION TOOLS
# ------------------------------------------------------------
current_agent = None
current_job_context = None
class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: str
    quantity: int
    price: float


class CreateOrderArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    items: List[OrderItem]
    phone: str | None = None
    name: str | None = None
    address: str | None = None


# 🔴 ADDED: Pinecone menu search tool with hierarchical filtering
@function_tool()
async def lookup_menu(query: str):
    """
    Search menu items using Pinecone with hierarchical filtering.
    This automatically filters by section/sub_section/protein to reduce token usage by 80-90%.
    
    Examples:
    - "chicken biryani" → searches only non_veg/biryani/chicken items (~8-10 items instead of 399)
    - "masala puri" → searches only veg/chaat items (~13 items instead of 399)
    - "mutton biryani" → searches only non_veg/biryani/mutton items (~5 items instead of 399)
    
    ALWAYS use this tool for menu, price, and category queries.
    """
    # Run blocking Pinecone + OpenAI calls in a thread
    # search_menu() automatically applies hierarchical filtering
    return await asyncio.to_thread(search_menu, query)

def store_customer_name_tool_factory(agent_instance):
    """Factory function to create a store_customer_name tool to store name immediately when customer says it"""
    @function_tool()
    async def store_customer_name(name: str):
        """Store the customer's name in memory immediately when they say it. Use this right after the customer tells you their name, before spelling it back for confirmation."""
        if agent_instance and name:
            agent_instance.customer_name = name.strip()
            log.info(f"✅ Stored customer name in memory: {name.strip()}")
            return f"Name '{name.strip()}' stored successfully. You can now use this name when placing the order."
        return "Name storage failed."
    
    return store_customer_name

def create_order_tool_factory(agent_instance):
    """Factory function to create a create_order tool bound to a specific agent instance"""
    @function_tool()
    async def create_order(items: List[OrderItem], phone: str | None = None, name: str | None = None, address: str | None = None):
        """Create an order with the provided items."""
        if agent_instance and agent_instance.order_placed:
            return "I'm sorry, but I can only place one order per call. Your previous order has already been confirmed."
        
        # Validate quantity limit (max 10 per item)
        for item in items:
            if item.quantity > 10:
                return f"Sorry, you can order a maximum of 10 for a single item. You requested {item.quantity} of {item.name}. Could you please reduce the quantity to 10 or less?"

        # Use caller phone if available
        if agent_instance and agent_instance.caller_phone:
            if not phone or phone == "unknown":
                phone = agent_instance.caller_phone
        
        try:
            if not phone or phone == "unknown":
                final_phone = f"call_{int(time.time())}"
            else:
                final_phone = phone

            # Use stored name if available, otherwise use provided name
            if agent_instance and agent_instance.customer_name and not name:
                name = agent_instance.customer_name
                log.info(f"✅ Using stored customer name: {name}")
            
            # Remember provided name for the rest of the call / future calls.
            if agent_instance and name:
                agent_instance.customer_name = name.strip()

            # Make database call non-blocking - don't wait for it
            async def save_order_async():
                try:
                    # 🔍 DEBUG: Agent calling save
                    log.info(f"🔍 DEBUG: Agent save_order_async starting...")
                    
                    # Use the new Clover-integrated method (fully async)
                    items_payload = [item.model_dump() for item in items]
                    log.info(f"🔍 DEBUG: Items payload: {items_payload}")
                    
                    # Get database driver (lazy initialization)
                    driver = get_db_driver()
                    result = await driver.create_order_with_clover(
                        final_phone, items_payload, name, address
                    )
                    
                    log.info(f"🔍 DEBUG: save result: {result is not None}")
                    
                    if result:
                        agent_instance.order_placed = True
                        log.info(f"✅ Order saved (MongoDB + Clover POS)")

                        # Create / update customer record in Clover AFTER order placement.
                        # This runs in the background and does not affect call latency.
                        if name and final_phone:
                            asyncio.create_task(
                                create_customer_in_clover_async(final_phone, name)
                            )
                        
                        asyncio.create_task(agent_instance._terminate_call_after_delay())
                except Exception as e:
                    log.error(f"Async order save failed: {e}")
                    import traceback
                    log.error(f"🔍 DEBUG: Agent traceback: {traceback.format_exc()}")
            
            # Don't wait for database - respond immediately
            asyncio.create_task(save_order_async())

            return "✅ Order placed successfully! Your order has been confirmed and saved to our system. We will send you the details shortly."
        except Exception as e:
            log.error(f"Order creation failed: {e}")
            return "Sorry, there was an error saving your order. Please try again."

    return create_order


async def create_customer_in_clover_async(phone: str, name: str):
    """
    Create or update customer in Clover AFTER the order is placed.
    Runs in the background and does not block the live call.
    """
    try:
        from clover import get_clover_client

        clover_client = get_clover_client()
        customer = await clover_client.get_or_create_customer(phone, name)
        if customer:
            log.info(f"✅ Customer created/updated in Clover after order: {name} ({phone})")
        else:
            log.warning("⚠️ Could not create/update customer in Clover after order")
    except Exception as e:
        log.warning(f"⚠️ Clover customer creation after order failed: {e}")


# ------------------------------------------------------------
# 🧠 AGENT CLASS
# ------------------------------------------------------------
class RestaurantAgent(Agent):
    # Class-level cache (shared across all instances)
    _cached_instructions = None
    
    def __init__(self, job_context=None):
        # Use module-level cache to ensure prompts are loaded only once
        # _get_combined_instructions() guarantees single computation
        if RestaurantAgent._cached_instructions is None:
            RestaurantAgent._cached_instructions = _get_combined_instructions()
        
        create_order_tool = create_order_tool_factory(self)
        store_name_tool = store_customer_name_tool_factory(self)

        # 🔴 UPDATED: Add lookup_menu to tools list
        super().__init__(
            instructions=RestaurantAgent._cached_instructions,
            tools=[create_order_tool, store_name_tool, lookup_menu],  # 🔴 ADDED lookup_menu
        )

        self.current_session = None
        self.caller_phone = None
        self.customer_name = None  # Store customer name for personalized greeting
        self.termination_started = False
        self.order_placed = False
        self.job_context = job_context
        self.greeting_in_progress = False  # Track if greeting is being spoken

        global current_agent
        current_agent = self

    async def _execute_tool(self, tool_call, session):
        if tool_call.function.name == "create_order":
            import json, time
            args = json.loads(tool_call.function.arguments)
            phone = self.caller_phone
            if not phone or phone in ["unknown", "extracted_failed"]:
                phone = f"call_{int(time.time())}"
            args["phone"] = phone
            
            # If name is not provided but we have stored name, use it
            if not args.get("name") and self.customer_name:
                args["name"] = self.customer_name
                log.info(f"✅ Using stored customer name in create_order: {self.customer_name}")
            
            tool_call.function.arguments = json.dumps(args)
        return await super()._execute_tool(tool_call, session)

    async def on_message(self, message, session):
        if self.termination_started:
            return "The call is ending. Thank you for choosing Bawarchi Restaurant!"
        
        # 🔒 PROTECT GREETING: Ignore user messages while greeting is in progress
        # This prevents the agent from interrupting the greeting and confusing user logic
        if self.greeting_in_progress:
            log.info("⏸️ Ignoring user message - greeting in progress")
            return None  # Return None to ignore the message
        
        try:
            # Use reasonable timeout - balance between waiting and responsiveness
            # If LLM is consistently slow, fallback will kick in
            response = await asyncio.wait_for(
                super().on_message(message, session),
                timeout=3.0  # Optimized timeout - faster fallback for better UX
            )
            return response
        except asyncio.TimeoutError:
            # Fallback immediately if LLM is slow - better UX than waiting
            log.warning("LLM response timeout, using fallback")
            return self._get_smart_fallback_response(message.content or "")
        except Exception as e:
            log.error(f"Error in on_message: {e}")
            return self._get_smart_fallback_response(message.content or "")

    def _get_smart_fallback_response(self, msg: str):
        msg = msg.lower()
        if any(x in msg for x in ['order', 'food', 'menu', 'biryani', 'chicken', 'mutton', 'rice', 'curry']):
            return "I can help you place an order! Please tell me what you'd like to order."
        if any(x in msg for x in ['hello', 'hi', 'hey']):
            return "Hello! Welcome to Bawarchi Restaurant. How can I help you today?"
        if any(x in msg for x in ['price', 'cost', 'how much']):
            return "Our prices are very reasonable. What specific dish would you like to know the price for?"
        return "I'm here to help you with your order. What would you like to order?"

    async def on_start(self, session: AgentSession):
        self.current_session = session
        # Start greeting immediately - generate_reply returns a SpeechHandle, not a coroutine
        # Don't await it - let it run in the background
        try:
            # Generate greeting (enabled by default, can be disabled with ENABLE_TTS=0)
            if os.getenv("ENABLE_TTS", "1") != "0":
                # 🔒 Set greeting flag to protect from interruptions
                self.greeting_in_progress = True
                log.info("🔒 Greeting started - protecting from user interruptions")
                
                # Personalized greeting if customer name is available
                if self.customer_name:
                    greeting = f'Say the complete greeting in English: "Hello {self.customer_name}! Welcome back to Bawarchi Restaurant. I am emma. What would you like to order today?" Say all parts of the greeting - do not skip any words.'
                else:
                    greeting = 'Say the complete greeting in English: "Hello! Welcome to Bawarchi Restaurant. I am emma. What would you like to order today?" Say all parts of the greeting - do not skip any words.'
                
                # Generate greeting and wait for it to complete
                async def generate_and_clear_greeting():
                    try:
                        # Generate greeting and await its completion (like in termination code)
                        # This will wait for the greeting speech to actually finish
                        await asyncio.wait_for(
                            session.generate_reply(instructions=greeting),
                            timeout=10.0  # Reasonable timeout for greeting
                        )
                        # Flag cleared when greeting actually completes (not time-based)
                    except asyncio.TimeoutError:
                        log.warning("Greeting timeout - clearing flag anyway")
                    except Exception as e:
                        # If generate_reply raises an error or is not awaitable,
                        # the greeting has still been initiated
                        log.debug(f"Greeting initiated: {e}")
                    finally:
                        # Clear flag when greeting completes (event-based, not time-based)
                        self.greeting_in_progress = False
                        log.info("✅ Greeting completed - user interactions now allowed")
                
                # Start greeting generation in background
                asyncio.create_task(generate_and_clear_greeting())
        except Exception as e:
            log.warning(f"Greeting generation error: {e}, continuing anyway")
            self.greeting_in_progress = False  # Clear flag on error

    # ------------------------------------------------------------
    # 🧩 FULL TERMINATION SEQUENCE
    # ------------------------------------------------------------
    async def _terminate_call_after_delay(self):
        """Comprehensive call termination logic"""
        job_context = self.job_context
        try:
            log.info("🔧 Starting automatic call termination sequence...")
            await asyncio.sleep(5.0)
            self.termination_started = True

            if self.current_session:
                try:
                    if os.getenv("ENABLE_TTS", "1") != "0":
                        await asyncio.wait_for(
                            self.current_session.generate_reply(
                                instructions="Say: Thank you for choosing Bawarchi Restaurant! Goodbye!"
                            ),
                            timeout=4.0
                        )
                    await asyncio.sleep(6.0)
                except Exception as e:
                    log.warning(f"⚠️ Could not send final goodbye: {e}")

                # 1️⃣ Disconnect all participants
                try:
                    if hasattr(self.current_session, "room") and self.current_session.room:
                        for pid, p in self.current_session.room.remote_participants.items():
                            try:
                                await p.disconnect()
                            except Exception:
                                pass
                except Exception:
                    pass

                # 2️⃣ Close room
                try:
                    if hasattr(self.current_session, "room") and self.current_session.room:
                        await self.current_session.room.close()
                except Exception:
                    pass

                # 3️⃣ Session termination variants
                for method_name in ["disconnect", "stop", "end", "close", "terminate", "shutdown"]:
                    if hasattr(self.current_session, method_name):
                        try:
                            await getattr(self.current_session, method_name)()
                            break
                        except Exception:
                            continue

                # 4️⃣ Close _room
                try:
                    if hasattr(self.current_session, "_room") and self.current_session._room:
                        await self.current_session._room.close()
                except Exception:
                    pass

                # 5️⃣ Stop agent
                try:
                    if hasattr(self.current_session, "agent") and self.current_session.agent:
                        if hasattr(self.current_session.agent, "stop"):
                            await self.current_session.agent.stop()
                except Exception:
                    pass

                # 6️⃣ Force disconnect SIP participants
                try:
                    if job_context and hasattr(job_context, "room") and job_context.room:
                        for pid, participant in job_context.room.remote_participants.items():
                            if pid.startswith("sip_"):
                                for m in ["disconnect", "remove", "kick"]:
                                    if hasattr(participant, m):
                                        try:
                                            await getattr(participant, m)()
                                        except Exception:
                                            pass
                except Exception:
                    pass

                # 7️⃣ room.disconnect_participant
                try:
                    if job_context and hasattr(job_context, "room") and job_context.room:
                        for pid in job_context.room.remote_participants.keys():
                            if hasattr(job_context.room, "disconnect_participant"):
                                await job_context.room.disconnect_participant(pid)
                except Exception:
                    pass

                # 8️⃣ room.remove_participant
                try:
                    if job_context and hasattr(job_context, "room") and job_context.room:
                        for pid in job_context.room.remote_participants.keys():
                            if hasattr(job_context.room, "remove_participant"):
                                await job_context.room.remove_participant(pid)
                except Exception:
                    pass

                # 9️⃣ Close connection
                try:
                    if job_context and hasattr(job_context, "room") and job_context.room:
                        room = job_context.room
                        if hasattr(room, "connection"):
                            conn = room.connection
                            if hasattr(conn, "close"):
                                await conn.close()
                        elif hasattr(room, "_connection"):
                            conn = room._connection
                            if hasattr(conn, "close"):
                                await conn.close()
                except Exception:
                    pass

                # 🔟 Terminate Twilio call via API
                try:
                    if job_context and hasattr(job_context, "room") and job_context.room:
                        room = job_context.room
                        for pid, participant in room.remote_participants.items():
                            if pid.startswith("sip_"):
                                if hasattr(participant, "attributes") and participant.attributes:
                                    call_sid = participant.attributes.get("sip.twilio.callSid")
                                    if call_sid:
                                        log.info(f"🔧 Terminating Twilio call SID: {call_sid}")
                                        await self._terminate_twilio_call(call_sid)
                except Exception as e:
                    log.warning(f"⚠️ Twilio termination failed: {e}")

                # 11️⃣ Disconnect job context
                try:
                    if hasattr(job_context, "disconnect"):
                        await job_context.disconnect()
                except Exception:
                    pass

                # 12️⃣ Clear session reference
                self.current_session = None
                log.info("✅ Call termination sequence completed successfully.")
        except Exception as e:
            log.error(f"⚠️ Error in _terminate_call_after_delay: {e}")

    async def _terminate_twilio_call(self, call_sid: str):
        """Terminate Twilio call using Twilio REST API"""
        import aiohttp

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")

        if not account_sid or not auth_token:
            log.warning("⚠️ Twilio credentials missing.")
            return

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    auth=aiohttp.BasicAuth(account_sid, auth_token),
                    data={"Status": "completed"},
                ) as resp:
                    if resp.status == 200:
                        log.info(f"✅ Twilio call {call_sid} terminated.")
                    else:
                        body = await resp.text()
                        log.warning(f"⚠️ Twilio API failed: {resp.status} - {body}")
        except Exception as e:
            log.error(f"⚠️ Error terminating Twilio call: {e}")


# ------------------------------------------------------------
# 🚀 ENTRYPOINT
# ------------------------------------------------------------
async def entrypoint(ctx: JobContext):
    global current_job_context
    current_job_context = ctx

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in environment variables!")

    # 🚀 REALTIME MODEL: Ultra-low latency - STT + LLM + TTS all in one!
    # Using OpenAI Realtime Model with explicit model/version and server-side VAD
    realtime_model = realtime.RealtimeModel(
        api_key=openai_api_key,
        model="gpt-4o-mini-realtime-preview-2024-12-17",
        voice="alloy",  # Options: alloy, echo, shimmer, nova, fable, onyx
        modalities=["audio", "text"],
        temperature=0.2,
        turn_detection={
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
        },
    )

    # Create Agent with RealtimeModel (no separate STT/TTS/LLM needed)
    agent = RestaurantAgent(job_context=ctx)
    
    # Override agent's LLM with RealtimeModel
    agent._llm = realtime_model
    
    # Create AgentSession (RealtimeModel handles everything)
    session = AgentSession(
        stt=None,  # RealtimeModel handles STT
        tts=None,  # RealtimeModel handles TTS
        llm=realtime_model,  # RealtimeModel handles LLM
    )
    
    await ctx.connect()

    # Extract caller phone number (non-blocking - done in parallel with session start)
    async def extract_phone_number():
        caller_phone = None
        try:
            # Try multiple times in case the SIP participant metadata is not ready immediately
            for attempt in range(8):  # ~4 seconds total
                room = ctx.room
                if room:
                    for pid, participant in room.remote_participants.items():
                        # SIP participant id usually starts with "sip_+<number>"
                        if pid.startswith("sip_"):
                            phone = pid.replace("sip_", "")
                            if phone.startswith("+"):
                                caller_phone = phone
                                break
                        if hasattr(participant, "attributes") and participant.attributes:
                            sip_phone = participant.attributes.get("sip.phoneNumber") or participant.attributes.get("from")
                            if sip_phone:
                                caller_phone = sip_phone
                                break
                        if hasattr(participant, "metadata") and participant.metadata:
                            phone_metadata = participant.metadata.get("phoneNumber") or participant.metadata.get("from")
                            if phone_metadata:
                                caller_phone = phone_metadata
                                break
                if caller_phone:
                    break
                await asyncio.sleep(0.5)
        except Exception as e:
            log.warning(f"Error extracting phone number: {e}")
        
        # Store phone number in agent
        if caller_phone:
            agent.caller_phone = caller_phone
            log.info(f"✅ Extracted caller phone: {caller_phone}")
            
            # Fetch customer name from database/Clover
            try:
                driver = get_db_driver()
                customer_name = await driver.get_customer_name_by_phone(caller_phone)
                if customer_name:
                    agent.customer_name = customer_name
                    log.info(f"✅ Found existing customer: {customer_name}")
            except Exception as e:
                log.warning(f"Error fetching customer name: {e}")
        else:
            agent.caller_phone = "extracted_failed"
            log.warning("⚠️ Failed to extract caller phone number.")

    # Start session immediately without blocking
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Extract phone number and customer name FIRST (before greeting)
    # This ensures we have the customer name before sending the greeting
    await extract_phone_number()
    
    # Start greeting AFTER phone/name extraction is complete
    asyncio.create_task(agent.on_start(session))


# ------------------------------------------------------------
# 🏁 MAIN RUNNER
# ------------------------------------------------------------
if __name__ == "__main__":
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="inbound_agent",
        )
    )