"""
Backfill historical 15-minute candle data to Supabase
This script fetches historical data for popular pairs and stores it in the database
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import requests
import time
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for writes

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bybit API configuration
BYBIT_API_BASE = "https://api.bybit.com/v5"
CATEGORY = "linear"

def fetch_bybit_candles(symbol, interval, start_time, end_time, max_retries=3):
    """Fetch candle data from Bybit API with retry logic"""
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    all_klines = []
    current_start = start_ts
    
    while current_start < end_ts:
        url = f"{BYBIT_API_BASE}/market/kline"
        params = {
            "category": CATEGORY,
            "symbol": symbol,
            "interval": interval,
            "start": current_start,
            "end": end_ts,
            "limit": 1000  # Bybit max
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get("retCode") == 0:
                    result = data.get("result", {})
                    klines = result.get("list", [])
                    
                    if not klines:
                        break
                    
                    all_klines.extend(klines)
                    
                    # Get oldest timestamp for next iteration
                    oldest_ts = min(int(k[0]) for k in klines)
                    
                    if oldest_ts <= current_start:
                        break
                    
                    current_start = oldest_ts
                    time.sleep(0.1)  # Rate limiting
                    break
                else:
                    print(f"  API error: {data.get('retMsg')}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    else:
                        return None
                        
            except Exception as e:
                print(f"  Request error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        else:
            break
    
    return all_klines

def format_candles_for_db(symbol, klines):
    """Format Bybit candles for database insertion"""
    formatted = []
    
    for k in klines:
        try:
            formatted.append({
                "ticker": symbol,
                "timestamp": datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc).isoformat(),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "turnover": float(k[6]) if len(k) > 6 else 0
            })
        except (ValueError, IndexError) as e:
            print(f"  Warning: Skipping malformed candle: {e}")
            continue
    
    return formatted

def insert_candles_batch(candles, batch_size=1000):
    """Insert candles in batches with error handling"""
    total = len(candles)
    inserted = 0
    
    for i in range(0, total, batch_size):
        batch = candles[i:i + batch_size]
        
        try:
            # Use upsert to handle duplicates
            response = supabase.table('candles_15m').upsert(
                batch,
                on_conflict='ticker,timestamp'
            ).execute()
            
            inserted += len(batch)
            print(f"  Inserted batch {i // batch_size + 1}: {inserted}/{total} candles")
            
        except Exception as e:
            print(f"  Error inserting batch: {str(e)}")
            # Try to log the error
            try:
                supabase.table('update_logs').insert({
                    "ticker": batch[0]["ticker"] if batch else "unknown",
                    "update_type": "candles",
                    "success": False,
                    "error_message": str(e)
                }).execute()
            except:
                pass
    
    return inserted

def get_latest_timestamp(symbol):
    """Get the latest candle timestamp from database"""
    try:
        response = supabase.table('candles_15m') \
            .select('timestamp') \
            .eq('ticker', symbol) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .execute()
        
        if response.data:
            return datetime.fromisoformat(response.data[0]['timestamp'])
        return None
    except Exception as e:
        print(f"  Error getting latest timestamp: {e}")
        return None

def backfill_symbol(symbol, days_back=730, force_full=False):
    """Backfill historical data for a single symbol"""
    print(f"\n{'='*60}")
    print(f"Backfilling {symbol}")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    # Check for existing data
    if not force_full:
        latest = get_latest_timestamp(symbol)
        if latest:
            print(f"  Latest data: {latest.isoformat()}")
            # Only fetch data after the latest timestamp
            start_date = latest + timedelta(minutes=15)
            end_date = datetime.now(timezone.utc)
            
            if start_date >= end_date:
                print(f"  Already up to date!")
                return
        else:
            print(f"  No existing data, fetching full history")
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)
    else:
        print(f"  Force full backfill: {days_back} days")
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
    
    print(f"  Fetching data from {start_date.date()} to {end_date.date()}")
    
    # Fetch candles from Bybit
    klines = fetch_bybit_candles(symbol, "15", start_date, end_date)
    
    if not klines:
        print(f"  ❌ Failed to fetch data for {symbol}")
        return
    
    print(f"  ✓ Fetched {len(klines)} candles from Bybit")
    
    # Format for database
    formatted_candles = format_candles_for_db(symbol, klines)
    
    if not formatted_candles:
        print(f"  ❌ No valid candles to insert")
        return
    
    # Insert into database
    inserted = insert_candles_batch(formatted_candles)
    
    # Update popular_pairs table
    try:
        supabase.table('popular_pairs').update({
            'last_fetched': datetime.now(timezone.utc).isoformat()
        }).eq('ticker', symbol).execute()
    except Exception as e:
        print(f"  Warning: Could not update popular_pairs: {e}")
    
    # Log the update
    try:
        execution_time = int((time.time() - start_time) * 1000)
        supabase.table('update_logs').insert({
            "ticker": symbol,
            "update_type": "candles",
            "rows_affected": inserted,
            "success": True,
            "execution_time_ms": execution_time
        }).execute()
    except Exception as e:
        print(f"  Warning: Could not log update: {e}")
    
    elapsed = time.time() - start_time
    print(f"  ✓ Inserted {inserted} candles in {elapsed:.2f}s")
    print(f"  {'='*60}\n")

def backfill_all_popular_pairs(days_back=730, force_full=False):
    """Backfill all popular pairs from the database"""
    try:
        response = supabase.table('popular_pairs') \
            .select('ticker, priority') \
            .eq('auto_update', True) \
            .order('priority') \
            .execute()
        
        pairs = response.data
        
        if not pairs:
            print("No popular pairs found in database!")
            return
        
        print(f"\n🚀 Starting backfill for {len(pairs)} pairs")
        print(f"📅 Date range: {days_back} days")
        print(f"🔄 Mode: {'Full backfill' if force_full else 'Incremental update'}\n")
        
        total_start = time.time()
        
        for i, pair in enumerate(pairs, 1):
            print(f"[{i}/{len(pairs)}] Processing {pair['ticker']}...")
            backfill_symbol(pair['ticker'], days_back, force_full)
            
            # Small delay between symbols to avoid rate limits
            if i < len(pairs):
                time.sleep(1)
        
        total_elapsed = time.time() - total_start
        print(f"\n✅ Backfill complete! Total time: {total_elapsed/60:.2f} minutes")
        
    except Exception as e:
        print(f"❌ Error fetching popular pairs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill historical candle data to Supabase")
    parser.add_argument("--symbol", type=str, help="Specific symbol to backfill (e.g., BTCUSDT)")
    parser.add_argument("--days", type=int, default=730, help="Number of days to fetch (default: 730)")
    parser.add_argument("--force", action="store_true", help="Force full backfill even if data exists")
    parser.add_argument("--all", action="store_true", help="Backfill all popular pairs")
    
    args = parser.parse_args()
    
    if args.symbol:
        backfill_symbol(args.symbol, args.days, args.force)
    elif args.all:
        backfill_all_popular_pairs(args.days, args.force)
    else:
        print("Usage:")
        print("  Backfill specific symbol:  python backfill_historical_data.py --symbol BTCUSDT --days 730")
        print("  Backfill all popular pairs: python backfill_historical_data.py --all --days 730")
        print("  Force full backfill:       python backfill_historical_data.py --all --force")

