# Call Termination Issues and Fix

## Problem Analysis

The original codebase had several critical issues that prevented proper call termination when multiple calls were received simultaneously:

### **Root Causes:**

1. **Global State Management Issues**
   - Used global variables `current_agent` and `current_job_context` that get overwritten with each new call
   - When multiple calls arrive, the global variables point to the most recent call, causing termination logic to operate on the wrong call

2. **Shared Termination Logic**
   - The `create_order` function relied on global `current_agent` variable
   - Termination logic used global `current_job_context` which could be from a different call
   - This caused calls to interfere with each other's termination process

3. **Session Context Confusion**
   - Multiple termination methods tried to use the wrong session/room context
   - Calls could not properly identify which session they belonged to

## **Solution Implemented**

### **1. Agent-Scoped State Management**
- Modified `RestaurantAgent` to store its own `job_context` instead of relying on global variables
- Each agent instance now manages its own termination state independently

### **2. Factory Pattern for Tool Creation**
- Created `create_order_tool_factory()` function that binds the `create_order` tool to a specific agent instance
- This ensures each call uses its own agent's state, not global state

### **3. Updated Termination Logic**
- Modified `_terminate_call_after_delay()` to use the agent's own `job_context` instead of global `current_job_context`
- All termination methods now operate on the correct call's context

### **4. Backward Compatibility**
- Kept global variables for backward compatibility but added warnings about their problematic nature
- The system now works correctly for both single and multiple concurrent calls

## **Key Changes Made**

### **1. Agent Constructor**
```python
class RestaurantAgent(Agent):
    def __init__(self, job_context=None):
        # Create a bound create_order tool for this specific agent instance
        create_order_tool = create_order_tool_factory(self)
        
        super().__init__(
            instructions=combined_instructions,
            tools=[create_order_tool],
        )
        # ... other initialization ...
        self.job_context = job_context  # Store job context per agent instance
```

### **2. Factory Function for Tools**
```python
def create_order_tool_factory(agent_instance):
    """Factory function to create a create_order tool bound to a specific agent instance"""
    
    @function_tool()
    async def create_order(items, phone=None, name=None, address=None):
        # Use agent_instance instead of global current_agent
        if agent_instance and agent_instance.order_placed:
            # ... handle order already placed ...
        
        # ... order creation logic ...
        
        # Schedule termination using the specific agent instance
        if agent_instance:
            asyncio.create_task(agent_instance._terminate_call_after_delay())
    
    return create_order
```

### **3. Updated Termination Logic**
```python
async def _terminate_call_after_delay(self):
    # Use the agent's own job context instead of global
    job_context = self.job_context
    
    # ... termination logic using job_context instead of global current_job_context ...
```

### **4. Entrypoint Update**
```python
async def entrypoint(ctx: JobContext):
    # Pass job context to agent constructor
    agent = RestaurantAgent(job_context=ctx)
    # ... rest of initialization ...
```

## **Benefits of the Fix**

1. **Isolated Call Management**: Each call now manages its own state independently
2. **Proper Termination**: Calls terminate correctly even when multiple calls are active
3. **No Race Conditions**: Global variable conflicts are eliminated
4. **Scalable**: System can handle multiple concurrent calls without interference
5. **Backward Compatible**: Existing functionality is preserved

## **Testing Recommendations**

1. **Single Call Test**: Verify that a single call terminates properly after order placement
2. **Multiple Call Test**: Test with 2-3 simultaneous calls to ensure each terminates independently
3. **Concurrent Order Test**: Verify that multiple calls can place orders without interfering with each other
4. **Termination Timing Test**: Ensure calls terminate after appropriate delays for user experience

## **Monitoring**

The fix includes extensive logging to help monitor the termination process:
- Agent-specific job context logging
- Termination method success/failure tracking
- Session state monitoring
- Participant disconnection status

This will help identify any remaining issues and ensure the system works correctly under load.
