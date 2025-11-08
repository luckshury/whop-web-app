"""
Supabase client helper for Streamlit app
Provides functions to fetch candle data and cached pivot analysis
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone, date
from supabase import create_client, Client
from typing import Optional, Tuple, List

def get_env(key: str, default: str = '') -> str:
    """Get environment variable from Streamlit secrets or os.environ"""
    try:
        # Try Streamlit secrets first (for Cloud deployment)
        if hasattr(st, 'secrets') and key in st.secrets:
            return str(st.secrets[key])
    except:
        pass
    # Fall back to environment variables (for local development)
    return os.getenv(key, default)

# Initialize Supabase client
@st.cache_resource
def get_supabase_client() -> Client:
    """Get or create Supabase client (cached)"""
    supabase_url = get_env("SUPABASE_URL")
    supabase_key = get_env("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        st.error("⚠️ Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
        return None
    
    return create_client(supabase_url, supabase_key)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_candles_from_supabase(ticker: str, days: int = 365) -> Optional[pd.DataFrame]:
    """
    Fetch historical 15-minute candles from Supabase with pagination
    
    Args:
        ticker: Symbol to fetch (e.g., 'BTCUSDT')
        days: Number of days of history to fetch
        
    Returns:
        DataFrame with columns: start_time, open, high, low, close, volume, turnover
    """
    supabase = get_supabase_client()
    if not supabase:
        return None
    
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    try:
        # Supabase limits responses to 1000 rows per request
        # Use timestamp-based pagination to fetch all data
        all_data = []
        batch_size = 1000
        current_start = start_date
        
        while True:
            response = supabase.table('candles_15m') \
                .select('timestamp,open,high,low,close,volume,turnover') \
                .eq('ticker', ticker) \
                .gte('timestamp', current_start.isoformat()) \
                .order('timestamp') \
                .limit(batch_size) \
                .execute()
            
            if not response.data:
                break
            
            all_data.extend(response.data)
            
            # If we got less than batch_size rows, we're done
            if len(response.data) < batch_size:
                break
            
            # Update current_start to last timestamp + 1 millisecond for next batch
            last_timestamp = response.data[-1]['timestamp']
            current_start = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00')) + timedelta(milliseconds=1)
        
        if not all_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data)
        
        # Rename timestamp to start_time for compatibility
        df = df.rename(columns={'timestamp': 'start_time'})
        
        # Convert types
        df['start_time'] = pd.to_datetime(df['start_time'], utc=True)
        for col in ['open', 'high', 'low', 'close', 'volume', 'turnover']:
            df[col] = df[col].astype(float)
        
        return df
        
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {str(e)}")
        return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cached_pivot_analysis(ticker: str, timeframe: str = 'daily', days: int = 365, weekdays: List[int] = None) -> Optional[Tuple[pd.DataFrame, dict]]:
    """
    Get pre-computed pivot analysis from cache
    
    Args:
        ticker: Symbol (e.g., 'BTCUSDT')
        timeframe: 'daily' or 'weekly'
        days: Date range in days
        weekdays: List of weekdays (0=Mon, 6=Sun)
        
    Returns:
        Tuple of (pivot_table DataFrame, stats dict) or None if not cached
    """
    if weekdays is None:
        weekdays = [0, 1, 2, 3, 4, 5, 6]
    
    supabase = get_supabase_client()
    if not supabase:
        return None
    
    try:
        response = supabase.table('pivot_analysis_cache') \
            .select('pivot_table,stats,last_updated') \
            .eq('ticker', ticker) \
            .eq('timeframe', timeframe) \
            .eq('date_range_days', days) \
            .contains('weekdays', weekdays) \
            .order('last_updated', desc=True) \
            .limit(1) \
            .execute()
        
        if not response.data:
            return None
        
        cache = response.data[0]
        
        # Check if cache is fresh (< 1 hour old)
        cache_time = datetime.fromisoformat(cache['last_updated'].replace('Z', '+00:00'))
        age = datetime.now(timezone.utc) - cache_time
        
        if age > timedelta(hours=1):
            return None  # Cache too old
        
        # Convert back to DataFrame
        pivot_table = pd.DataFrame(cache['pivot_table'])
        stats = cache['stats']
        
        return pivot_table, stats
        
    except Exception as e:
        # If error, just return None (will fall back to live calculation)
        return None

def save_pivot_analysis_to_cache(ticker: str, pivot_table: pd.DataFrame, stats: dict, timeframe: str = 'daily', days: int = 365, weekdays: List[int] = None):
    """
    Save computed pivot analysis to cache
    
    Args:
        ticker: Symbol
        pivot_table: Pivot analysis DataFrame
        stats: Statistics dict
        timeframe: 'daily' or 'weekly'
        days: Date range in days
        weekdays: List of weekdays
    """
    if weekdays is None:
        weekdays = [0, 1, 2, 3, 4, 5, 6]
    
    supabase = get_supabase_client()
    if not supabase:
        return
    
    try:
        data = {
            'ticker': ticker,
            'timeframe': timeframe,
            'date_range_days': days,
            'weekdays': weekdays,
            'pivot_table': pivot_table.to_dict('records'),
            'stats': stats,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert (insert or update)
        supabase.table('pivot_analysis_cache').upsert(
            data,
            on_conflict='ticker,timeframe,date_range_days,weekdays'
        ).execute()
        
    except Exception as e:
        # Silently fail - caching is optional
        pass

@st.cache_data(ttl=60)  # Cache for 1 minute
def get_popular_pairs() -> List[str]:
    """Get list of popular pairs from database"""
    supabase = get_supabase_client()
    if not supabase:
        return []
    
    try:
        response = supabase.table('popular_pairs') \
            .select('ticker') \
            .eq('auto_update', True) \
            .order('priority') \
            .execute()
        
        return [pair['ticker'] for pair in response.data]
    except:
        return []

@st.cache_data(ttl=60)  # Cache for 1 minute
def check_data_availability(ticker: str) -> dict:
    """
    Check if data is available in Supabase for a ticker
    
    Returns:
        Dict with keys: available (bool), latest_timestamp, candle_count
    """
    supabase = get_supabase_client()
    if not supabase:
        return {"available": False}
    
    try:
        # Just check if any data exists (fast query)
        check_response = supabase.table('candles_15m') \
            .select('timestamp') \
            .eq('ticker', ticker) \
            .order('timestamp', desc=True) \
            .limit(1) \
            .execute()
        
        if not check_response.data:
            return {"available": False}
        
        return {
            "available": True,
            "latest_timestamp": check_response.data[0]['timestamp'],
            "candle_count": 1000  # Placeholder - we don't need exact count
        }
    except Exception as e:
        print(f"Supabase check error: {e}")
        return {"available": False}

def is_supabase_enabled() -> bool:
    """Check if Supabase is properly configured"""
    return bool(get_env("SUPABASE_URL") and get_env("SUPABASE_SERVICE_KEY"))

