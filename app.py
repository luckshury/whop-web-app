import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Pivot Analysis Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🚀 Pivot Analysis Pro")
st.success("✅ App is running!")

st.markdown("""
## Testing Deployment

If you see this, your app is successfully deployed to Streamlit Cloud!

### Next Steps:
1. Verify Supabase connection
2. Test authentication
3. Enable full features

### Environment Check:
""")

# Check if secrets are available
try:
    if hasattr(st, 'secrets'):
        st.success("✅ Streamlit secrets are available")
        
        if 'SUPABASE_URL' in st.secrets:
            st.success("✅ SUPABASE_URL is configured")
        else:
            st.error("❌ SUPABASE_URL is missing")
            
        if 'WHOP_API_KEY' in st.secrets:
            st.success("✅ WHOP_API_KEY is configured")
        else:
            st.error("❌ WHOP_API_KEY is missing")
            
        if 'DEV_MODE' in st.secrets:
            st.info(f"DEV_MODE = {st.secrets['DEV_MODE']}")
        else:
            st.warning("DEV_MODE not set (defaults to False)")
    else:
        st.warning("Running locally without secrets")
except Exception as e:
    st.error(f"Error checking secrets: {str(e)}")

# Test Supabase connection
st.markdown("### Testing Supabase Connection")
try:
    from utils.supabase_client import get_supabase_client
    
    client = get_supabase_client()
    if client:
        st.success("✅ Supabase client initialized")
    else:
        st.error("❌ Could not initialize Supabase client")
except Exception as e:
    st.error(f"❌ Supabase error: {str(e)}")

st.markdown("---")
st.markdown("Once this test page works, we'll switch back to the full app!")

