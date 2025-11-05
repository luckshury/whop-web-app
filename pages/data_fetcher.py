import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, date, time
import plotly.graph_objects as go

st.set_page_config(
    page_title="Data Fetcher",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
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

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Exchange selection
    exchange = st.selectbox(
        "Exchange",
        ["Bybit", "Hyperliquid"],
        index=0
    )
    
    st.markdown("---")
    
    # Category selection for Bybit
    if exchange == "Bybit":
        category = st.selectbox(
            "Category",
            ["spot", "linear", "inverse", "option"],
            index=0,
            help="Product category: spot, linear (USDT perpetual), inverse (coin perpetual), or option"
        )
        
        # Fetch symbols if category changed or not cached
        cache_key = f"{exchange}_{category}"
        if cache_key not in st.session_state.bybit_symbols:
            with st.spinner("Loading available symbols..."):
                symbols = fetch_bybit_symbols(category)
                st.session_state.bybit_symbols[cache_key] = symbols
        else:
            symbols = st.session_state.bybit_symbols[cache_key]
        
        # Ticker selection (selectbox that auto-populates from API)
        if symbols:
            default_index = 0
            if "BTCUSDT" in symbols:
                default_index = symbols.index("BTCUSDT")
            
            ticker = st.selectbox(
                "Ticker",
                options=symbols,
                index=default_index,
                help=f"Select from {len(symbols)} available trading pairs"
            )
        else:
            ticker = st.text_input(
                "Ticker",
                value="BTCUSDT",
                placeholder="Enter ticker symbol",
                help="Unable to fetch symbols. Please enter manually."
            )
    else:
        # Hyperliquid - placeholder for now
        category = "spot"  # Default for Hyperliquid
        ticker = st.text_input(
            "Ticker",
            value="BTC-USDT",
            placeholder="e.g., BTC-USDT, ETH-USDT",
            help="Hyperliquid integration coming soon"
        )
    
    # Timeframe selection
    timeframe = st.selectbox(
        "Timeframe",
        ["1", "3", "5", "15", "30", "60", "120", "240", "360", "720", "D", "W", "M"],
        index=5,  # Default to 60 minutes
        help="Timeframe in minutes (1, 3, 5, 15, 30, 60, etc.) or D/W/M for daily/weekly/monthly"
    )
    
    # Date range selection
    st.markdown("---")
    st.subheader("Date Range")
    
    date_range = st.date_input(
        "Select Date Range",
        value=(date.today() - timedelta(days=30), date.today()),
        max_value=date.today(),
        help="Select start and end dates"
    )
    
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
    
    # Fetch button
    fetch_button = st.button("🔍 Fetch Data", type="primary", use_container_width=True)

# Main content area
st.title("📥 Data Fetcher")
st.markdown("---")

# Function to fetch data from Bybit
def fetch_bybit_data(symbol, interval, start_time, end_time, category="spot"):
    """
    Fetch kline/candlestick data from Bybit V5 API with pagination support
    Documentation: https://bybit-exchange.github.io/docs/v5/market/kline
    """
    try:
        # Convert date objects to datetime if needed
        if isinstance(start_time, date) and not isinstance(start_time, datetime):
            start_time = datetime.combine(start_time, time.min)
        if isinstance(end_time, date) and not isinstance(end_time, datetime):
            end_time = datetime.combine(end_time, time.max)
        
        url = f"{BYBIT_API_BASE}/market/kline"
        all_klines = []
        current_start = start_time
        
        # Pagination: Bybit API limit is 200 per request
        max_limit = 200
        end_timestamp = int(end_time.timestamp() * 1000)
        
        while current_start <= end_time:
            params = {
                "category": category,  # spot, linear, inverse, option
                "symbol": symbol,
                "interval": interval,
                "start": int(current_start.timestamp() * 1000),  # Convert to milliseconds
                "end": end_timestamp,
                "limit": max_limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("retCode") == 0:
                result = data.get("result", {})
                klines = result.get("list", [])
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # If we got less than the limit, we've reached the end
                if len(klines) < max_limit:
                    break
                
                # Set next start time to the last timestamp + 1 interval
                last_timestamp = int(klines[-1][0])  # First element is timestamp
                last_datetime = datetime.fromtimestamp(last_timestamp / 1000)
                
                # Calculate next interval based on timeframe
                if interval.isdigit():
                    # Minutes
                    current_start = last_datetime + timedelta(minutes=int(interval))
                elif interval == "D":
                    current_start = last_datetime + timedelta(days=1)
                elif interval == "W":
                    current_start = last_datetime + timedelta(weeks=1)
                elif interval == "M":
                    # Approximate month as 30 days
                    current_start = last_datetime + timedelta(days=30)
                else:
                    current_start = last_datetime + timedelta(minutes=1)
            else:
                error_msg = data.get('retMsg', 'Unknown error')
                st.error(f"API Error: {error_msg}")
                return None
        
        if all_klines:
            # Convert to DataFrame
            df = pd.DataFrame(all_klines, columns=[
                "start_time", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            # Convert data types
            df["start_time"] = pd.to_datetime(df["start_time"].astype(int), unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)
            df["turnover"] = df["turnover"].astype(float)
            
            # Remove duplicates and sort by time
            df = df.drop_duplicates(subset=["start_time"])
            df = df.sort_values("start_time").reset_index(drop=True)
            
            return df
        else:
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"Request error: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# Display exchange info
col1, col2 = st.columns([3, 1])
with col1:
    if exchange == "Bybit":
        st.info(f"**Exchange:** {exchange} | **Category:** {category} | **Ticker:** {ticker} | **Timeframe:** {timeframe}")
    else:
        st.info(f"**Exchange:** {exchange} | **Ticker:** {ticker} | **Timeframe:** {timeframe}")

# Fetch data when button is clicked
if fetch_button:
    if not ticker:
        st.error("Please enter a ticker symbol!")
    elif start_date > end_date:
        st.error("Invalid date range!")
    else:
        with st.spinner(f"Fetching data from {exchange}..."):
            if exchange == "Bybit":
                df = fetch_bybit_data(ticker, timeframe, start_date, end_date, category)
                if df is not None and not df.empty:
                    st.session_state.data = df
                    st.success(f"✅ Successfully fetched {len(df)} data points!")
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
    
    st.subheader("📊 Volume Chart")
    st.bar_chart(st.session_state.data.set_index("start_time")[["volume"]])

else:
    st.info("👆 Configure your settings in the sidebar and click 'Fetch Data' to begin.")
