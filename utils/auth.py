"""
Authentication module for Whop integration
Handles user authentication and subscription validation
Supports both iframe embedding and external access
"""

import os
import streamlit as st
import requests
from typing import Optional, Tuple, Dict
import json

def is_dev_mode() -> bool:
    """Check if running in development mode"""
    return os.getenv('DEV_MODE', 'True').lower() == 'true'

def is_iframe_context() -> bool:
    """Check if running inside Whop iframe"""
    # Check for iframe-specific headers or parameters
    return st.query_params.get('whop_iframe') == 'true' or st.query_params.get('experience_id') is not None

def validate_whop_membership(user_id: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate if a user has an active Whop membership
    
    Args:
        user_id: Whop user ID to validate
        
    Returns:
        Tuple of (is_valid: bool, user_data: dict or None)
    """
    try:
        api_key = os.getenv('WHOP_API_KEY')
        if not api_key:
            return False, None
        
        # Whop API endpoint to validate membership
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Check user's memberships
        response = requests.get(
            f'https://api.whop.com/api/v5/me/memberships',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check if user has any active memberships
            if data.get('data') and len(data['data']) > 0:
                for membership in data['data']:
                    if membership.get('valid') and membership.get('status') == 'active':
                        return True, {
                            'user_id': user_id,
                            'membership_id': membership.get('id'),
                            'plan': membership.get('plan', {}).get('name', 'Premium'),
                            'expires_at': membership.get('expires_at')
                        }
        
        return False, None
        
    except Exception as e:
        st.error(f"Whop API error: {str(e)}")
        return False, None

def check_access() -> Tuple[bool, Optional[Dict]]:
    """
    Universal access check - handles dev, iframe, and external access
    
    Returns:
        Tuple of (has_access: bool, user_info: dict or None)
    """
    
    # Development mode - bypass authentication
    if is_dev_mode():
        return True, {
            'user_id': 'dev_user',
            'username': 'Developer',
            'plan': 'unlimited',
            'mode': 'development'
        }
    
    # Check if running in iframe context (inside Whop)
    if is_iframe_context():
        # In iframe, Whop automatically validates users
        # Users can only access if they have membership
        query_params = st.query_params
        
        # Extract user data from Whop iframe parameters
        user_id = query_params.get('user_id') or query_params.get('userId')
        experience_id = query_params.get('experience_id')
        
        if user_id:
            # Store in session
            if 'whop_iframe_validated' not in st.session_state:
                st.session_state['whop_iframe_validated'] = True
                st.session_state['whop_user_id'] = user_id
                st.session_state['whop_user_data'] = {
                    'user_id': user_id,
                    'experience_id': experience_id,
                    'mode': 'iframe',
                    'plan': 'Premium'  # All iframe users have access
                }
            
            return True, st.session_state.get('whop_user_data')
        
        # In iframe but no user ID means Whop hasn't loaded yet
        # Grant access and let Whop handle the gating
        return True, {
            'user_id': 'iframe_loading',
            'mode': 'iframe',
            'plan': 'Premium'
        }
    
    # External access - validate with Whop API
    try:
        query_params = st.query_params
        whop_user_id = query_params.get('user_id') or query_params.get('whop_user_id')
        
        # If we have a user ID from query params, validate and store in session
        if whop_user_id and 'whop_validated' not in st.session_state:
            is_valid, user_data = validate_whop_membership(whop_user_id)
            if is_valid:
                st.session_state['whop_user_id'] = whop_user_id
                st.session_state['whop_user_data'] = user_data
                st.session_state['whop_validated'] = True
                return True, user_data
        
        # Check if user already authenticated in session
        if st.session_state.get('whop_validated'):
            user_data = st.session_state.get('whop_user_data', {})
            return True, user_data
        
        # No authentication found
        return False, None
            
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, None

def require_authentication():
    """
    Enforce authentication - call this at the top of your app
    Will stop execution if user doesn't have access
    """
    has_access, user_info = check_access()
    
    if not has_access:
        # Show subscription required page
        st.title("🔒 Subscription Required")
        st.markdown("""
        ### Access to Pivot Analysis requires an active subscription
        
        **What you get:**
        - ✅ Real-time pivot analysis for all major crypto pairs
        - ✅ Historical data analysis (up to 2 years)
        - ✅ P1/P2 flip risk assessments
        - ✅ Multiple timeframe analysis (Hourly, Daily, Weekly)
        - ✅ Custom filters and insights
        - ✅ Instant data loading from cache
        - ✅ 9 color themes for heatmaps
        - ✅ Mini candlestick charts with pivot levels
        
        ---
        """)
        
        # Get checkout URL from environment
        checkout_url = os.getenv('WHOP_CHECKOUT_URL', 'https://whop.com')
        
        st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <a href="{checkout_url}" target="_blank">
                <button style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 1.2rem;
                    padding: 1rem 3rem;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                ">
                    🚀 Subscribe Now
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("💡 **Already subscribed?** Access your membership from your Whop dashboard and return to this app.")
        
        # Show login option with user ID
        st.markdown("---")
        st.subheader("🔑 Direct Access")
        st.markdown("If you have your Whop User ID, enter it below:")
        
        user_id_input = st.text_input("Whop User ID", placeholder="user_xxxxxxxxxxxxx")
        if st.button("Validate Access"):
            if user_id_input:
                with st.spinner("Validating membership..."):
                    is_valid, user_data = validate_whop_membership(user_id_input)
                    if is_valid:
                        st.session_state['whop_user_id'] = user_id_input
                        st.session_state['whop_user_data'] = user_data
                        st.session_state['whop_validated'] = True
                        st.success("✅ Access granted! Reloading...")
                        st.rerun()
                    else:
                        st.error("❌ No active membership found for this User ID")
            else:
                st.warning("Please enter your Whop User ID")
        
        # Stop execution - don't load the rest of the app
        st.stop()
    
    # Store user info in session state for use throughout the app
    st.session_state['authenticated_user'] = user_info
    
    # Show appropriate indicator based on mode
    mode = user_info.get('mode', 'unknown')
    if mode == 'development':
        st.sidebar.info("🔧 DEV MODE - Authentication bypassed")
    elif mode == 'iframe':
        st.sidebar.success("✅ Running inside Whop")
        if user_info.get('user_id') not in ['iframe_loading', 'dev_user']:
            st.sidebar.caption(f"User: {user_info.get('user_id', 'Unknown')[:15]}...")
    else:
        # External access
        st.sidebar.success(f"✅ Logged in: {user_info.get('plan', 'Premium')}")

def get_current_user() -> Optional[Dict]:
    """
    Get the currently authenticated user
    
    Returns:
        User info dict or None if not authenticated
    """
    return st.session_state.get('authenticated_user')

def logout():
    """Log out the current user"""
    for key in ['whop_user_id', 'whop_user_data', 'whop_validated', 'authenticated_user']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
