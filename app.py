import streamlit as st
from dotenv import load_dotenv
from utils.auth import require_authentication

# Load environment variables
load_dotenv()

# Page configuration (must be called before authentication check)
st.set_page_config(
    page_title="Pivot Analysis Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Require authentication (will stop execution if not authenticated)
# Set DEV_MODE=True in .env to bypass during development
require_authentication()

# Check if running in iframe (inside Whop)
is_iframe = st.query_params.get('whop_iframe') == 'true' or st.query_params.get('experience_id') is not None

# Custom CSS for neutral dark theme (Morty-inspired)
iframe_css = """
    /* Hide Streamlit branding in iframe */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
""" if is_iframe else ""

st.markdown(f"""
    <style>
        .main .block-container {{
            background-color: #1E1E1E;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        .stApp {{
            background-color: #1E1E1E;
        }}
        section[data-testid="stSidebar"] {{
            background-color: #252525;
        }}
        .stApp > header {{
            background-color: #252525;
        }}
        header[data-testid="stHeader"] {{
            background-color: #252525;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #E8E8E8;
        }}
        .stMarkdown {{
            color: #E8E8E8;
        }}
        .stDataFrame {{
            background-color: #2D2D2D;
        }}
        .stSelectbox label, .stTextInput label, .stDateInput label, .stButton button {{
            color: #E8E8E8;
        }}
        .stSelectbox > div > div {{
            background-color: #2D2D2D;
            color: #E8E8E8;
        }}
        .stTextInput > div > div > input {{
            background-color: #2D2D2D;
            color: #E8E8E8;
        }}
        .stDateInput > div > div > input {{
            background-color: #2D2D2D;
            color: #E8E8E8;
        }}
        .stButton > button {{
            background-color: #4A4A4A;
            color: #E8E8E8;
        }}
        .stButton > button:hover {{
            background-color: #5A5A5A;
        }}
        .stCaption {{
            color: #B0B0B0;
        }}
        {iframe_css}
    </style>
    """, unsafe_allow_html=True)

# Navigation
page = st.navigation([
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/data_fetcher.py", title="Data Fetcher", icon="📥"),
    st.Page("pages/volume_analysis.py", title="Volume Analysis", icon="📊"),
    st.Page("pages/pivot_analysis.py", title="Pivot Analysis", icon="📈")
])
page.run()

