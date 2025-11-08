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
        :root {{
            color-scheme: dark;
        }}
        html, body {{
            background-color: #111 !important;
            color: #E8E8E8 !important;
        }}
        body * {{
            color: #E8E8E8;
        }}
        /* Force cache bust - v3 */
        .main .block-container {{
            background-color: #111 !important;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        .stApp {{
            background-color: #111 !important;
        }}
        .stApp > div {{
            background-color: #111 !important;
        }}
        section[data-testid="stSidebar"] {{
            background-color: #000 !important;
        }}
        section[data-testid="stSidebar"] > div {{
            background-color: #000 !important;
        }}
        .stApp > header {{
            background-color: #111 !important;
        }}
        header[data-testid="stHeader"] {{
            background-color: #111 !important;
        }}
        /* Hide the 3-dot menu button */
        button[kind="header"] {{
            display: none !important;
        }}
        /* Make toolbar/deploy button area seamless */
        [data-testid="stToolbar"] {{
            background-color: #111 !important;
        }}
        [data-testid="stStatusWidget"] {{
            background-color: #111 !important;
        }}
        [data-testid="stDecoration"] {{
            background-color: #111 !important;
        }}
        /* Force header children */
        header * {{
            background-color: #111 !important;
        }}
        /* Force main content area */
        [data-testid="stAppViewContainer"] {{
            background-color: #111 !important;
        }}
        [data-testid="stMain"] {{
            background-color: #111 !important;
        }}
        [data-testid="stSidebarNav"] {{
            background-color: #000 !important;
        }}
        /* Text colors */
        .stMarkdown p, .stMarkdown span, .stMarkdown div {{
            color: #E8E8E8 !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #E8E8E8 !important;
        }}
        .stMarkdown {{
            color: #E8E8E8 !important;
        }}
        .stDataFrame {{
            background-color: #2D2D2D !important;
        }}
        /* Input labels and fields */
        .stSelectbox label, .stTextInput label, .stDateInput label, .stButton button {{
            color: #E8E8E8 !important;
        }}
        .stSelectbox > div > div {{
            background-color: #2D2D2D !important;
            color: #E8E8E8 !important;
        }}
        .stTextInput > div > div > input {{
            background-color: #2D2D2D !important;
            color: #E8E8E8 !important;
        }}
        .stDateInput > div > div > input {{
            background-color: #2D2D2D !important;
            color: #E8E8E8 !important;
        }}
        .stButton > button {{
            background-color: #4A4A4A !important;
            color: #E8E8E8 !important;
        }}
        .stButton > button:hover {{
            background-color: #5A5A5A !important;
        }}
        div[data-baseweb="select"] {{
            background-color: #2D2D2D !important;
        }}
        div[data-baseweb="select"] * {{
            color: #E8E8E8 !important;
        }}
        .stRadio div[role="radiogroup"] > label {{
            color: #E8E8E8 !important;
        }}
        .stTabs [data-baseweb="tab-list"] {{
            background-color: #111 !important;
        }}
        .stTabs button {{
            color: #E8E8E8 !important;
        }}
        .stCaption {{
            color: #B0B0B0 !important;
        }}
        /* Checkbox styling */
        .stCheckbox label {{
            color: #E8E8E8 !important;
        }}
        .stCheckbox div[role="checkbox"] {{
            border-color: #E8E8E8 !important;
        }}
        /* Spinner styling */
        .stSpinner > div {{
            border-color: #E8E8E8 !important;
        }}
        /* Table styling */
        .stDataFrame div[data-testid="stHorizontalBlock"] {{
            background-color: #2D2D2D !important;
        }}
        .stDataFrame thead th {{
            background-color: #1f1f1f !important;
            color: #E8E8E8 !important;
        }}
        .stDataFrame tbody td {{
            color: #E8E8E8 !important;
        }}
        .st-emotion-cache-1629p8f, .st-emotion-cache-1qdco6z {{
            background-color: transparent !important;
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

