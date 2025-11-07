import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, date, time
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

st.set_page_config(
    page_title="Data Fetcher",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Bybit API base URL
BYBIT_API_BASE = "https://api.bybit.com/v5"

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'bybit_symbols' not in st.session_state:
    st.session_state.bybit_symbols = {}
if 'bybit_category' not in st.session_state:
    st.session_state.bybit_category = "spot"

# Function to fetch available symbols from Bybit
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_bybit_symbols(category="spot"):
    """
    Fetch available trading symbols from Bybit V5 API
    Documentation: https://bybit-exchange.github.io/docs/v5/market/instrument
    """
    try:
        url = f"{BYBIT_API_BASE}/market/instruments-info"
        
        params = {
            "category": category  # spot, linear, inverse, option
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("retCode") == 0:
            result = data.get("result", {})
            instruments = result.get("list", [])
            
            # Extract symbols that are tradable
            symbols = []
            for instrument in instruments:
                symbol = instrument.get("symbol", "")
                status = instrument.get("status", "")
                # Only include active trading symbols
                if symbol and status == "Trading":
                    symbols.append(symbol)
            
            # Sort symbols alphabetically
            symbols.sort()
            return symbols
        else:
            st.error(f"API Error fetching symbols: {data.get('retMsg', 'Unknown error')}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request error fetching symbols: {str(e)}")
        return []
    except Exception as e:
        st.error(f"Error fetching symbols: {str(e)}")
        return []

# Slim header bar with settings at the top
with st.container():
    # Create a compact horizontal layout for settings
    col1, col2, col3, col4, col5, col6 = st.columns([1.2, 1.2, 1.5, 1.2, 2, 1])
    
    with col1:
        exchange = st.selectbox(
            "Exchange",
            ["Bybit", "Hyperliquid"],
            index=0,
            label_visibility="collapsed"
        )
        st.caption("Exchange")
    
    with col2:
        if exchange == "Bybit":
            category = st.selectbox(
                "Category",
                ["spot", "linear", "inverse", "option"],
                index=0,
                help="Product category",
                label_visibility="collapsed"
            )
            st.caption("Category")
        else:
            category = "spot"
            st.caption("Category")
    
    with col3:
        if exchange == "Bybit":
            # Fetch symbols if category changed or not cached
            cache_key = f"{exchange}_{category}"
            if cache_key not in st.session_state.bybit_symbols:
                with st.spinner("Loading..."):
                    symbols = fetch_bybit_symbols(category)
                    st.session_state.bybit_symbols[cache_key] = symbols
            else:
                symbols = st.session_state.bybit_symbols[cache_key]
            
            # Ticker selection
            if symbols:
                default_index = 0
                if "BTCUSDT" in symbols:
                    default_index = symbols.index("BTCUSDT")
                
                ticker = st.selectbox(
                    "Ticker",
                    options=symbols,
                    index=default_index,
                    help=f"{len(symbols)} pairs available",
                    label_visibility="collapsed"
                )
            else:
                ticker = st.text_input(
                    "Ticker",
                    value="BTCUSDT",
                    placeholder="Enter ticker",
                    label_visibility="collapsed"
                )
            st.caption("Ticker")
        else:
            ticker = st.text_input(
                "Ticker",
                value="BTC-USDT",
                placeholder="BTC-USDT",
                label_visibility="collapsed"
            )
            st.caption("Ticker")
    
    with col4:
        timeframe = st.selectbox(
            "Timeframe",
            ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"],
            index=5,
            help="Timeframe",
            label_visibility="collapsed"
        )
        st.caption("Timeframe")
    
    with col5:
        date_range = st.date_input(
            "Select Date Range",
            value=(date.today() - timedelta(days=30), date.today()),
            max_value=date.today(),
            help="Select dates",
            label_visibility="collapsed"
        )
        st.caption("Date Range")
    
    with col6:
        fetch_button = st.button("🔍 Fetch", type="primary", use_container_width=True)
        st.caption("")  # Spacer for alignment

# Handle date range selection
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, date):
    start_date = date_range
    end_date = date.today()
else:
    start_date = date.today() - timedelta(days=30)
    end_date = date.today()

# Validate date range
if start_date > end_date:
    st.error("Start date must be before end date!")

st.markdown("---")

# Main content area
st.title("📥 Data Fetcher")

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
                # Reverse to get chronological order
                klines.reverse()
                return klines, None
            return [], None
        else:
            return None, data.get('retMsg', 'Unknown error')
    except Exception as e:
        return None, str(e)

# Function to fetch data from Bybit with concurrent requests
def fetch_bybit_data(symbol, interval, start_time, end_time, category="spot", progress_bar=None):
    """
    Fetch kline/candlestick data from Bybit V5 API with concurrent requests for speed
    Documentation: https://bybit-exchange.github.io/docs/v5/market/kline
    """
    try:
        # Convert date objects to datetime if needed
        if isinstance(start_time, date) and not isinstance(start_time, datetime):
            start_time = datetime.combine(start_time, time.min)
        if isinstance(end_time, date) and not isinstance(end_time, datetime):
            end_time = datetime.combine(end_time, time.max)
        
        url = f"{BYBIT_API_BASE}/market/kline"
        max_limit = 200
        
        # Calculate interval in seconds
        if interval.isdigit():
            interval_seconds = int(interval) * 60
        elif interval == "D":
            interval_seconds = 86400
        elif interval == "W":
            interval_seconds = 604800
        elif interval == "M":
            interval_seconds = 2592000
        else:
            interval_seconds = 60
        
        # First, make a test request to determine the date range per batch
        test_end = end_time
        test_start_ts = int(start_time.timestamp() * 1000)
        test_end_ts = int(test_end.timestamp() * 1000)
        
        test_session = requests.Session()
        test_klines, test_error = fetch_single_batch(
            test_session, url, category, symbol, interval, test_start_ts, test_end_ts, max_limit
        )
        
        if test_error:
            st.error(f"Test request failed: {test_error}")
            return None
        
        if not test_klines:
            return pd.DataFrame()
        
        # Determine batch size based on first response
        oldest_timestamp = int(test_klines[0][0])  # After reverse, first is oldest
        oldest_datetime = datetime.fromtimestamp(oldest_timestamp / 1000)
        
        # Calculate how many intervals fit in one batch (approximately)
        batch_duration = (test_end - oldest_datetime).total_seconds()
        intervals_per_batch = max(int(batch_duration / interval_seconds), 1) if interval_seconds > 0 else 1
        
        # Create date ranges for concurrent fetching
        date_ranges = []
        current_end = end_time
        batch_size_days = max(batch_duration / 86400, 1)  # Convert to days
        
        # Split into chunks for concurrent fetching (use larger chunks to reduce requests)
        # Each chunk should be roughly the size that returns ~200 records
        while current_end > start_time:
            chunk_start = max(start_time, current_end - timedelta(days=batch_size_days * 2))
            date_ranges.append((chunk_start, current_end))
            current_end = chunk_start - timedelta(milliseconds=1)
            if current_end < start_time:
                break
        
        # Reverse to process from oldest to newest
        date_ranges.reverse()
        
        status_text = st.empty()
        all_klines = []
        lock = Lock()
        
        # Use concurrent requests with ThreadPoolExecutor
        max_workers = min(10, len(date_ranges))  # Limit concurrent requests to avoid rate limiting
        
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
                oldest_dt = datetime.fromtimestamp(oldest_ts / 1000)
                
                chunk_klines.extend(klines)
                
                if oldest_dt <= chunk_start or len(klines) < max_limit:
                    break
                
                current_chunk_end = oldest_dt - timedelta(milliseconds=1)
            
            session.close()
            return chunk_klines
        
        # Fetch chunks concurrently
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
        test_session.close()
        
        if all_klines:
            # Convert to DataFrame
            df = pd.DataFrame(all_klines, columns=[
                "start_time", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            # Convert data types efficiently
            df["start_time"] = pd.to_datetime(df["start_time"].astype(int), unit="ms")
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = df[col].astype(float)
            
            # Remove duplicates and sort
            df = df.drop_duplicates(subset=["start_time"])
            df = df.sort_values("start_time").reset_index(drop=True)
            
            # Filter to requested range
            df = df[(df["start_time"] >= start_time) & (df["start_time"] <= end_time)]
            
            return df
        else:
            return None
            
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

# Fetch data when button is clicked
if fetch_button:
    if not ticker:
        st.error("Please enter a ticker symbol!")
    elif start_date > end_date:
        st.error("Invalid date range!")
    else:
        with st.spinner(f"Fetching data from {exchange}..."):
            if exchange == "Bybit":
                # Create progress bar for large data fetches
                progress_bar = st.progress(0)
                status_placeholder = st.empty()
                
                df = fetch_bybit_data(ticker, timeframe, start_date, end_date, category, progress_bar)
                
                progress_bar.empty()
                
                if df is not None and not df.empty:
                    st.session_state.data = df
                    st.success(f"✅ Successfully fetched {len(df):,} data points!")
                else:
                    st.warning("No data returned. Please check your parameters.")
            elif exchange == "Hyperliquid":
                st.info("Hyperliquid integration coming soon!")
                st.session_state.data = None

# Display data if available
if st.session_state.data is not None and not st.session_state.data.empty:
    st.markdown("---")
    st.header("📊 Data Preview")
    
    # Display statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", len(st.session_state.data))
    with col2:
        st.metric("Start Date", st.session_state.data["start_time"].min().strftime("%Y-%m-%d"))
    with col3:
        st.metric("End Date", st.session_state.data["start_time"].max().strftime("%Y-%m-%d"))
    with col4:
        st.metric("Latest Close", f"${st.session_state.data['close'].iloc[-1]:,.2f}")
    
    # Display dataframe
    st.subheader("Data Table")
    st.dataframe(st.session_state.data, use_container_width=True)
    
    # Download button
    csv = st.session_state.data.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"{ticker}_{timeframe}_{start_date}_{end_date}.csv",
        mime="text/csv"
    )
    
    # Candlestick chart
    st.subheader("📈 Price Chart (Candlestick)")
    
    # Create candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=st.session_state.data['start_time'],
        open=st.session_state.data['open'],
        high=st.session_state.data['high'],
        low=st.session_state.data['low'],
        close=st.session_state.data['close']
    )])
    
    fig.update_layout(
        title=f"{ticker} - {timeframe} Candlestick Chart",
        xaxis_title="Date",
        yaxis_title="Price",
        height=600,
        xaxis_rangeslider_visible=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👆 Configure your settings in the sidebar and click 'Fetch Data' to begin.")
