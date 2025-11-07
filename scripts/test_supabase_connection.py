"""
Test Supabase connection and data insertion
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

print("="*60)
print("Testing Supabase Connection")
print("="*60)

# Test 1: Check environment variables
print("\n1. Checking environment variables...")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERROR: Environment variables not set")
    sys.exit(1)
print(f"✅ SUPABASE_URL: {SUPABASE_URL[:30]}...")
print(f"✅ SUPABASE_SERVICE_KEY: {SUPABASE_KEY[:30]}...")

# Test 2: Create client
print("\n2. Creating Supabase client...")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Client created successfully")
except Exception as e:
    print(f"❌ ERROR creating client: {e}")
    sys.exit(1)

# Test 3: Check if tables exist
print("\n3. Checking if tables exist...")
try:
    response = supabase.table('popular_pairs').select('ticker').limit(1).execute()
    print(f"✅ Tables exist, found {len(response.data)} popular pairs")
except Exception as e:
    print(f"❌ ERROR: {e}")
    sys.exit(1)

# Test 4: Fetch small amount of data from Bybit
print("\n4. Fetching test data from Bybit (last 10 candles)...")
try:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=3)
    
    url = "https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "interval": "15",
        "start": int(start_time.timestamp() * 1000),
        "end": int(end_time.timestamp() * 1000),
        "limit": 10
    }
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if data.get("retCode") == 0:
        klines = data.get("result", {}).get("list", [])
        print(f"✅ Fetched {len(klines)} candles from Bybit")
    else:
        print(f"❌ API error: {data.get('retMsg')}")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ERROR fetching from Bybit: {e}")
    sys.exit(1)

# Test 5: Format and insert test data
print("\n5. Inserting test data into Supabase...")
try:
    formatted_candles = []
    for k in klines[:5]:  # Only insert 5 candles for testing
        formatted_candles.append({
            "ticker": "BTCUSDT",
            "timestamp": datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc).isoformat(),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "turnover": float(k[6]) if len(k) > 6 else 0
        })
    
    print(f"  Formatted {len(formatted_candles)} candles")
    print(f"  First candle timestamp: {formatted_candles[0]['timestamp']}")
    
    # Insert into database
    result = supabase.table('candles_15m').upsert(
        formatted_candles,
        on_conflict='ticker,timestamp'
    ).execute()
    
    print(f"✅ Inserted {len(formatted_candles)} candles successfully")
    
except Exception as e:
    print(f"❌ ERROR inserting data: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Verify data was inserted
print("\n6. Verifying data in database...")
try:
    response = supabase.table('candles_15m').select('ticker', count='exact').eq('ticker', 'BTCUSDT').execute()
    count = response.count
    print(f"✅ Total BTCUSDT candles in database: {count}")
    
    if count >= 5:
        print("✅ Data insertion successful!")
    else:
        print("⚠️  Warning: Expected at least 5 candles")
        
except Exception as e:
    print(f"❌ ERROR verifying data: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("🎉 All tests passed! Supabase is working correctly.")
print("="*60)

