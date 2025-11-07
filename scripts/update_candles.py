"""
Update candle data for popular pairs - Run every 15 minutes
This script fetches the latest candles and updates the database
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
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bybit API
BYBIT_API_BASE = "https://api.bybit.com/v5"
CATEGORY = "linear"

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
        print(f"Error getting latest timestamp for {symbol}: {e}")
        return None

def fetch_latest_candles(symbol, since_time=None):
    """Fetch latest candles from Bybit"""
    if since_time is None:
        since_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    start_ts = int(since_time.timestamp() * 1000)
    end_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
    
    url = f"{BYBIT_API_BASE}/market/kline"
    params = {
        "category": CATEGORY,
        "symbol": symbol,
        "interval": "15",
        "start": start_ts,
        "end": end_ts,
        "limit": 200
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("retCode") == 0:
            return data.get("result", {}).get("list", [])
        else:
            print(f"  API error for {symbol}: {data.get('retMsg')}")
            return None
    except Exception as e:
        print(f"  Request error for {symbol}: {str(e)}")
        return None

def format_and_insert_candles(symbol, klines):
    """Format candles and insert into database"""
    if not klines:
        return 0
    
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
    
    if not formatted:
        return 0
    
    try:
        response = supabase.table('candles_15m').upsert(
            formatted,
            on_conflict='ticker,timestamp'
        ).execute()
        return len(formatted)
    except Exception as e:
        print(f"  Error inserting candles for {symbol}: {e}")
        return 0

def update_symbol(symbol):
    """Update latest candles for a symbol"""
    # Get latest timestamp
    latest = get_latest_timestamp(symbol)
    
    if latest:
        since_time = latest - timedelta(minutes=30)  # Fetch with overlap
    else:
        since_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    # Fetch latest candles
    klines = fetch_latest_candles(symbol, since_time)
    
    if klines is None:
        return False, 0
    
    # Insert candles
    inserted = format_and_insert_candles(symbol, klines)
    
    # Update popular_pairs last_fetched
    try:
        supabase.table('popular_pairs').update({
            'last_fetched': datetime.now(timezone.utc).isoformat()
        }).eq('ticker', symbol).execute()
    except:
        pass
    
    return True, inserted

def update_all_popular_pairs():
    """Update all popular pairs with auto_update=true"""
    try:
        response = supabase.table('popular_pairs') \
            .select('ticker, priority') \
            .eq('auto_update', True) \
            .order('priority') \
            .execute()
        
        pairs = response.data
        
        if not pairs:
            print("No popular pairs found")
            return
        
        print(f"\n🔄 Updating {len(pairs)} pairs at {datetime.now(timezone.utc).isoformat()}")
        
        total_inserted = 0
        successful = 0
        failed = 0
        
        start_time = time.time()
        
        for pair in pairs:
            symbol = pair['ticker']
            success, inserted = update_symbol(symbol)
            
            if success:
                successful += 1
                total_inserted += inserted
                print(f"  ✓ {symbol}: {inserted} new candles")
            else:
                failed += 1
                print(f"  ✗ {symbol}: Failed")
            
            time.sleep(0.2)  # Rate limiting
        
        elapsed = time.time() - start_time
        
        # Log the batch update
        try:
            supabase.table('update_logs').insert({
                "ticker": "ALL_PAIRS",
                "update_type": "candles",
                "rows_affected": total_inserted,
                "success": failed == 0,
                "error_message": f"Failed: {failed}" if failed > 0 else None,
                "execution_time_ms": int(elapsed * 1000)
            }).execute()
        except:
            pass
        
        print(f"\n✅ Update complete: {successful} successful, {failed} failed")
        print(f"📊 Total new candles: {total_inserted}")
        print(f"⏱️  Time: {elapsed:.2f}s\n")
        
    except Exception as e:
        print(f"❌ Error updating pairs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update latest candle data")
    parser.add_argument("--symbol", type=str, help="Update specific symbol")
    parser.add_argument("--all", action="store_true", help="Update all popular pairs")
    
    args = parser.parse_args()
    
    if args.symbol:
        success, inserted = update_symbol(args.symbol)
        if success:
            print(f"✓ {args.symbol}: {inserted} new candles")
        else:
            print(f"✗ {args.symbol}: Failed")
    elif args.all:
        update_all_popular_pairs()
    else:
        # Default: update all
        update_all_popular_pairs()

