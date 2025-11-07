# Whop Integration Guide

Your Pivot Analysis app is now integrated with Whop! Here's how to complete the setup.

> **📌 Note:** This guide covers **External Integration** (standalone website).  
> For **Iframe Embedding** (app inside Whop dashboard), see **[WHOP_IFRAME_SETUP.md](WHOP_IFRAME_SETUP.md)**

## ✅ What's Already Done

- ✅ Whop credentials added to `.env`
- ✅ Whop SDK installed
- ✅ Authentication system implemented
- ✅ Subscription gate active (when DEV_MODE=False)

## 🚀 Complete Setup (5 Minutes)

### Step 1: Create Your Product on Whop

1. Go to [whop.com](https://whop.com)
2. Click **"Create"** → **"Product"**
3. Fill in product details:
   - **Name**: Pivot Analysis Pro
   - **Description**: Advanced crypto pivot analysis with real-time data
   - **Price**: Your choice (e.g., $29/month or $99/year)
   - **Type**: Digital Product / Software Access

4. **Copy your product/checkout URL** - it will look like:
   ```
   https://whop.com/your-username/pivot-analysis
   ```

### Step 2: Update Your `.env` File

Add your checkout URL:

```bash
# Replace this with your actual checkout URL
WHOP_CHECKOUT_URL=https://whop.com/your-username/pivot-analysis
```

### Step 3: Test in Development

Your app is currently in **DEV_MODE**:
- Authentication is bypassed
- You can develop freely
- You'll see "🔧 DEV MODE" in the sidebar

### Step 4: Go Live (When Ready)

In your `.env` file, change:

```bash
# Switch to production mode
DEV_MODE=False
```

Now the app requires Whop authentication!

---

## 🔐 How Authentication Works

### For Your Users:

1. **User visits your app**
   - Sees subscription page
   - Clicks "Subscribe Now"
   
2. **Subscribes on Whop**
   - Pays via Whop checkout
   - Gets membership

3. **Returns to app**
   - Either via direct link with `?user_id=xxx`
   - Or enters their User ID manually
   
4. **Access granted**
   - App validates with Whop API
   - Full access to all features

### Access Methods:

**Method 1: Direct Link (Recommended)**
```
https://your-app-url.com?user_id=user_xxxxxxxxxxxxx
```

**Method 2: Manual Entry**
- User enters their Whop User ID on the subscription page
- App validates and grants access

---

## 🎨 Customization

### Change Subscription Page

Edit `/utils/auth.py` → `require_authentication()` function:
- Modify the benefits list
- Change button styling
- Add custom messaging

### Multiple Plans

If you have multiple tiers (Basic, Premium, Pro):

1. Update `validate_whop_membership()` to check plan names
2. Gate features based on `user_info.get('plan')`

Example:
```python
user = get_current_user()
if user.get('plan') == 'Premium':
    # Show advanced features
    show_premium_features()
```

---

## 📊 Testing

### Test Flow:

1. Set `DEV_MODE=False` in `.env`
2. Restart app
3. You'll see subscription page
4. Click "Subscribe Now" → goes to your Whop product
5. After subscribing, return with `?user_id=your_user_id`

### Get Your User ID:

Go to [dash.whop.com](https://dash.whop.com) and find your User ID

---

## 🔧 Troubleshooting

### "No active membership found"

**Causes:**
- User ID is incorrect
- Subscription hasn't processed yet
- Subscription expired

**Fix:**
- Verify User ID format: `user_xxxxxxxxxxxxx`
- Check Whop dashboard for active memberships
- Ensure API key is correct in `.env`

### API Key Issues

**Test your API key:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://api.whop.com/api/v5/me/memberships
```

Should return your memberships JSON

### DEV_MODE Not Working

**Check:**
- `.env` file has `DEV_MODE=True`
- App was restarted after changing `.env`
- `load_dotenv()` is called in `app.py`

---

## 🚀 Deployment

### Environment Variables

When deploying (Railway, Streamlit Cloud, etc.), set:

```bash
DEV_MODE=False
WHOP_API_KEY=s6uH7Ai74uhvQ8RgLknX7m2EbVA7K4ntzxZiFjfSOs8
WHOP_APP_ID=app_DJhUuup8LkNM5l
WHOP_COMPANY_ID=biz_knsV903sM2sJ3d
WHOP_CHECKOUT_URL=https://whop.com/your-product
```

Plus all your Supabase credentials.

### Deploy URL

Once deployed, configure your Whop product:
- Add your app URL in product description
- Create a button that links to: `your-app-url.com?user_id={USER_ID}`

---

## 📚 Advanced Features

### Webhooks (Optional)

Listen for subscription events:
- `payment.succeeded`
- `membership.went_valid`
- `membership.went_invalid`

Add webhook endpoint to automatically update user access.

### OAuth Flow (Advanced)

For seamless login without manual User ID entry:
1. Implement OAuth redirect
2. Store tokens in session
3. Auto-authenticate on return

See: [Whop OAuth Docs](https://docs.whop.com/apps/oauth)

---

## 🎯 Your Current Setup

```
✅ App ID: app_DJhUuup8LkNM5l
✅ Company ID: biz_knsV903sM2sJ3d
✅ API Key: Configured
✅ Authentication: Ready
⏳ Checkout URL: Needs your product link
```

---

## 🆘 Support

- **Whop Docs**: https://docs.whop.com
- **Whop Discord**: Join the Whop community
- **API Reference**: https://docs.whop.com/api-reference

---

**You're all set!** Just create your product on Whop, add the checkout URL, and you're ready to monetize! 💰

