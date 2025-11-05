import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Streamlit App",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Navigation
page = st.navigation([
    st.Page("pages/data_fetcher.py", title="Data Fetcher", icon="📥", default=True),
    st.Page("pages/volume_analysis.py", title="Volume Analysis", icon="📊")
])
page.run()

