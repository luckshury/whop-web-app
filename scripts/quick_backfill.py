"""
Quick backfill script - simplified and faster
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
import time
from supabase import create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_candles_simple(symbol, days=30):
    """Fetch candles with simpler logic"""
    print(f"\n{'='*60}")
    print(f"Fetching {days} days of data for {symbol}")
    print(f"{'='*60}\n")
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)
    
    all_candles = []
    current_end = end_time
    
    # Fetch in chunks (7 days at a time for faster processing)
    chunk_days = 7
    total_chunks = (days // chunk_days) + 1
    
    for chunk_num in range(total_chunks):
        chunk_start = current_end - timedelta(days=chunk_days)
        if chunk_start < start_time:
            chunk_start = start_time
        
        print(f"📥 Chunk {chunk_num + 1}/{total_chunks}: {chunk_start.date()} to {current_end.date()}")
        
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            "category": "linear",
            "symbol": symbol,
            "interval": "15",
            "start": int(chunk_start.timestamp() * 1000),
            "end": int(current_end.timestamp() * 1000),
            "limit": 1000
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if data.get("retCode") == 0:
                klines = data.get("result", {}).get("list", [])
                print(f"  ✓ Fetched {len(klines)} candles")
                
                # Format for database
                for k in klines:
                    all_candles.append({
                        "ticker": symbol,
                        "timestamp": datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc).isoformat(),
                        "open": float(k[1]),
                        "high": float(k[2]),
                        "low": float(k[3]),
                        "close": float(k[4]),
                        "volume": float(k[5]),
                        "turnover": float(k[6]) if len(k) > 6 else 0
                    })
            else:
                print(f"  ✗ API error: {data.get('retMsg')}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        current_end = chunk_start
        
        if current_end <= start_time:
            break
            
        time.sleep(0.2)  # Rate limiting
    
    return all_candles

def insert_candles(candles, batch_size=500):
    """Insert candles in batches"""
    print(f"\n💾 Inserting {len(candles)} candles into database...")
    
    total = len(candles)
    inserted = 0
    
    for i in range(0, total, batch_size):
        batch = candles[i:i + batch_size]
        
        try:
            supabase.table('candles_15m').upsert(
                batch,
                on_conflict='ticker,timestamp'
            ).execute()
            
            inserted += len(batch)
            progress = (inserted / total) * 100
            print(f"  ✓ Batch {i//batch_size + 1}: {inserted}/{total} ({progress:.1f}%)")
            
        except Exception as e:
            print(f"  ✗ Error inserting batch: {e}")
    
    return inserted

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Quick backfill for testing")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="Symbol to backfill")
    parser.add_argument("--days", type=int, default=30, help="Number of days")
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    # Fetch candles
    candles = fetch_candles_simple(args.symbol, args.days)
    
    if not candles:
        print("\n❌ No candles fetched!")
        sys.exit(1)
    
    print(f"\n✅ Total candles fetched: {len(candles)}")
    
    # Insert into database
    inserted = insert_candles(candles)
    
    # Verify
    response = supabase.table('candles_15m').select('ticker', count='exact').eq('ticker', args.symbol).execute()
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"🎉 COMPLETE!")
    print(f"{'='*60}")
    print(f"Symbol: {args.symbol}")
    print(f"Candles inserted: {inserted:,}")
    print(f"Total in database: {response.count:,}")
    print(f"Time taken: {elapsed:.1f}s")
    print(f"{'='*60}\n")

