import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date, time, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import sys
import os

# Add utils directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import Supabase client
try:
    from utils.supabase_client import (
        fetch_candles_from_supabase,
        get_cached_pivot_analysis,
        save_pivot_analysis_to_cache,
        is_supabase_enabled,
        check_data_availability
    )
    SUPABASE_AVAILABLE = is_supabase_enabled()
except ImportError:
    SUPABASE_AVAILABLE = False

st.set_page_config(
    page_title="Pivot Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, minimal CSS for sidebar only
st.markdown("""
<style>
    /* Sidebar content styling only - let Streamlit handle collapse */
    [data-testid="stSidebar"] > div:first-child {
        padding: 1rem;
    }
    
    [data-testid="stSidebar"] label {
        font-size: 0.9rem;
        white-space: normal;
        word-wrap: break-word;
    }
    
    [data-testid="stSidebar"] h3 {
        font-size: 1rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    [data-testid="stSidebar"] .stCheckbox label {
        font-size: 0.85rem;
        padding: 0.25rem 0;
    }
    
    [data-testid="stSidebar"] .stSelectbox label {
        font-size: 0.85rem;
    }
    
    [data-testid="stSidebar"] .stDateInput label {
        font-size: 0.85rem;
    }
    
    [data-testid="stSidebar"] button {
        margin-top: 0.5rem;
    }
    
    [data-testid="stSidebar"] hr {
        margin: 0.75rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Bybit API base URL
BYBIT_API_BASE = "https://api.bybit.com/v5"

# Color theme generator function
def get_color_from_theme(intensity, theme="Blue (Default)"):
    """
    Generate RGB color based on intensity (0-1) and selected theme
    Returns: tuple of (r, g, b, alpha)
    """
    # Clamp intensity between 0 and 1
    intensity = max(0, min(1, intensity))
    alpha = 0.1 + (intensity * 0.4)
    
    if theme == "Blue (Default)":
        r, g, b = 0, int(100 + (intensity * 155)), 255
    elif theme == "Viridis":
        # Viridis colormap: purple -> green -> yellow
        if intensity < 0.5:
            r = int(intensity * 120)
            g = int(50 + intensity * 180)
            b = int(150 - intensity * 100)
        else:
            r = int(60 + (intensity - 0.5) * 400)
            g = int(140 + (intensity - 0.5) * 230)
            b = int(50 - (intensity - 0.5) * 50)
    elif theme == "Plasma":
        # Plasma colormap: blue -> purple -> yellow
        if intensity < 0.5:
            r = int(50 + intensity * 200)
            g = int(10 + intensity * 60)
            b = int(150 - intensity * 100)
        else:
            r = int(150 + (intensity - 0.5) * 210)
            g = int(40 + (intensity - 0.5) * 430)
            b = int(50 + (intensity - 0.5) * 50)
    elif theme == "Inferno":
        # Inferno colormap: black -> red -> yellow
        if intensity < 0.5:
            r = int(intensity * 200)
            g = int(intensity * 40)
            b = int(20 + intensity * 60)
        else:
            r = int(100 + (intensity - 0.5) * 310)
            g = int(20 + (intensity - 0.5) * 470)
            b = int(50 - (intensity - 0.5) * 50)
    elif theme == "Magma":
        # Magma colormap: black -> purple -> pink -> yellow
        if intensity < 0.5:
            r = int(intensity * 180)
            g = int(intensity * 40)
            b = int(50 + intensity * 150)
        else:
            r = int(90 + (intensity - 0.5) * 330)
            g = int(20 + (intensity - 0.5) * 460)
            b = int(125 - (intensity - 0.5) * 125)
    elif theme == "Turbo":
        # Turbo colormap: blue -> cyan -> green -> yellow -> red
        if intensity < 0.25:
            r = int(intensity * 400)
            g = int(intensity * 800)
            b = int(255 - intensity * 400)
        elif intensity < 0.5:
            r = int(100 + (intensity - 0.25) * 200)
            g = int(200 + (intensity - 0.25) * 220)
            b = int(155 - (intensity - 0.25) * 620)
        elif intensity < 0.75:
            r = int(150 + (intensity - 0.5) * 380)
            g = int(255 - (intensity - 0.5) * 600)
            b = int(0)
        else:
            r = int(255)
            g = int(105 - (intensity - 0.75) * 420)
            b = int(0)
    elif theme == "Purple":
        r = int(150 + intensity * 105)
        g = int(50 + intensity * 100)
        b = int(200 + intensity * 55)
    elif theme == "Green":
        r = int(50 + intensity * 100)
        g = int(150 + intensity * 105)
        b = int(50 + intensity * 100)
    elif theme == "Orange":
        r = int(200 + intensity * 55)
        g = int(100 + intensity * 155)
        b = int(0 + intensity * 50)
    else:
        # Default to blue
        r, g, b = 0, int(100 + (intensity * 155)), 255
    
    return r, g, b, alpha

# Initialize session state
if 'bybit_symbols' not in st.session_state:
    st.session_state.bybit_symbols = {}
if 'pivot_data' not in st.session_state:
    st.session_state.pivot_data = None
if 'pivot_stats' not in st.session_state:
    st.session_state.pivot_stats = {"days_analyzed": 0}
if 'current_price' not in st.session_state:
    st.session_state.current_price = None
if 'current_ohlc' not in st.session_state:
    st.session_state.current_ohlc = None
if 'today_high' not in st.session_state:
    st.session_state.today_high = None
if 'today_low' not in st.session_state:
    st.session_state.today_low = None
# Persist input parameters
if 'saved_exchange' not in st.session_state:
    st.session_state.saved_exchange = "Bybit"
if 'saved_ticker' not in st.session_state:
    st.session_state.saved_ticker = "BTCUSDT"
if 'saved_date_range' not in st.session_state:
    st.session_state.saved_date_range = (date.today() - timedelta(days=365), date.today())
if 'saved_weekdays' not in st.session_state:
    st.session_state.saved_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# Persist tab state
if 'saved_main_tab' not in st.session_state:
    st.session_state.saved_main_tab = "Time"
if 'saved_timeframe_tab' not in st.session_state:
    st.session_state.saved_timeframe_tab = "Daily"
if 'saved_distance_tab' not in st.session_state:
    st.session_state.saved_distance_tab = "Daily"
if 'saved_color_theme' not in st.session_state:
    st.session_state.saved_color_theme = "Blue (Default)"

# Function to fetch available symbols from Bybit
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bybit_symbols(category="linear"):
    """Fetch available trading symbols from Bybit V5 API"""
    try:
        url = f"{BYBIT_API_BASE}/market/instruments-info"
        params = {"category": category}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("retCode") == 0:
            result = data.get("result", {})
            instruments = result.get("list", [])
            symbols = []
            for instrument in instruments:
                symbol = instrument.get("symbol", "")
                status = instrument.get("status", "")
                if symbol and status == "Trading":
                    symbols.append(symbol)
            symbols.sort()
            return symbols
        else:
            return []
    except Exception as e:
        return []

# Function to fetch real-time ticker price
def fetch_realtime_price(symbol, category="linear"):
    """Fetch current ticker price and OHLC data from Bybit"""
    try:
        url = f"{BYBIT_API_BASE}/market/tickers"
        params = {"category": category, "symbol": symbol}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("retCode") == 0:
            result = data.get("result", {})
            list_data = result.get("list", [])
            if list_data:
                ticker_data = list_data[0]
                return {
                    "price": float(ticker_data.get("lastPrice", 0)),
                    "high24h": float(ticker_data.get("highPrice24h", 0)),
                    "low24h": float(ticker_data.get("lowPrice24h", 0)),
                    "open24h": float(ticker_data.get("openPrice24h", 0)),
                }
        return None
    except Exception as e:
        return None

# Function to calculate today's P1 and P2 based on current price data
def get_todays_pivots(kline_data, current_utc_time):
    """
    Determine today's P1 and P2 based on current candle data.
    
    P1 = First extreme (high or low, whichever occurred first)
    P2 = Second extreme (the other one)
    
    Returns tuple: (p1_hour, p2_hour, p1_time, p2_time) 
    - p1_hour, p2_hour: Just the hour for table bucket
    - p1_time, p2_time: Full timestamp for exact time display
    or (None, None, None, None) if not yet determined
    """
    if kline_data is None or kline_data.empty:
        return None, None, None, None
    
    try:
        # Filter to only today's data (same day in UTC)
        today_start = current_utc_time.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        todays_data = kline_data[
            (kline_data['start_time'] >= today_start) & 
            (kline_data['start_time'] < today_end)
        ]
        
        if todays_data.empty:
            return None, None, None, None
        
        # Sort by time to get chronological order
        todays_data = todays_data.sort_values('start_time')
        
        # Find the high and low for today
        high_row = todays_data.loc[todays_data['high'].idxmax()]
        low_row = todays_data.loc[todays_data['low'].idxmin()]
        
        high_time = high_row['start_time']
        low_time = low_row['start_time']
        
        # Determine which came first
        if high_time < low_time:
            p1_hour = high_time.hour
            p2_hour = low_time.hour
            p1_time = high_time
            p2_time = low_time
        else:
            p1_hour = low_time.hour
            p2_hour = high_time.hour
            p1_time = low_time
            p2_time = high_time
        
        return p1_hour, p2_hour, p1_time, p2_time
    except Exception as e:
        return None, None, None, None

# Sidebar with input fields
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Get index for saved exchange
    exchange_options = ["Bybit", "Hyperliquid"]
    saved_exchange_index = 0
    if st.session_state.saved_exchange in exchange_options:
        saved_exchange_index = exchange_options.index(st.session_state.saved_exchange)
    
    exchange = st.selectbox(
        "Exchange",
        exchange_options,
        index=saved_exchange_index
    )
    
    # Always use "linear" for Bybit
    if exchange == "Bybit":
        category = "linear"
        cache_key = f"{exchange}_{category}"
        if cache_key not in st.session_state.bybit_symbols:
            with st.spinner("Loading symbols..."):
                symbols = fetch_bybit_symbols(category)
                st.session_state.bybit_symbols[cache_key] = symbols
        else:
            symbols = st.session_state.bybit_symbols[cache_key]
        
        if symbols:
            default_index = 0
            # Use saved ticker if available, otherwise default to BTCUSDT
            if st.session_state.saved_ticker in symbols:
                default_index = symbols.index(st.session_state.saved_ticker)
            elif "BTCUSDT" in symbols:
                default_index = symbols.index("BTCUSDT")
            
            ticker = st.selectbox(
                "Ticker",
                options=symbols,
                index=default_index,
                help=f"{len(symbols)} pairs available"
            )
        else:
            ticker = st.text_input(
                "Ticker",
                value="BTCUSDT",
                placeholder="Enter ticker"
            )
    else:
        category = "spot"
        ticker = st.text_input(
            "Ticker",
            value="BTC-USDT",
            placeholder="BTC-USDT"
        )
    
    date_range = st.date_input(
        "Date Range",
        value=st.session_state.saved_date_range,
        max_value=date.today()
    )
    
    st.markdown("---")
    st.subheader("📅 Weekday Filters")
    
    weekday_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    selected_weekdays = []
    for day in weekday_options:
        # Check if day is in saved weekdays
        default_checked = day in st.session_state.saved_weekdays
        if st.checkbox(day, value=default_checked, key=f"weekday_{day}"):
            selected_weekdays.append(day)
    
    st.markdown("---")
    
    # Color Theme Selector
    st.subheader("🎨 Color Theme")
    color_theme_options = [
        "Blue (Default)",
        "Viridis",
        "Plasma",
        "Inferno",
        "Magma",
        "Turbo",
        "Purple",
        "Green",
        "Orange"
    ]
    
    theme_index = 0
    if st.session_state.saved_color_theme in color_theme_options:
        theme_index = color_theme_options.index(st.session_state.saved_color_theme)
    
    color_theme = st.selectbox(
        "Heatmap Style",
        color_theme_options,
        index=theme_index,
        help="Color scheme for table"
    )
    
    # Save color theme selection
    st.session_state.saved_color_theme = color_theme
    
    st.markdown("---")
    analyze_button = st.button("📈 Analyze", type="primary", use_container_width=True)

# Handle date range selection
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, date):
    start_date = date_range
    end_date = date.today()
else:
    start_date = date.today() - timedelta(days=365)
    end_date = date.today()

# Map weekday names to numbers (Monday=0, Sunday=6) for filtering
weekday_map = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}
# Convert weekday names to integers for the calculation function
selected_weekdays_numeric = [weekday_map[day] for day in selected_weekdays] if selected_weekdays else list(range(7))

# Helper function to fetch a single batch
def fetch_single_batch(session, url, category, symbol, interval, start_ts, end_ts, max_limit):
    """Fetch a single batch of kline data"""
    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "start": start_ts,
        "end": end_ts,
        "limit": max_limit
    }
    try:
        response = session.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data.get("retCode") == 0:
            result = data.get("result", {})
            klines = result.get("list", [])
            if klines:
                klines.reverse()
                return klines, None
            return [], None
        else:
            return None, data.get('retMsg', 'Unknown error')
    except Exception as e:
        return None, str(e)

# Function to fetch data from Bybit
def fetch_bybit_data(symbol, interval, start_time, end_time, category="spot", progress_bar=None):
    """Fetch kline/candlestick data from Bybit V5 API"""
    try:
        # Convert date objects to datetime with UTC timezone
        if isinstance(start_time, date) and not isinstance(start_time, datetime):
            start_time = datetime.combine(start_time, time.min)
        if isinstance(end_time, date) and not isinstance(end_time, datetime):
            end_time = datetime.combine(end_time, time.max)
        
        # Make timezone-aware (UTC)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        
        url = f"{BYBIT_API_BASE}/market/kline"
        max_limit = 200
        
        # Create date ranges for fetching
        date_ranges = []
        current_end = end_time
        batch_size_days = 30
        
        while current_end > start_time:
            chunk_start = max(start_time, current_end - timedelta(days=batch_size_days))
            date_ranges.append((chunk_start, current_end))
            current_end = chunk_start - timedelta(milliseconds=1)
            if current_end < start_time:
                break
        
        date_ranges.reverse()
        
        status_text = st.empty()
        all_klines = []
        lock = Lock()
        
        def fetch_chunk(chunk_start, chunk_end):
            chunk_klines = []
            chunk_start_ts = int(chunk_start.timestamp() * 1000)
            chunk_end_ts = int(chunk_end.timestamp() * 1000)
            current_chunk_end = chunk_end
            
            session = requests.Session()
            
            while current_chunk_end >= chunk_start:
                klines, error = fetch_single_batch(
                    session, url, category, symbol, interval,
                    chunk_start_ts, int(current_chunk_end.timestamp() * 1000), max_limit
                )
                
                if error:
                    if "rate limit" in error.lower() or "10004" in error:
                        import time as time_module
                        time_module.sleep(0.5)
                        continue
                    break
                
                if not klines:
                    break
                
                oldest_ts = int(klines[0][0])
                oldest_dt = datetime.fromtimestamp(oldest_ts / 1000, tz=timezone.utc)
                
                chunk_klines.extend(klines)
                
                if oldest_dt <= chunk_start or len(klines) < max_limit:
                    break
                
                current_chunk_end = oldest_dt - timedelta(milliseconds=1)
            
            session.close()
            return chunk_klines
        
        # Fetch chunks concurrently
        max_workers = min(10, len(date_ranges))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_chunk, start, end): (start, end) 
                      for start, end in date_ranges}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    chunk_data = future.result()
                    with lock:
                        all_klines.extend(chunk_data)
                    
                    if progress_bar:
                        progress = min(completed / len(date_ranges), 1.0)
                        progress_bar.progress(progress)
                    
                    status_text.text(f"Fetched {len(all_klines):,} records ({completed}/{len(date_ranges)} chunks)...")
                except Exception as e:
                    st.warning(f"Error in chunk: {str(e)}")
        
        status_text.empty()
        
        if all_klines:
            df = pd.DataFrame(all_klines, columns=[
                "start_time", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            df["start_time"] = pd.to_datetime(df["start_time"].astype(int), unit="ms", utc=True)
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = df[col].astype(float)
            
            df = df.drop_duplicates(subset=["start_time"])
            df = df.sort_values("start_time").reset_index(drop=True)
            df = df[(df["start_time"] >= start_time) & (df["start_time"] <= end_time)]
            
            return df
        else:
            return None
            
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None


def build_empty_pivot_table():
    """Return an empty pivot table with the required structure."""
    empty_rows = []
    for hour in range(24):
        empty_rows.append({
            'Hour': f"{hour:02d}:00",
            'P1 %': 0.0,
            'Last P1': None,
            'P2 %': 0.0,
            'Last P2': None
        })
    return pd.DataFrame(empty_rows)

# Function to calculate P1 and P2 pivots
def calculate_pivot_analysis(df, selected_weekdays):
    """Calculate P1/P2 frequency distribution by hour (UTC+0)."""
    if df is None or df.empty:
        return build_empty_pivot_table(), 0

    df = df.copy()
    df = df.sort_values('start_time')

    df['date'] = df['start_time'].dt.date
    df['weekday'] = df['start_time'].dt.dayofweek
    df = df[df['weekday'].isin(selected_weekdays)]

    if df.empty:
        return build_empty_pivot_table(), 0

    pivot_rows = []
    for date_val, day_data in df.groupby('date'):
        day_data = day_data.sort_values('start_time')
        if day_data.empty:
            continue

        high_idx = day_data['high'].idxmax()
        low_idx = day_data['low'].idxmin()

        high_time = day_data.loc[high_idx, 'start_time']
        low_time = day_data.loc[low_idx, 'start_time']

        if pd.isna(high_time) or pd.isna(low_time):
            continue

        if high_time < low_time:
            p1_hour = high_time.hour
            p2_hour = low_time.hour
        else:
            p1_hour = low_time.hour
            p2_hour = high_time.hour

        pivot_rows.append({
            'date': date_val,
            'p1_hour': p1_hour,
            'p2_hour': p2_hour
        })

    if not pivot_rows:
        return build_empty_pivot_table(), 0

    pivot_df = pd.DataFrame(pivot_rows)
    current_utc = datetime.now(timezone.utc)
    current_date = current_utc.date()
    current_hour = current_utc.hour

    has_current_day = current_date in pivot_df['date'].values
    completed_df = pivot_df[pivot_df['date'] != current_date] if has_current_day else pivot_df
    completed_days = len(completed_df)

    if completed_days == 0:
        completed_df = pivot_df
        completed_days = len(completed_df)

    p1_counts = completed_df['p1_hour'].value_counts()
    p2_counts = completed_df['p2_hour'].value_counts()

    today = date.today()
    p1_last = {}
    p2_last = {}
    for hour in range(24):
        p1_dates = pivot_df[pivot_df['p1_hour'] == hour]['date']
        p2_dates = pivot_df[pivot_df['p2_hour'] == hour]['date']
        p1_last[hour] = (today - p1_dates.max()).days if len(p1_dates) > 0 else None
        p2_last[hour] = (today - p2_dates.max()).days if len(p2_dates) > 0 else None

    denominator = completed_days if completed_days > 0 else 1

    rows = []
    for hour in range(24):
        p1_count = p1_counts.get(hour, 0)
        p2_count = p2_counts.get(hour, 0)

        # Always show the historical percentage (don't zero it out)
        # The "as the live day progresses" logic is about updating the denominator,
        # but we still want to see what the actual probability is for each hour
        p1_pct = (p1_count / denominator * 100) if denominator > 0 else 0.0
        p2_pct = (p2_count / denominator * 100) if denominator > 0 else 0.0

        rows.append({
            'Hour': f"{hour:02d}:00",
            'P1 %': round(p1_pct, 1),
            'Last P1': p1_last[hour],
            'P2 %': round(p2_pct, 1),
            'Last P2': p2_last[hour]
        })

    result_df = pd.DataFrame(rows)
    return result_df, completed_days

# Fetch and analyze data when button is clicked
if analyze_button:
    if not ticker:
        st.error("Please enter a ticker symbol!")
    elif start_date > end_date:
        st.error("Invalid date range!")
    else:
        # Save current parameters to session state for persistence
        st.session_state.saved_exchange = exchange
        st.session_state.saved_ticker = ticker
        st.session_state.saved_date_range = (start_date, end_date)
        st.session_state.saved_weekdays = selected_weekdays
        
        df = None
        days_in_range = (end_date - start_date).days
        
        # Try Supabase first if available
        if SUPABASE_AVAILABLE and exchange == "Bybit":
            # Check if data is available in Supabase
            data_check = check_data_availability(ticker)
            
            if data_check.get("available"):
                with st.spinner(f"⚡ Loading from cache... ({data_check.get('candle_count', 0):,} candles available)"):
                    df = fetch_candles_from_supabase(ticker, days_in_range)
                    
                    if df is not None and not df.empty:
                        st.success(f"✨ Loaded {len(df):,} candles from cache - updated every 15 minutes!")
        
        # Fallback to direct API if Supabase not available or no data
        if df is None or (df is not None and df.empty):
            if SUPABASE_AVAILABLE:
                st.info(f"📡 Fetching from {exchange} API (not cached yet)...")
            
            with st.spinner(f"Fetching data from {exchange}..."):
                if exchange == "Bybit":
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()
                    
                    df = fetch_bybit_data(ticker, "15", start_date, end_date, category, progress_bar)
                    
                    progress_bar.empty()
                    
                    if df is None or df.empty:
                        st.error("❌ No data returned from Bybit API")
                        st.error("Possible issues:")
                        st.error("- Ticker symbol might be wrong (try BTCUSDT)")
                        st.error("- Bybit API might be rate limiting")
                        st.error("- Network connection issue")
                        
                        # Try a simple test request
                        try:
                            test_response = requests.get("https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=15&limit=1")
                            st.info(f"Test API status: {test_response.status_code}")
                            st.code(test_response.text[:500])
                        except Exception as e:
                            st.error(f"Test request failed: {str(e)}")
                        
                        st.session_state.pivot_data = build_empty_pivot_table()
                        st.session_state.pivot_stats = {"days_analyzed": 0}
                elif exchange == "Hyperliquid":
                    st.info("Hyperliquid integration coming soon!")
                    st.session_state.pivot_data = build_empty_pivot_table()
                    st.session_state.pivot_stats = {"days_analyzed": 0}
        
        # Calculate pivot analysis if we have data
        if df is not None and not df.empty:
            with st.spinner("Calculating pivot analysis..."):
                pivot_table, days_count = calculate_pivot_analysis(df, selected_weekdays_numeric)
                st.session_state.pivot_data = pivot_table
                st.session_state.pivot_stats = {
                    "days_analyzed": days_count
                }
                
                # Save to Supabase cache if available
                if SUPABASE_AVAILABLE:
                    try:
                        save_pivot_analysis_to_cache(
                            ticker, 
                            pivot_table, 
                            {"days_analyzed": days_count},
                            timeframe='daily',
                            days=days_in_range,
                            weekdays=selected_weekdays_numeric
                        )
                    except:
                        pass  # Silently fail if cache save fails

# Display pivot analysis table
pivot_table = st.session_state.pivot_data

if pivot_table is not None:
    # Fetch real-time price for the selected ticker
    price_info = fetch_realtime_price(ticker, category)
    if price_info:
        st.session_state.current_price = price_info["price"]
        st.session_state.today_high = price_info["high24h"]
        st.session_state.today_low = price_info["low24h"]
    
    days_info = st.session_state.pivot_stats.get("days_analyzed", 0)
    
    # Mapping of timeframe names to Bybit interval codes
    timeframe_map = {
        "hourly": "60",
        "4h": "240",
        "session": "D",
        "daily": "D",
        "weekly": "W",
        "monthly": "M"
    }
    
    def render_pivot_analysis(timeframe_key, timeframe_label, tab_container):
        """Render pivot analysis for a given timeframe"""
        with tab_container:
            current_utc_time = datetime.now(timezone.utc)
            
            # For Daily tab, use the existing pivot_table (already calculated)
            # For other tabs, fetch data for that timeframe
            if timeframe_key == "daily":
                timeframe_klines = None
                current_p1_hour = None
                current_p2_hour = None
                p1_exact_time = None
                p2_exact_time = None
                
                # Fetch today's data for P1/P2 determination
                try:
                    today_start = current_utc_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = current_utc_time
                    timeframe_klines = fetch_bybit_data(ticker, "15", today_start, today_end, category)
                    if timeframe_klines is not None and not timeframe_klines.empty:
                        current_p1_hour, current_p2_hour, p1_exact_time, p2_exact_time = get_todays_pivots(timeframe_klines, current_utc_time)
                except:
                    timeframe_klines = None
            else:
                # Fetch data for other timeframes
                try:
                    if timeframe_key == "hourly":
                        data_start = current_utc_time - timedelta(hours=24)
                    elif timeframe_key == "4h":
                        data_start = current_utc_time - timedelta(days=7)
                    elif timeframe_key == "session":
                        data_start = current_utc_time.replace(hour=0, minute=0, second=0, microsecond=0)
                    elif timeframe_key == "weekly":
                        data_start = current_utc_time - timedelta(days=365)
                    else:  # monthly
                        data_start = current_utc_time - timedelta(days=730)
                    
                    timeframe_klines = fetch_bybit_data(ticker, timeframe_map[timeframe_key], data_start, current_utc_time, category)
                except:
                    timeframe_klines = None
                
                if timeframe_klines is None or timeframe_klines.empty:
                    st.info(f"No data available for {timeframe_label} timeframe")
                    return
                
                # Calculate pivots for this timeframe
                current_p1_hour = None
                current_p2_hour = None
                p1_exact_time = None
                p2_exact_time = None
                
                if timeframe_klines is not None and not timeframe_klines.empty:
                    current_p1_hour, current_p2_hour, p1_exact_time, p2_exact_time = get_todays_pivots(timeframe_klines, current_utc_time)
            
            # Re-calculate pivot analysis for this timeframe's data
            # Note: This uses the existing pivot_table from the Daily analysis
            # For other timeframes, we'd need to recalculate based on timeframe_klines
            # For now, we'll show the daily table in all tabs as placeholder
            
            numeric_df = pivot_table.copy()
            
            p1_max = numeric_df['P1 %'].max()
            p2_max = numeric_df['P2 %'].max()
            if pd.isna(p1_max) or p1_max <= 0:
                p1_max = 1
            if pd.isna(p2_max) or p2_max <= 0:
                p2_max = 1
            
            def percentage_gradient(series, max_val):
                styles = []
                for val in series:
                    if pd.isna(val) or max_val <= 0:
                        styles.append('')
                    else:
                        intensity = min(val / max_val, 1.0)
                        alpha = 0.1 + (intensity * 0.4)
                        blue = int(100 + (intensity * 155))
                        styles.append(f'background-color: rgba(0, {blue}, 255, {alpha})')
                return styles
            
            # Format data for display
            display_df = numeric_df.copy()
            display_df['P1 %'] = display_df['P1 %'].apply(lambda x: f"{x:.1f}%")
            display_df['P2 %'] = display_df['P2 %'].apply(lambda x: f"{x:.1f}%")
            display_df['Last P1'] = display_df['Last P1'].apply(lambda x: '' if pd.isna(x) else f"{int(x)}d ago")
            display_df['Last P2'] = display_df['Last P2'].apply(lambda x: '' if pd.isna(x) else f"{int(x)}d ago")
            
            current_hour_utc = datetime.now(timezone.utc).hour
            
            # Generate HTML table (reuse existing logic)
            html_table = '<table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 0;">'
            html_table += '<thead><tr style="background-color: rgba(255, 255, 255, 0.05);">'
            col_widths = {'Hour': '14%', 'P1 %': '18%', 'Last P1': '20%', 'P2 %': '18%', 'Last P2': '20%'}
            for col in display_df.columns:
                width = col_widths.get(col, '16%')
                html_table += f'<th style="width: {width}; padding: 5px 4px; text-align: center; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; border: 1px solid rgba(255, 255, 255, 0.1); white-space: nowrap; background-color: rgba(255, 255, 255, 0.08);">{col}</th>'
            html_table += '</tr></thead>'
            
            html_table += '<tbody>'
            for idx, row in numeric_df.iterrows():
                row_bg = 'rgba(255, 255, 255, 0.02)' if idx % 2 == 1 else 'transparent'
                hour_str = display_df.iloc[idx, 0]
                hour_num = int(hour_str.split(':')[0])
                
                is_p1_hour = (hour_num == current_p1_hour) if current_p1_hour is not None else False
                is_p2_hour = (hour_num == current_p2_hour) if current_p2_hour is not None else False
                is_current_hour = (hour_num == current_hour_utc)
                
                if is_p1_hour:
                    row_bg = 'rgba(0, 255, 0, 0.08)'
                    row_border = '1px solid rgba(0, 255, 0, 0.15)'
                elif is_p2_hour:
                    row_bg = 'rgba(255, 107, 107, 0.08)'
                    row_border = '1px solid rgba(255, 107, 107, 0.15)'
                elif is_current_hour:
                    row_bg = 'rgba(255, 255, 255, 0.06)'
                    row_border = '1px solid rgba(255, 255, 255, 0.08)'
                else:
                    row_border = '1px solid rgba(255, 255, 255, 0.05)'
                
                html_table += f'<tr style="background-color: {row_bg}; border: {row_border};">'
                
                for col_idx, col in enumerate(display_df.columns):
                    cell_value = display_df.iloc[idx, col_idx]
                    width = col_widths.get(col, '16%')
                    cell_style = f'width: {width}; padding: 5px 4px; text-align: center; height: 32px; border: 1px solid rgba(255, 255, 255, 0.05); white-space: nowrap;'
                    
                    if col == 'P1 %' and is_p1_hour:
                        cell_value = f'✓ {cell_value}'
                        cell_style += ' border: 1.5px solid rgba(100, 150, 255, 0.4); border-radius: 3px; background-color: rgba(100, 150, 255, 0.08);'
                    elif col == 'P2 %' and is_p2_hour:
                        cell_value = f'✓ {cell_value}'
                        cell_style += ' border: 1.5px solid rgba(100, 150, 255, 0.4); border-radius: 3px; background-color: rgba(100, 150, 255, 0.08);'
                    elif col == 'P1 %':
                        try:
                            num_val = float(numeric_df.iloc[idx, col_idx])
                            if p1_max > 0:
                                intensity = min(num_val / p1_max, 1.0)
                                r, g, b, alpha = get_color_from_theme(intensity, color_theme)
                                cell_style += f' background-color: rgba({r}, {g}, {b}, {alpha});'
                        except:
                            pass
                    elif col == 'P2 %':
                        try:
                            num_val = float(numeric_df.iloc[idx, col_idx])
                            if p2_max > 0:
                                intensity = min(num_val / p2_max, 1.0)
                                r, g, b, alpha = get_color_from_theme(intensity, color_theme)
                                cell_style += f' background-color: rgba({r}, {g}, {b}, {alpha});'
                        except:
                            pass
                    
                    html_table += f'<td style="{cell_style}">{cell_value}</td>'
                
                html_table += '</tr>'
            
            html_table += '</tbody></table>'
            
            # Table CSS (optimized for 1080p)
            table_css = """
            <style>
            table {
                color: #E8E8E8;
            }
            table th, table td {
                font-size: 0.85rem;
            }
            </style>
            """
            
            # Display table and insights side-by-side (optimized for 1080p)
            col_table, col_insights = st.columns([2.2, 1])
            
            with col_table:
                st.markdown(table_css, unsafe_allow_html=True)
                st.markdown(html_table, unsafe_allow_html=True)
            
            with col_insights:
                st.markdown("### Key Insights")
                
                if current_p1_hour is not None and current_p2_hour is not None:
                    p1_time = f"{current_p1_hour:02d}:00"
                    p2_time = f"{current_p2_hour:02d}:00"
                    
                    if timeframe_klines is not None and not timeframe_klines.empty:
                        today_data = timeframe_klines[
                            (timeframe_klines['start_time'].dt.date == datetime.now(timezone.utc).date())
                        ]
                        if not today_data.empty:
                            high_time = today_data.loc[today_data['high'].idxmax(), 'start_time']
                            low_time = today_data.loc[today_data['low'].idxmin(), 'start_time']
                            
                            p1_type = "High" if high_time.hour == current_p1_hour else "Low"
                            p2_type = "Low" if p1_type == "High" else "High"
                            
                            st.markdown(f"**{ticker}** | P1: {p1_type} {p1_time} | P2: {p2_type} {p2_time}")
                            st.divider()
                            
                            # Initialize variables for risk assessment
                            p1_after_current = 0
                            p2_after_current = 0
                            p1_at_or_after_p2 = 0
                            
                            # P1 Status
                            p1_pct_hist = numeric_df.loc[numeric_df['Hour'] == p1_time, 'P1 %'].values
                            if len(p1_pct_hist) > 0:
                                # Format exact times for display (use 15-min precision)
                                p1_exact_display = f"{p1_exact_time.hour:02d}:{p1_exact_time.minute:02d}" if p1_exact_time else p1_time
                                p2_exact_display = f"{p2_exact_time.hour:02d}:{p2_exact_time.minute:02d}" if p2_exact_time else p2_time
                                
                                # % of P1s formed after current P1 time
                                p1_hour_num = current_p1_hour
                                after_p1 = numeric_df[numeric_df['Hour'] > f"{p1_hour_num:02d}:00"]
                                p1_after_p1_total = after_p1['P1 %'].sum() if not after_p1.empty else 0
                                
                                # % of P1s formed at or after current P2 time (P2 hour onwards in P1% column)
                                p2_hour_num = current_p2_hour if current_p2_hour is not None else 0
                                at_or_after_p2 = numeric_df[numeric_df['Hour'] >= f"{p2_hour_num:02d}:00"]
                                p1_at_or_after_p2 = at_or_after_p2['P1 %'].sum() if not at_or_after_p2.empty else 0
                                
                                # Debug: Show what hours are being summed
                                # st.caption(f"Debug: Summing P1% from {p2_hour_num:02d}:00 onwards: {list(at_or_after_p2['Hour'].values)}")
                                
                                # Calculate P1s after current time (for risk assessment later)
                                current_time_hour = current_utc_time.hour
                                after_current_time = numeric_df[numeric_df['Hour'] > f"{current_time_hour:02d}:00"]
                                p1_after_current = after_current_time['P1 %'].sum() if not after_current_time.empty else 0
                                
                                st.markdown(f"**P1 Status**  \nAfter {p1_exact_display}: **{p1_after_p1_total:.1f}%** | At/After {p2_exact_display}: **{p1_at_or_after_p2:.1f}%**")
                            
                            st.divider()
                            
                            # P2 Status
                            p2_pct_hist = numeric_df.loc[numeric_df['Hour'] == p2_time, 'P2 %'].values
                            if len(p2_pct_hist) > 0:
                                # % of P2s formed after current P2 time
                                p2_hour_num = current_p2_hour
                                after_p2 = numeric_df[numeric_df['Hour'] > f"{p2_hour_num:02d}:00"]
                                p2_after_p2_total = after_p2['P2 %'].sum() if not after_p2.empty else 0
                                
                                # % of P2s formed after current time
                                current_time_hour = current_utc_time.hour
                                after_current_time = numeric_df[numeric_df['Hour'] > f"{current_time_hour:02d}:00"]
                                p2_after_current = after_current_time['P2 %'].sum() if not after_current_time.empty else 0
                                
                                st.markdown(f"**P2 Status**  \nAfter {p2_exact_display}: **{p2_after_p2_total:.1f}%** | After {current_time_hour:02d}:{current_utc_time.minute:02d}: **{p2_after_current:.1f}%**")
                            
                            # Risk Assessment
                            selected_weekdays_str = ", ".join(selected_weekdays) if selected_weekdays else "All days"
                            st.caption(f"Statistics are based on: {selected_weekdays_str}")
                            
                        # P1 Flip Risk (based on % at/after P2 time)
                        if p1_at_or_after_p2 < 20:
                            st.success(f"✓ **P1 Flip Risk:** Low — {p1_at_or_after_p2:.1f}%")
                        elif p1_at_or_after_p2 < 50:
                            st.warning(f"⚠ **P1 Flip Risk:** Moderate — {p1_at_or_after_p2:.1f}%")
                        else:
                            st.error(f"✗ **P1 Flip Risk:** High — {p1_at_or_after_p2:.1f}%")
                        
                        # P2 Formation Likelihood (based on % after current time)
                        if p2_after_current < 20:
                            st.success(f"✓ **P2 Formation:** Likely — {p2_after_current:.1f}%")
                        elif p2_after_current < 50:
                            st.warning(f"⚠ **P2 Formation:** Moderate — {p2_after_current:.1f}%")
                        else:
                            st.error(f"✗ **P2 Formation:** Unlikely — {p2_after_current:.1f}%")
                        
                        # Mini Chart - Today's Price Action (in Key Insights column)
                        st.markdown("---")
                        
                        if timeframe_klines is not None and not timeframe_klines.empty:
                            # Filter to today's data only
                            today_data = timeframe_klines[
                                timeframe_klines['start_time'].dt.date == current_utc_time.date()
                            ].copy()
                            
                            if not today_data.empty and p1_exact_time is not None and p2_exact_time is not None:
                                import plotly.graph_objects as go
                                
                                # Determine if P1 is high or low (first extreme)
                                high_row = today_data.loc[today_data['high'].idxmax()]
                                low_row = today_data.loc[today_data['low'].idxmin()]
                                
                                p1_is_high = high_row['start_time'] < low_row['start_time']
                                
                                # Get P1 and P2 prices from the correct extreme
                                if p1_is_high:
                                    p1_price = float(high_row['high'])
                                    p2_price = float(low_row['low'])
                                else:
                                    p1_price = float(low_row['low'])
                                    p2_price = float(high_row['high'])
                                
                                if p1_price and p2_price:
                                    
                                    # Create mini candlestick chart
                                    fig = go.Figure()
                                    
                                    # Add candlestick
                                    fig.add_trace(go.Candlestick(
                                        x=today_data['start_time'],
                                        open=today_data['open'],
                                        high=today_data['high'],
                                        low=today_data['low'],
                                        close=today_data['close'],
                                        name=ticker,
                                        increasing_line_color='#26a69a',
                                        decreasing_line_color='#ef5350',
                                        increasing_fillcolor='rgba(38, 166, 154, 0.3)',
                                        decreasing_fillcolor='rgba(239, 83, 80, 0.3)'
                                    ))
                                    
                                    # Get the last candle time for ray extension
                                    last_time = today_data['start_time'].max()
                                    
                                    # Add P1 marker at exact pivot (high or low)
                                    p1_symbol = 'triangle-up' if p1_is_high else 'triangle-down'
                                    fig.add_trace(go.Scatter(
                                        x=[p1_exact_time],
                                        y=[p1_price],
                                        mode='markers+text',
                                        marker=dict(
                                            size=10,
                                            color='rgba(100, 150, 255, 1)',
                                            symbol=p1_symbol,
                                            line=dict(width=1, color='white')
                                        ),
                                        text=['P1'],
                                        textposition='top center' if p1_is_high else 'bottom center',
                                        textfont=dict(size=8, color='rgba(100, 150, 255, 1)', family='Arial Black'),
                                        name='P1',
                                        showlegend=False,
                                        hovertemplate=f'<b>P1 {"High" if p1_is_high else "Low"}</b><br>${p1_price:,.2f}<extra></extra>'
                                    ))
                                    
                                    # Add P1 ray extending from pivot to end
                                    fig.add_trace(go.Scatter(
                                        x=[p1_exact_time, last_time],
                                        y=[p1_price, p1_price],
                                        mode='lines',
                                        line=dict(
                                            color='rgba(100, 150, 255, 0.6)',
                                            width=1.5,
                                            dash='dash'
                                        ),
                                        name='P1',
                                        showlegend=False,
                                        hoverinfo='skip'
                                    ))
                                    
                                    # Add P2 marker at exact pivot (opposite of P1)
                                    p2_symbol = 'triangle-down' if p1_is_high else 'triangle-up'
                                    fig.add_trace(go.Scatter(
                                        x=[p2_exact_time],
                                        y=[p2_price],
                                        mode='markers+text',
                                        marker=dict(
                                            size=10,
                                            color='rgba(255, 150, 100, 1)',
                                            symbol=p2_symbol,
                                            line=dict(width=1, color='white')
                                        ),
                                        text=['P2'],
                                        textposition='bottom center' if p1_is_high else 'top center',
                                        textfont=dict(size=8, color='rgba(255, 150, 100, 1)', family='Arial Black'),
                                        name='P2',
                                        showlegend=False,
                                        hovertemplate=f'<b>P2 {"Low" if p1_is_high else "High"}</b><br>${p2_price:,.2f}<extra></extra>'
                                    ))
                                    
                                    # Add P2 ray extending from pivot to end
                                    fig.add_trace(go.Scatter(
                                        x=[p2_exact_time, last_time],
                                        y=[p2_price, p2_price],
                                        mode='lines',
                                        line=dict(
                                            color='rgba(255, 150, 100, 0.6)',
                                            width=1.5,
                                            dash='dash'
                                        ),
                                        name='P2',
                                        showlegend=False,
                                        hoverinfo='skip'
                                    ))
                                    
                                    # Add price annotations at end of rays
                                    fig.add_annotation(
                                        x=last_time,
                                        y=p1_price,
                                        text=f"${p1_price:,.0f}",
                                        showarrow=False,
                                        xanchor="left",
                                        xshift=3,
                                        font=dict(size=8, color='rgba(100, 150, 255, 0.9)'),
                                        bgcolor='rgba(30, 30, 30, 0.7)',
                                        bordercolor='rgba(100, 150, 255, 0.3)',
                                        borderwidth=1,
                                        borderpad=1
                                    )
                                    
                                    fig.add_annotation(
                                        x=last_time,
                                        y=p2_price,
                                        text=f"${p2_price:,.0f}",
                                        showarrow=False,
                                        xanchor="left",
                                        xshift=3,
                                        font=dict(size=8, color='rgba(255, 150, 100, 0.9)'),
                                        bgcolor='rgba(30, 30, 30, 0.7)',
                                        bordercolor='rgba(255, 150, 100, 0.3)',
                                        borderwidth=1,
                                        borderpad=1
                                    )
                                    
                                    # Compact layout for mini view
                                    fig.update_layout(
                                        height=250,
                                        margin=dict(l=0, r=0, t=5, b=0),
                                        xaxis_title="",
                                        yaxis_title="",
                                        xaxis_rangeslider_visible=False,
                                        plot_bgcolor='rgba(30, 30, 30, 0.3)',
                                        paper_bgcolor='rgba(0,0,0,0)',
                                        font=dict(color='#E8E8E8', size=8),
                                        xaxis=dict(
                                            gridcolor='rgba(255, 255, 255, 0.05)',
                                            showgrid=True,
                                            zeroline=False,
                                            showticklabels=False
                                        ),
                                        yaxis=dict(
                                            gridcolor='rgba(255, 255, 255, 0.05)',
                                            showgrid=True,
                                            zeroline=False,
                                            side='right',
                                            tickfont=dict(size=8)
                                        ),
                                        hovermode='x unified',
                                        showlegend=False
                                    )
                                    
                                    # Display mini chart
                                    st.plotly_chart(fig, use_container_width=True, key=f"mini_chart_{ticker}")
                else:
                    st.info("Waiting for P1 and P2 to be established...")
    
    def render_weekly_analysis(tab_container):
        """Render weekly analysis by weekday"""
        with tab_container:
            current_utc_time = datetime.now(timezone.utc)
            current_weekday = current_utc_time.weekday()
            
            # Fetch weekly data
            try:
                data_start = current_utc_time - timedelta(days=365)
                weekly_klines = fetch_bybit_data(ticker, "D", data_start, current_utc_time, category)
            except:
                weekly_klines = None
            
            if weekly_klines is None or weekly_klines.empty:
                st.info("No data available for Weekly timeframe")
                return
            
            # Calculate pivot frequency by weekday
            weekly_klines_copy = weekly_klines.copy()
            weekly_klines_copy['date'] = weekly_klines_copy['start_time'].dt.date
            weekly_klines_copy['weekday'] = weekly_klines_copy['start_time'].dt.dayofweek
            weekly_klines_copy['weekday_name'] = weekly_klines_copy['start_time'].dt.day_name()
            
            # Filter by selected weekdays
            weekly_klines_copy = weekly_klines_copy[weekly_klines_copy['weekday'].isin(selected_weekdays_numeric)]
            
            if weekly_klines_copy.empty:
                st.info("No data available for selected weekdays")
                return
            
            # Determine this week's P1 and P2 weekday
            # Find the start of current week (Monday)
            days_since_monday = current_utc_time.weekday()
            week_start = current_utc_time - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            this_week_data = weekly_klines_copy[
                (weekly_klines_copy['start_time'] >= week_start) & 
                (weekly_klines_copy['start_time'] < week_end)
            ]
            
            # Get current day name
            weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            current_day_name = weekday_names[current_weekday]
            
            current_p1_weekday = None
            current_p2_weekday = None
            
            if not this_week_data.empty:
                high_idx = this_week_data['high'].idxmax()
                low_idx = this_week_data['low'].idxmin()
                high_time = this_week_data.loc[high_idx, 'start_time']
                low_time = this_week_data.loc[low_idx, 'start_time']
                
                # Determine which came first: high or low
                if high_time < low_time:
                    # High was first (P1), low was second (P2)
                    current_p1_weekday = high_time.weekday()
                    current_p2_weekday = low_time.weekday()
                else:
                    # Low was first (P1), high was second (P2)
                    current_p1_weekday = low_time.weekday()
                    current_p2_weekday = high_time.weekday()
            
            # Count P1 and P2 occurrences by weekday across all historical weeks
            p1_counts = {day: 0 for day in weekday_names}
            p2_counts = {day: 0 for day in weekday_names}
            p1_last = {day: None for day in weekday_names}
            p2_last = {day: None for day in weekday_names}
            
            today = date.today()
            
            # Group by week (using ISO calendar week)
            weekly_klines_copy['year'] = weekly_klines_copy['start_time'].dt.isocalendar().year
            weekly_klines_copy['week'] = weekly_klines_copy['start_time'].dt.isocalendar().week
            
            total_weeks = 0
            for (year, week), week_group in weekly_klines_copy.groupby(['year', 'week']):
                if week_group.empty:
                    continue
                
                total_weeks += 1
                
                # Find P1 and P2 for this week
                high_idx = week_group['high'].idxmax()
                low_idx = week_group['low'].idxmin()
                
                high_row = week_group.loc[high_idx]
                low_row = week_group.loc[low_idx]
                
                high_time = high_row['start_time']
                low_time = low_row['start_time']
                
                # Determine which came first
                if high_time < low_time:
                    p1_time = high_time
                    p2_time = low_time
                else:
                    p1_time = low_time
                    p2_time = high_time
                
                p1_weekday = p1_time.weekday()
                p2_weekday = p2_time.weekday()
                p1_weekday_name = weekday_names[p1_weekday]
                p2_weekday_name = weekday_names[p2_weekday]
                
                # Increment counts
                p1_counts[p1_weekday_name] += 1
                p2_counts[p2_weekday_name] += 1
                
                # Track last occurrence
                p1_last[p1_weekday_name] = (today - p1_time.date()).days
                p2_last[p2_weekday_name] = (today - p2_time.date()).days
            
            rows = []
            for weekday_name in weekday_names:
                p1_pct = (p1_counts[weekday_name] / total_weeks * 100) if total_weeks > 0 else 0.0
                p2_pct = (p2_counts[weekday_name] / total_weeks * 100) if total_weeks > 0 else 0.0
                
                rows.append({
                    'Weekday': weekday_name,
                    'P1 %': round(p1_pct, 1),
                    'Last P1': p1_last[weekday_name] if p1_last[weekday_name] is not None else '',
                    'P2 %': round(p2_pct, 1),
                    'Last P2': p2_last[weekday_name] if p2_last[weekday_name] is not None else ''
                })
            
            weekly_df = pd.DataFrame(rows)
            
            # Format for display
            display_weekly_df = weekly_df.copy()
            display_weekly_df['P1 %'] = display_weekly_df['P1 %'].apply(lambda x: f"{x:.1f}%")
            display_weekly_df['P2 %'] = display_weekly_df['P2 %'].apply(lambda x: f"{x:.1f}%")
            display_weekly_df['Last P1'] = display_weekly_df['Last P1'].apply(lambda x: '' if (pd.isna(x) or x == '') else f"{int(x)}d ago")
            display_weekly_df['Last P2'] = display_weekly_df['Last P2'].apply(lambda x: '' if (pd.isna(x) or x == '') else f"{int(x)}d ago")
            
            # Get max values for heatmap
            p1_max = weekly_df['P1 %'].max()
            p2_max = weekly_df['P2 %'].max()
            if pd.isna(p1_max) or p1_max <= 0:
                p1_max = 1
            if pd.isna(p2_max) or p2_max <= 0:
                p2_max = 1
            
            # Generate HTML table
            html_table = '<table style="width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 0;">'
            html_table += '<thead><tr style="background-color: rgba(255, 255, 255, 0.05);">'
            col_widths = {'Weekday': '22%', 'P1 %': '18%', 'Last P1': '18%', 'P2 %': '18%', 'Last P2': '18%'}
            for col in display_weekly_df.columns:
                width = col_widths.get(col, '10%')
                html_table += f'<th style="width: {width}; padding: 5px 4px; text-align: center; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; border: 1px solid rgba(255, 255, 255, 0.1); white-space: nowrap; background-color: rgba(255, 255, 255, 0.08);">{col}</th>'
            html_table += '</tr></thead>'
            
            html_table += '<tbody>'
            for idx, row in weekly_df.iterrows():
                row_bg = 'rgba(255, 255, 255, 0.02)' if idx % 2 == 1 else 'transparent'
                html_table += f'<tr style="background-color: {row_bg}; border: 1px solid rgba(255, 255, 255, 0.05);">'
                
                for col_idx, col in enumerate(display_weekly_df.columns):
                    cell_value = display_weekly_df.iloc[idx, col_idx]
                    width = col_widths.get(col, '10%')
                    cell_style = f'width: {width}; padding: 5px 4px; text-align: center; height: 32px; border: 1px solid rgba(255, 255, 255, 0.05); white-space: nowrap;'
                    
                    # Check if this is P1 or P2 cell for current weekday
                    is_p1_weekday = (idx == current_p1_weekday) if current_p1_weekday is not None else False
                    is_p2_weekday = (idx == current_p2_weekday) if current_p2_weekday is not None else False
                    
                    # Apply heatmap to P1% and P2% with improved shading
                    if col == 'P1 %':
                        try:
                            num_val = float(weekly_df.iloc[idx, col_idx])
                            if p1_max > 0:
                                intensity = min(num_val / p1_max, 1.0)
                                r, g, b, alpha = get_color_from_theme(intensity, color_theme)
                                # Enhanced gradient for weekly: stronger intensity
                                alpha = 0.2 + (intensity * 0.5)
                                cell_style += f' background-color: rgba({r}, {g}, {b}, {alpha});'
                        except:
                            pass
                        
                        # Add checkmark if this is current P1 weekday
                        if is_p1_weekday:
                            cell_value = f'✓ {cell_value}'
                            cell_style += ' border: 1.5px solid rgba(100, 150, 255, 0.4); border-radius: 3px; background-color: rgba(100, 150, 255, 0.08);'
                    elif col == 'P2 %':
                        try:
                            num_val = float(weekly_df.iloc[idx, col_idx])
                            if p2_max > 0:
                                intensity = min(num_val / p2_max, 1.0)
                                r, g, b, alpha = get_color_from_theme(intensity, color_theme)
                                # Enhanced gradient for weekly: stronger intensity
                                alpha = 0.2 + (intensity * 0.5)
                                cell_style += f' background-color: rgba({r}, {g}, {b}, {alpha});'
                        except:
                            pass
                        
                        # Add checkmark if this is current P2 weekday
                        if is_p2_weekday:
                            cell_value = f'✓ {cell_value}'
                            cell_style += ' border: 1.5px solid rgba(100, 150, 255, 0.4); border-radius: 3px; background-color: rgba(100, 150, 255, 0.08);'
                    
                    html_table += f'<td style="{cell_style}">{cell_value}</td>'
                
                html_table += '</tr>'
            
            html_table += '</tbody></table>'
            
            table_css = """
            <style>
            table {
                color: #E8E8E8;
            }
            table th, table td {
                font-size: 0.85rem;
            }
            </style>
            """
            
            # Display table and insights side-by-side (optimized for 1080p)
            col_table, col_insights = st.columns([2.2, 1])
            
            with col_table:
                st.markdown(table_css, unsafe_allow_html=True)
                st.markdown(html_table, unsafe_allow_html=True)
            
            with col_insights:
                st.markdown("### Key Insights")
                
                # Data points used
                st.success(f"✓ {total_weeks} weeks analyzed — statistics are reliable.")
                
                if current_p1_weekday is not None and current_p2_weekday is not None:
                    p1_weekday_name = weekday_names[current_p1_weekday]
                    p2_weekday_name = weekday_names[current_p2_weekday]
                    
                    # Get P1 and P2 times from this week's data
                    if not this_week_data.empty:
                        high_idx = this_week_data['high'].idxmax()
                        low_idx = this_week_data['low'].idxmin()
                        high_time = this_week_data.loc[high_idx, 'start_time']
                        low_time = this_week_data.loc[low_idx, 'start_time']
                        
                        # Determine P1 and P2 types based on chronological order
                        if high_time < low_time:
                            p1_type = "Weekly High"
                            p1_time_str = high_time.strftime("%A %H:00")
                            p2_type = "Weekly Low"
                            p2_time_str = low_time.strftime("%A %H:00")
                        else:
                            p1_type = "Weekly Low"
                            p1_time_str = low_time.strftime("%A %H:00")
                            p2_type = "Weekly High"
                            p2_time_str = high_time.strftime("%A %H:00")
                        
                        # Asset and P1/P2 info
                        st.markdown(f"**Asset:** {ticker}")
                        st.markdown(f"**Current P1:** {p1_type} - {p1_time_str}")
                        st.markdown(f"**Current P2:** {p2_type} - {p2_time_str}")
                        
                        st.divider()
                        
                        # P1 Status
                        p1_weekday_pct = p1_counts[p1_weekday_name] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        # % of P1s formed after current P1 weekday
                        p1_after_p1_total = 0
                        for i in range(current_p1_weekday + 1, 7):
                            p1_after_p1_total += p1_counts[weekday_names[i]] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        # % of P1s formed after current day of week
                        p1_after_current = 0
                        for i in range(current_weekday + 1, 7):
                            p1_after_current += p1_counts[weekday_names[i]] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        st.markdown(f"**P1 Status**  \nAfter {p1_weekday_name}: **{p1_after_p1_total:.1f}%** | After {current_day_name}: **{p1_after_current:.1f}%**")
                        
                        st.divider()
                        
                        # P2 Status
                        p2_weekday_pct = p2_counts[p2_weekday_name] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        # % of P2s formed after current P2 weekday
                        p2_after_p2_total = 0
                        for i in range(current_p2_weekday + 1, 7):
                            p2_after_p2_total += p2_counts[weekday_names[i]] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        # % of P2s formed after current day of week
                        p2_after_current = 0
                        for i in range(current_weekday + 1, 7):
                            p2_after_current += p2_counts[weekday_names[i]] / total_weeks * 100 if total_weeks > 0 else 0
                        
                        st.markdown(f"**P2 Status**  \nAfter {p2_weekday_name}: **{p2_after_p2_total:.1f}%** | After {current_day_name}: **{p2_after_current:.1f}%**")
                        
                        st.divider()
                        
                        # Time Summary
                        st.markdown(f"**Time Summary for Current Week — {ticker}**")
                        selected_weekdays_str = ", ".join(selected_weekdays) if selected_weekdays else "All days"
                        st.caption(f"Statistics are based on: {selected_weekdays_str}")
                        
                        # P1 Flip Risk (based on % of P1s formed after current day, accounting for time remaining in week)
                        if p1_after_current < 20:
                            st.success(f"✓ Low P1 flip risk — {p1_after_current:.1f}% of weeks form P1 after {current_day_name}")
                        elif p1_after_current < 50:
                            st.warning(f"⚠ Moderate P1 flip risk — {p1_after_current:.1f}% of weeks form P1 after {current_day_name}")
                        else:
                            st.error(f"✗ High P1 flip risk — {p1_after_current:.1f}% of weeks form P1 after {current_day_name}")
                        
                        # P2 Formation Likelihood (based on % of P2s formed after current day, accounting for time remaining in week)
                        if p2_after_current < 20:
                            st.success(f"✓ Likely P2 in place — {p2_after_current:.1f}% of weeks form P2 after {current_day_name}")
                        elif p2_after_current < 50:
                            st.warning(f"⚠ Moderate P2 formation chance — {p2_after_current:.1f}% of weeks form P2 after {current_day_name}")
                        else:
                            st.error(f"✗ Unlikely that P2 is in — {p2_after_current:.1f}% of weeks form P2 after {current_day_name}")
                else:
                    st.info("Waiting for P1 and P2 to be established...")
    
    # Add CSS to style radio buttons like tabs
    st.markdown("""
        <style>
        div[role="radiogroup"] {
            gap: 0.5rem;
        }
        div[role="radiogroup"] label {
            padding: 0.5rem 1rem;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 4px;
            cursor: pointer;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background-color: rgba(100, 150, 255, 0.2);
            border-bottom: 2px solid rgba(100, 150, 255, 0.8);
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create main tabs with persistence
    main_tab_options = ["Time", "Distance"]
    main_tab_index = 0
    if st.session_state.saved_main_tab in main_tab_options:
        main_tab_index = main_tab_options.index(st.session_state.saved_main_tab)
    
    selected_main_tab = st.radio(
        "Main Category",
        main_tab_options,
        index=main_tab_index,
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Save the selected main tab
    st.session_state.saved_main_tab = selected_main_tab
    
    if selected_main_tab == "Time":
        # Create nested tabs for different timeframes with persistence
        timeframe_options = ["Hourly", "4-Hour", "Session", "Daily", "Weekly", "Monthly"]
        timeframe_index = 3  # Default to "Daily"
        if st.session_state.saved_timeframe_tab in timeframe_options:
            timeframe_index = timeframe_options.index(st.session_state.saved_timeframe_tab)
        
        selected_timeframe = st.radio(
            "Timeframe",
            timeframe_options,
            index=timeframe_index,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # Save the selected timeframe tab
        st.session_state.saved_timeframe_tab = selected_timeframe
        
        # Render the appropriate timeframe analysis
        if selected_timeframe == "Hourly":
            render_pivot_analysis("hourly", "Hourly", st.container())
        elif selected_timeframe == "4-Hour":
            render_pivot_analysis("4h", "4-Hour", st.container())
        elif selected_timeframe == "Session":
            render_pivot_analysis("session", "Session", st.container())
        elif selected_timeframe == "Daily":
            render_pivot_analysis("daily", "Daily", st.container())
        elif selected_timeframe == "Weekly":
            render_weekly_analysis(st.container())
        elif selected_timeframe == "Monthly":
            render_pivot_analysis("monthly", "Monthly", st.container())
    
    elif selected_main_tab == "Distance":
        # Create nested tabs for distance analysis with persistence
        distance_options = ["Daily", "Weekly"]
        distance_index = 0  # Default to "Daily"
        if st.session_state.saved_distance_tab in distance_options:
            distance_index = distance_options.index(st.session_state.saved_distance_tab)
        
        selected_distance = st.radio(
            "Distance Timeframe",
            distance_options,
            index=distance_index,
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # Save the selected distance tab
        st.session_state.saved_distance_tab = selected_distance
        
        # Render the appropriate distance analysis
        if selected_distance == "Daily":
            st.info("Daily distance analysis coming soon...")
        elif selected_distance == "Weekly":
            st.info("Weekly distance analysis coming soon...")
