import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Bybit API base URL
BYBIT_API_BASE = "https://api.bybit.com/v5"

# Initialize session state
if 'bybit_symbols' not in st.session_state:
    st.session_state.bybit_symbols = {}
if 'bybit_category' not in st.session_state:
    st.session_state.bybit_category = "spot"
if 'volume_data' not in st.session_state:
    st.session_state.volume_data = None

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
        analyze_button = st.button("📊 Analyze", type="primary", use_container_width=True)
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

# Function to fetch data from Bybit
def fetch_bybit_data(symbol, interval, start_time, end_time, category="spot", progress_bar=None):
    """Fetch kline/candlestick data from Bybit V5 API"""
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
        
        # Calculate how many candles needed for 24H
        candles_per_24h = int(86400 / interval_seconds) if interval_seconds > 0 else 1
        
        # Create date ranges for fetching
        date_ranges = []
        current_end = end_time
        batch_size_days = 30  # Fetch in 30-day chunks
        
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
                oldest_dt = datetime.fromtimestamp(oldest_ts / 1000)
                
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
            # Convert to DataFrame
            df = pd.DataFrame(all_klines, columns=[
                "start_time", "open", "high", "low", "close", "volume", "turnover"
            ])
            
            # Convert data types
            df["start_time"] = pd.to_datetime(df["start_time"].astype(int), unit="ms")
            for col in ["open", "high", "low", "close", "volume", "turnover"]:
                df[col] = df[col].astype(float)
            
            # Remove duplicates and sort
            df = df.drop_duplicates(subset=["start_time"])
            df = df.sort_values("start_time").reset_index(drop=True)
            
            # Filter to requested range
            df = df[(df["start_time"] >= start_time) & (df["start_time"] <= end_time)]
            
            return df, candles_per_24h
        else:
            return None, candles_per_24h
            
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None, 0

# Calculate volume percentile and 24H price change
def calculate_volume_rank_map(df, lookback_period=60, candles_per_24h=24):
    """
    Calculate volume percentile and 24H price change for scatter plot
    
    Args:
        df: DataFrame with columns: start_time, close, volume, turnover
        lookback_period: Number of candles to look back for volume percentile calculation
        candles_per_24h: Number of candles that make up 24 hours
    
    Returns:
        DataFrame with volume_percentile and price_change_24h columns
    """
    if df is None or df.empty or len(df) < candles_per_24h + lookback_period:
        return None
    
    result = []
    
    for i in range(candles_per_24h + lookback_period, len(df)):
        # Current candle
        current_volume = df.iloc[i]['volume']
        current_close = df.iloc[i]['close']
        current_turnover = df.iloc[i]['turnover']
        
        # Lookback window for volume percentile
        lookback_start = max(0, i - lookback_period)
        lookback_end = i
        lookback_volumes = df.iloc[lookback_start:lookback_end]['volume'].values
        
        if len(lookback_volumes) == 0:
            continue
        
        # Calculate volume percentile (0-100)
        volume_percentile = (np.sum(lookback_volumes <= current_volume) / len(lookback_volumes)) * 100
        
        # Calculate 24H price change (%)
        past_close = df.iloc[i - candles_per_24h]['close']
        price_change_24h = ((current_close / past_close) - 1) * 100
        
        result.append({
            'start_time': df.iloc[i]['start_time'],
            'volume_percentile': volume_percentile,
            'price_change_24h': price_change_24h,
            'turnover': current_turnover,
            'close': current_close,
            'volume': current_volume
        })
    
    return pd.DataFrame(result)

# Fetch and analyze data when button is clicked
if analyze_button:
    if not ticker:
        st.error("Please enter a ticker symbol!")
    elif start_date > end_date:
        st.error("Invalid date range!")
    else:
        with st.spinner(f"Fetching data from {exchange}..."):
            if exchange == "Bybit":
                progress_bar = st.progress(0)
                status_placeholder = st.empty()
                
                df, candles_per_24h = fetch_bybit_data(ticker, timeframe, start_date, end_date, category, progress_bar)
                
                progress_bar.empty()
                
                if df is not None and not df.empty:
                    # Calculate volume rank map
                    with st.spinner("Calculating volume percentiles and price changes..."):
                        volume_map_df = calculate_volume_rank_map(df, lookback_period=60, candles_per_24h=candles_per_24h)
                        
                        if volume_map_df is not None and not volume_map_df.empty:
                            st.session_state.volume_data = volume_map_df
                            st.success(f"✅ Successfully analyzed {len(volume_map_df):,} data points!")
                        else:
                            st.warning("Not enough data for analysis. Please select a longer date range.")
                            st.session_state.volume_data = None
                else:
                    st.warning("No data returned. Please check your parameters.")
                    st.session_state.volume_data = None
            elif exchange == "Hyperliquid":
                st.info("Hyperliquid integration coming soon!")
                st.session_state.volume_data = None

