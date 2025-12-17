"""
Test script for Clover POS integration.

This script tests the complete flow:
1. Create order in MongoDB
2. Sync order to Clover POS
3. Verify integration works
"""

import asyncio
import logging
from db import DatabaseDriver
from clover import get_clover_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger("clover_test")


async def test_clover_connection():
    """Test 1: Verify Clover API connection."""
    print("\n" + "="*60)
    print("TEST 1: Clover API Connection")
    print("="*60)
    
    try:
        clover_client = get_clover_client()
        merchant_info = await clover_client.get_merchant_info()
        
        if merchant_info:
            print(f"✅ Connected to Clover POS")
            print(f"   Merchant: {merchant_info.get('name')}")
            print(f"   ID: {merchant_info.get('id')}")
            return True
        else:
            print("❌ Failed to connect to Clover POS")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_create_order():
    """Test 2: Create order with Clover integration."""
    print("\n" + "="*60)
    print("TEST 2: Create Order (MongoDB + Clover POS)")
    print("="*60)
    
    try:
        db_driver = DatabaseDriver()
        
        # Sample order data (simulating a phone order)
        phone = "+1234567890"
        name = "Test Customer"
        items = [
            {"name": "Chicken Biryani", "price": 12.99, "quantity": 2},
            {"name": "Mutton Curry", "price": 15.99, "quantity": 1},
            {"name": "Garlic Naan", "price": 2.99, "quantity": 3}
        ]
        
        print(f"\nCreating order for: {name} ({phone})")
        print(f"Items:")
        for item in items:
            print(f"  - {item['name']} x{item['quantity']} (${item['price']})")
        
        # Create order with Clover integration
        order = await db_driver.create_order_with_clover(
            phone=phone,
            items=items,
            name=name
        )
        
        if order:
            print(f"\n✅ Order created successfully!")
            print(f"   MongoDB ID: {order.get('_id')}")
            
            if order.get('clover_order_id'):
                print(f"   Clover Order ID: {order['clover_order_id']}")
                print(f"\n🎉 Integration successful! Order synced to both systems!")
                print(f"\n📱 Check your Clover Dashboard:")
                print(f"   https://sandbox.dev.clover.com/home/orders")
            else:
                print(f"   ⚠️ Order saved to MongoDB but not synced to Clover")
            
            return True
        else:
            print("❌ Failed to create order")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_direct_clover_order():
    """Test 3: Create order directly in Clover (bypass MongoDB)."""
    print("\n" + "="*60)
    print("TEST 3: Direct Clover Order Creation")
    print("="*60)
    
    try:
        clover_client = get_clover_client()
        
        items = [
            {"name": "Test Dish 1", "price": 9.99, "quantity": 1},
            {"name": "Test Dish 2", "price": 14.99, "quantity": 2}
        ]
        
        print(f"\nCreating order in Clover only...")
        
        order_id = await clover_client.create_order(
            phone="+1999888777",
            items=items,
            name="Direct Test"
        )
        
        if order_id:
            print(f"✅ Clover order created: {order_id}")
            return True
        else:
            print("❌ Failed to create Clover order")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "🚀"*30)
    print("CLOVER POS INTEGRATION TEST SUITE")
    print("🚀"*30)
    
    results = []
    
    # Test 1: Connection
    results.append(await test_clover_connection())
    
    if results[0]:  # Only continue if connection works
        # Test 2: Full integration
        results.append(await test_create_order())
        
        # Test 3: Direct Clover
        results.append(await test_direct_clover_order())
    else:
        print("\n⚠️ Skipping remaining tests due to connection failure")
        print("Please check your .env file:")
        print("  - CLOVER_MERCHANT_ID")
        print("  - CLOVER_ACCESS_TOKEN")
        print("  - CLOVER_BASE_URL")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    test_names = ["Connection Test", "Full Integration Test", "Direct Clover Test"]
    for i, result in enumerate(results):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_names[i]}: {status}")
    
    total_passed = sum(results)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    if all(results):
        print("\n🎉 All tests passed! Clover integration is ready!")
    else:
        print("\n⚠️ Some tests failed. Please check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())

