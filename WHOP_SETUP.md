# Whop Authentication Setup Guide

This app uses Whop for authentication and monetization. Follow this guide to set up and deploy.

## 🚀 Quick Start (Development)

**The app is currently in DEV_MODE** - authentication is bypassed for easy development.

```bash
# Your current setup already works!
streamlit run app.py --server.port 8502
```

You'll see a "🔧 DEV MODE" indicator in the sidebar confirming authentication is bypassed.

---

## 🔧 How It Works

### File Structure
```
/utils/auth.py          # Authentication logic
/app.py                 # Main entry point with auth check
/.env                   # Environment variables (DEV_MODE=True)
```

### Authentication Flow

1. **Development Mode (DEV_MODE=True)**
   - Authentication is bypassed
   - Full access to all features
   - Dev indicator shown in sidebar

2. **Production Mode (DEV_MODE=False)**
   - Requires Whop authentication
   - Shows subscription page if not authenticated
   - Full access only with valid subscription

---

## 📋 Setting Up Whop (When Ready)

### Step 1: Create a Whop App

1. Go to [Whop Developer Dashboard](https://whop.com/apps)
2. Click "Create App"
3. Fill in app details:
   - **Name**: Pivot Analysis Pro
   - **Description**: Real-time pivot analysis for crypto traders
   - **Type**: External Integration

### Step 2: Get Your Credentials

From the Whop dashboard, copy:
- **API Key** (for authentication)
- **Checkout URL** (your product subscription link)

### Step 3: Update `.env` File

```bash
# Switch to production mode
DEV_MODE=False

# Add your Whop credentials
WHOP_API_KEY=your_actual_api_key_here
WHOP_CHECKOUT_URL=https://whop.com/your-actual-product-link
```

### Step 4: Install Whop SDK

```bash
pip install whop
```

Update `requirements.txt`:
```txt
whop>=1.0.0
```

### Step 5: Implement Whop SDK in `utils/auth.py`

Replace the TODO section in `check_access()` function:

```python
# Production mode - check Whop authentication
try:
    from whop import Whop
    
    whop = Whop(api_key=os.getenv('WHOP_API_KEY'))
    
    # Get current user from Whop session
    user = whop.validate_license(st.query_params.get('token'))
    
    if user and user.valid:
        # Store in session
        st.session_state['whop_user_id'] = user.id
        st.session_state['whop_username'] = user.username
        st.session_state['whop_plan'] = user.plan
        
        return True, {
            'user_id': user.id,
            'username': user.username,
            'plan': user.plan,
            'mode': 'production'
        }
    else:
        return False, None
        
except Exception as e:
    st.error(f"Authentication error: {str(e)}")
    return False, None
```

---

## 🔄 Development Workflow

### Local Development (Current Setup)
```bash
# .env file
DEV_MODE=True

# Run normally
streamlit run app.py --server.port 8502
```

### Testing Whop Integration Locally
```bash
# .env file
DEV_MODE=False
WHOP_API_KEY=your_test_key

# Run to test auth flow
streamlit run app.py --server.port 8502
```

### Production Deployment
```bash
# .env file (or hosting platform environment variables)
DEV_MODE=False
WHOP_API_KEY=your_production_key
WHOP_CHECKOUT_URL=https://whop.com/your-product
```

---

## 🎯 What Users See

### Authenticated Users (Production)
- ✅ Full access to all pages
- ✅ Pivot Analysis with all features
- ✅ Real-time data and insights

### Unauthenticated Users (Production)
- 🔒 Subscription required page
- 📋 List of features included
- 🚀 "Subscribe Now" button → Whop checkout
- 💡 Login prompt for existing subscribers

### Developers (DEV_MODE=True)
- 🔧 Dev mode indicator in sidebar
- ✅ Full access without authentication
- 🚀 Normal development workflow

---

## 📊 Whop Features You Can Use

### 1. OAuth Authentication
```python
from whop import Whop

whop = Whop(api_key=os.getenv('WHOP_API_KEY'))
user = whop.oauth.get_user(token)
```

### 2. Subscription Validation
```python
# Check if user has active subscription
if user.has_active_subscription():
    # Grant access
```

### 3. Webhook Handling
```python
# Listen for subscription events
@app.route('/webhooks/whop', methods=['POST'])
def handle_whop_webhook():
    event = request.json
    if event['type'] == 'payment.succeeded':
        # Handle new subscription
```

### 4. Multiple Plans
```python
# Check user's plan tier
if user.plan == 'premium':
    # Show advanced features
elif user.plan == 'basic':
    # Show basic features
```

---

## 🚀 Deployment Options

### Streamlit Cloud
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Add environment variables:
   - `DEV_MODE=False`
   - `WHOP_API_KEY=your_key`
   - `WHOP_CHECKOUT_URL=your_url`
   - All Supabase variables

### Railway / Render / Fly.io
1. Deploy from GitHub
2. Set environment variables in dashboard
3. App automatically enforces authentication

---

## 💡 Tips

- **Keep DEV_MODE=True** while developing new features
- **Test with DEV_MODE=False** before deploying
- **Use Whop's test mode** for development testing
- **Monitor authentication** via Whop dashboard
- **Set up webhooks** for real-time subscription updates

---

## 🐛 Troubleshooting

### "Authentication error" in production
- Check WHOP_API_KEY is set correctly
- Verify user has active subscription
- Check Whop dashboard for API issues

### Can't bypass auth in development
- Ensure `DEV_MODE=True` in `.env`
- Restart Streamlit after changing `.env`
- Check `.env` file is in the correct directory

### Subscription page showing in dev mode
- `DEV_MODE` must equal exactly `'True'` (case-sensitive)
- Check for typos in `.env` file
- Verify `.env` is being loaded with `load_dotenv()`

---

## 📚 Resources

- [Whop Documentation](https://docs.whop.com/apps/introduction)
- [Whop Developer Dashboard](https://whop.com/apps)
- [Whop OAuth Guide](https://docs.whop.com/apps/oauth)
- [Whop Webhooks](https://docs.whop.com/apps/webhooks)

---

**Your app is ready to go!** Continue developing with DEV_MODE=True, then switch to production when you're ready to monetize. 🚀