# Display scatter plot if data is available
if st.session_state.volume_data is not None and not st.session_state.volume_data.empty:
    # Minimal title
    st.markdown("### Volume Rank Map")
    
    # Prepare data for Vega-Lite
    df_plot = st.session_state.volume_data.copy()
    
    # Format datetime for display
    df_plot['time_str'] = df_plot['start_time'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Get Y-axis range for quadrant regions
    y_max = df_plot['price_change_24h'].max()
    y_min = df_plot['price_change_24h'].min()
    y_padding = (y_max - y_min) * 0.1 if y_max > y_min else 10
    
    # Prepare the main chart data - convert to dict for embedding in Vega spec
    chart_data = df_plot[['volume_percentile', 'price_change_24h', 'turnover', 'time_str']].copy()
    
    # Convert to list of dicts for Vega-Lite
    chart_values = chart_data.to_dict('records')
    
    # Create data for quadrant regions and divider lines
    quadrant_rects = [
        {"x": 20, "x2": 80, "y": float(y_min - y_padding), "y2": float(y_max + y_padding)},
        {"x": 40, "x2": 60, "y": float(y_min - y_padding), "y2": float(y_max + y_padding)}
    ]
    divider_lines = [
        {"x": 20, "y": float(y_min - y_padding), "y2": float(y_max + y_padding)},
        {"x": 80, "y": float(y_min - y_padding), "y2": float(y_max + y_padding)}
    ]
    
    # Create Vega-Lite specification matching Morty's structure
    vega_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": "container",
        "height": 500,
        "layer": [
            # Background rectangle 1 (outer region)
            {
                "data": {"values": [quadrant_rects[0]]},
                "mark": {
                    "type": "rect",
                    "fillOpacity": 0.02,
                    "stroke": "rgba(255, 255, 255, 0.2)",
                    "strokeDash": [3]
                },
                "encoding": {
                    "tooltip": {"value": None},
                    "x": {"field": "x", "scale": {"zero": False, "domain": [0, 100]}, "type": "quantitative"},
                    "x2": {"field": "x2"},
                    "y": {"field": "y", "scale": {"zero": False}, "type": "quantitative"},
                    "y2": {"field": "y2"}
                }
            },
            # Background rectangle 2 (middle region)
            {
                "data": {"values": [{"x": 30, "x2": 70, "y": float(y_min - y_padding), "y2": float(y_max + y_padding)}]},
                "mark": {
                    "type": "rect",
                    "fillOpacity": 0.03,
                    "stroke": "rgba(255, 255, 255, 0.2)",
                    "strokeDash": [3]
                },
                "encoding": {
                    "tooltip": {"value": None},
                    "x": {"field": "x", "scale": {"zero": False, "domain": [0, 100]}, "type": "quantitative"},
                    "x2": {"field": "x2"},
                    "y": {"field": "y", "scale": {"zero": False}, "type": "quantitative"},
                    "y2": {"field": "y2"}
                }
            },
            # Background rectangle 3 (inner region)
            {
                "data": {"values": [quadrant_rects[1]]},
                "mark": {
                    "type": "rect",
                    "fillOpacity": 0.05,
                    "stroke": "rgba(255, 255, 255, 0.2)",
                    "strokeDash": [3]
                },
                "encoding": {
                    "tooltip": {"value": None},
                    "x": {"field": "x", "scale": {"zero": False, "domain": [0, 100]}, "type": "quantitative"},
                    "x2": {"field": "x2"},
                    "y": {"field": "y", "scale": {"zero": False}, "type": "quantitative"},
                    "y2": {"field": "y2"}
                }
            },
            # Scatter plot - main data layer
            {
                "data": {"values": chart_values},
                "mark": {
                    "type": "circle",
                    "opacity": 0.4
                },
                "encoding": {
                    "x": {
                        "field": "volume_percentile",
                        "type": "quantitative",
                        "scale": {"zero": False, "domain": [0, 100], "clamp": True},
                        "axis": {"title": "Volume Percentile (0-100)"}
                    },
                    "y": {
                        "field": "price_change_24h",
                        "type": "quantitative",
                        "scale": {"zero": False, "clamp": True},
                        "axis": {"title": "24H Price Change (%)"}
                    },
                    "size": {
                        "field": "turnover",
                        "type": "quantitative",
                        "legend": {"title": "Turnover"}
                    },
                    "color": {
                        "field": "price_change_24h",
                        "type": "quantitative",
                        "legend": {"title": "24H Price Change (%)"},
                        "scale": {
                            "domain": [float(y_min), 0, float(y_max)],
                            "interpolate": "rgb",
                            "range": ["teal", "lightgray", "red"]
                        }
                    },
                    "tooltip": [
                        {"field": "time_str", "type": "nominal", "title": "Time"},
                        {"field": "volume_percentile", "type": "quantitative", "title": "Volume Percentile", "format": ".1f"},
                        {"field": "price_change_24h", "type": "quantitative", "title": "24H Price Change (%)", "format": ".2f"},
                        {"field": "turnover", "type": "quantitative", "title": "Turnover", "format": ",.0f"}
                    ]
                }
            }
        ],
        "config": {
            "background": "#1E1E1E",
            "view": {"stroke": None},
            "axis": {
                "domain": False,
                "labelColor": "#E8E8E8",
                "titleColor": "#E8E8E8",
                "tickColor": "#E8E8E8",
                "gridColor": "rgba(255, 255, 255, 0.1)"
            },
            "text": {"color": "#E8E8E8"}
        }
    }
    
    # Display Vega-Lite chart - data is embedded in spec, so no need to pass DataFrame
    st.vega_lite_chart(vega_spec, use_container_width=True)
    
else:
    st.info("👆 Configure your settings above and click 'Analyze' to generate the Volume Rank Map.")


