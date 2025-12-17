# Phone Number Extraction & Simplified Order System

## Overview

This document describes the implementation of automatic phone number extraction from incoming calls and the simplified order system in the Bawarchi Restaurant calling agent. The system now automatically retrieves the caller's phone number from the LiveKit SIP session and creates orders using only the phone number as the base key, without requiring personal details from customers.

## Implementation Details

### 1. Phone Number Extraction Logic

The phone number extraction is implemented in the `entrypoint()` function in `agent.py`. The system attempts to extract the caller's phone number from three sources:

1. **Participant ID**: Extracts phone number from participant ID format (e.g., `sip_+919182367798`)
2. **SIP Participant Attributes**: Checks for `sip.phoneNumber` in participant attributes
3. **Participant Metadata**: Checks for `phoneNumber` or `from` fields in participant metadata

```python
# Extract caller phone number from room participants
caller_phone = None
try:
    room = ctx.room
    if room:
        participants = room.remote_participants
        for participant_id, participant in participants.items():
            # Extract phone number from participant ID (format: sip_+919182367798)
            if participant_id.startswith('sip_'):
                phone_from_id = participant_id.replace('sip_', '')
                if phone_from_id.startswith('+'):
                    caller_phone = phone_from_id
                    break
            
            # Check SIP attributes
            if hasattr(participant, 'attributes') and participant.attributes:
                sip_phone = participant.attributes.get('sip.phoneNumber')
                if sip_phone:
                    caller_phone = sip_phone
                    break
            
            # Check metadata
            if hasattr(participant, 'metadata') and participant.metadata:
                phone_metadata = participant.metadata.get('phoneNumber') or participant.metadata.get('from')
                if phone_metadata:
                    caller_phone = phone_metadata
                    break
except Exception as e:
    log.error(f"Failed to extract caller phone number: {e}")
```

### 2. Agent Storage

The extracted phone number is stored in the agent instance for later use:

```python
if caller_phone:
    agent.caller_phone = caller_phone
    log.info(f"Caller phone number stored in agent: {caller_phone}")
```

### 3. Automatic Phone Number Usage in Orders

The system automatically uses the extracted caller phone number when creating orders. This is implemented through:

1. **Tool Execution Override**: The `RestaurantAgent._execute_tool()` method intercepts the `create_order` function call
2. **Phone Number Replacement**: If a caller phone number is available, it replaces the phone number provided by the customer
3. **Database Storage**: Both the original and extracted phone numbers are stored in the database

```python
async def _execute_tool(self, tool_call, session):
    if tool_call.function.name == "create_order":
        caller_phone = self.caller_phone
        
        if caller_phone:
            args = json.loads(tool_call.function.arguments)
            args["phone"] = caller_phone
            args["caller_phone"] = caller_phone
            tool_call.function.arguments = json.dumps(args)
```

### 4. Simplified Order System

The system now creates orders with minimal required information:

```python
order = {
    "phone": phone,  # Primary key - extracted from caller
    "items": items,  # Required - order items with quantity and price
    "status": "confirmed",
    "created_at": datetime.now().isoformat(),
    "order_type": "phone_only",  # Indicates simplified order
    "caller_phone": caller_phone,  # Original extracted phone number
    "phone_source": "extracted_from_call",
    # Optional fields (only if customer provides them):
    "name": name,  # Optional
    "address": address  # Optional
}
```

### 5. Database Schema Updates

The database schema has been updated to support phone-only orders:

- **Required Fields**: `phone`, `items`, `status`, `created_at`, `order_type`
- **Optional Fields**: `name`, `address` (only stored if customer provides them)
- **System Fields**: `caller_phone`, `phone_source` (for tracking and debugging)

### 6. Agent Instructions Updates

The agent prompts have been updated to reflect the simplified order process:

- **Primary Focus**: Collect order items first (most important information)
- **Optional Details**: Name and address are optional, don't pressure customers
- **Automatic Phone**: System automatically detects caller's phone number
- **Simplified Confirmation**: Only confirm order items and any optional details provided
- **Streamlined Response**: Simplified confirmation messages

## Files Modified

1. **`agent.py`**:
   - Added phone number extraction logic in `entrypoint()` function
   - Added `_execute_tool()` override to inject caller phone number
   - Updated `create_order` function to use simplified signature (items first, optional details)
   - Moved phone extraction to entrypoint for proper room access

2. **`db.py`**:
   - Updated `create_order()` method to support phone-only orders
   - Made name and address optional parameters
   - Added `order_type` field to track simplified orders
   - Added timestamp and phone source tracking

3. **`prompts.py`**:
   - Updated agent instructions to focus on order items first
   - Made personal details (name, address) optional
   - Simplified confirmation process
   - Updated order creation instructions

4. **`PHONE_NUMBER_EXTRACTION.md`** (updated):
   - Comprehensive documentation of the phone extraction and simplified order system
   - Updated to reflect the new phone-only order process

## Testing

The implementation has been tested and verified to work correctly:

- ✅ Phone number extraction from participant ID format (`sip_+919182367798`)
- ✅ Phone number extraction from SIP attributes
- ✅ Phone number extraction from participant metadata
- ✅ Simplified order creation with phone-only data
- ✅ Optional name and address handling
- ✅ Database storage with proper schema
- ✅ Agent tool execution with phone number injection

The system successfully creates orders using only the phone number as the base key, with all other details being optional.

## Usage Flow

1. **Incoming Call**: Customer calls the restaurant
2. **Phone Extraction**: System automatically extracts caller's phone number from SIP session
3. **Agent Storage**: Phone number is stored in agent instance
4. **Order Collection**: Agent focuses on collecting order items first
5. **Optional Details**: Agent optionally collects name/address if customer provides them
6. **Order Processing**: System creates order using extracted phone number as base key
7. **Database Storage**: Order is saved with phone number and items (minimal required data)
8. **Confirmation**: Customer receives simplified confirmation message

## Benefits

1. **Automatic Detection**: No need for customers to manually provide phone numbers
2. **Privacy-Friendly**: Customers don't need to provide personal details
3. **Faster Processing**: Streamlined order collection focuses on items first
4. **Reduced Friction**: Optional personal details reduce customer hesitation
5. **Accuracy**: Eliminates errors from manual phone number entry
6. **Audit Trail**: Complete tracking of phone number sources
7. **Fallback Support**: Still works if phone number extraction fails

## Error Handling

The system includes robust error handling:

- Graceful fallback if phone number extraction fails
- Logging of all extraction attempts and results
- Continues normal operation even without phone number extraction
- Database stores phone source information for debugging

## Future Enhancements

Potential improvements for the future:

1. **Phone Number Validation**: Add validation for extracted phone numbers
2. **Multiple Phone Numbers**: Handle cases with multiple phone numbers
3. **Phone Number Formatting**: Standardize phone number formats
4. **Integration with CRM**: Link extracted phone numbers with customer database
5. **Analytics**: Track phone number extraction success rates
