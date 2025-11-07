# Supabase Integration Setup Guide

This guide will walk you through setting up Supabase for instant data loading in your Pivot Analysis app.

## 🎯 What You'll Get

- ⚡ **Instant loading** for popular crypto pairs
- 📊 **2+ years of historical 15m data** stored in the cloud
- 🔄 **Auto-updates every 15 minutes** via GitHub Actions
- 💰 **$0 cost** on Supabase free tier
- 👥 **Shared cache** for all your users

---

## 📋 Prerequisites

- GitHub account (for auto-updates)
- Supabase account (free tier is fine)
- Python 3.9+ installed locally

---

## Step 1: Create Supabase Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in:
   - **Name**: `crypto-pivot-analysis` (or any name)
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your users
4. Click "Create new project" (takes ~2 minutes)

---

## Step 2: Run SQL Schema

1. In your Supabase project, click **SQL Editor** (left sidebar)
2. Click "New Query"
3. Open `supabase/schema.sql` from this repo
4. Copy the entire contents
5. Paste into Supabase SQL Editor
6. Click **Run** (bottom right)

You should see: `Success. No rows returned`

This creates 4 tables:
- `candles_15m` - Historical candle data
- `pivot_analysis_cache` - Pre-computed results
- `popular_pairs` - Auto-update configuration
- `update_logs` - Monitoring logs

---

## Step 3: Get API Keys

1. In Supabase, go to **Settings** → **API** (left sidebar)
2. You'll see two keys:
   - **anon** key (public) - for read-only access
   - **service_role** key (secret) - for write access

**⚠️ Important**: Never commit the service_role key to git!

---

## Step 4: Configure Environment Variables

### For Local Development:

1. Copy the example env file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and fill in your keys:
   ```bash
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-anon-key-here
   SUPABASE_SERVICE_KEY=your-service-role-key-here
   ```

3. Make sure `.env` is in `.gitignore` (it should be by default)

### For GitHub Actions:

1. Go to your GitHub repo → **Settings** → **Secrets and variables** → **Actions**
2. Click "New repository secret"
3. Add these secrets:
   - `SUPABASE_URL` = Your Supabase project URL
   - `SUPABASE_SERVICE_KEY` = Your service_role key (NOT the anon key!)

### For Streamlit Cloud:

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Open your app settings → **Secrets**
3. Add:
   ```toml
   SUPABASE_URL = "https://your-project-id.supabase.co"
   SUPABASE_ANON_KEY = "your-anon-key-here"
   ```

**Note**: Only use the anon key in Streamlit Cloud (read-only access)

---

## Step 5: Install Dependencies

```bash
# Activate your virtual environment first
source venv/bin/activate  # On Mac/Linux
# or
venv\Scripts\activate  # On Windows

# Install new dependencies
pip install supabase python-dotenv
```

---

## Step 6: Backfill Historical Data

Now let's populate the database with 2 years of historical data for popular pairs.

### Option A: Backfill All Popular Pairs (~20 minutes)

```bash
python scripts/backfill_historical_data.py --all --days 730
```

This will:
- Fetch 2 years of 15m candles for all popular pairs (BTC, ETH, SOL, etc.)
- Insert ~700,000 rows into Supabase
- Takes 15-20 minutes (be patient!)

### Option B: Backfill Single Pair (for testing)

```bash
python scripts/backfill_historical_data.py --symbol BTCUSDT --days 730
```

### Monitor Progress

You can watch the progress in real-time:
- Open Supabase → **Table Editor** → `candles_15m`
- Refresh to see rows being added

---

## Step 7: Test the Integration

1. Start your Streamlit app:
   ```bash
   streamlit run app.py
   ```

2. Go to **Pivot Analysis** page
3. Select a ticker you backfilled (e.g., BTCUSDT)
4. Click "Analyze"

You should see:
```
✨ Loaded 35,040 candles from cache - instant load!
```

Instead of waiting 5-10 seconds, it should load in <1 second! 🚀

---

## Step 8: Enable Auto-Updates

### Via GitHub Actions (Recommended)

The workflow is already set up in `.github/workflows/update-candles.yml`

It will:
- Run every 15 minutes automatically
- Fetch latest candles for all popular pairs
- Keep your data fresh

**To enable:**
1. Make sure you added `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to GitHub Secrets (Step 4)
2. Push your code to GitHub:
   ```bash
   git add .
   git commit -m "Add Supabase integration"
   git push
   ```
3. Go to your repo → **Actions** tab
4. You should see "Update Candle Data" workflow

**Manual trigger** (for testing):
1. Go to **Actions** → **Update Candle Data**
2. Click "Run workflow" → "Run workflow"

### Via Local Cron Job (Alternative)

If you prefer to run updates locally:

```bash
# Add to crontab (Mac/Linux)
crontab -e

# Add this line (runs every 15 minutes):
*/15 * * * * cd /path/to/streamlit-for-whop && /path/to/venv/bin/python scripts/update_candles.py --all
```

---

## Step 9: Verify Everything Works

### Check Database

1. Supabase → **Table Editor** → `candles_15m`
2. You should see rows with recent timestamps
3. Check `update_logs` table for successful updates

### Check Streamlit App

1. Open your deployed app (or localhost)
2. Try different tickers:
   - Popular pairs (cached) → Instant load ✨
   - Non-popular pairs → Falls back to API 📡
3. You should see status messages indicating cache hits

---

## 🎉 You're Done!

Your app now has:
- ✅ Instant loading for popular pairs
- ✅ 2 years of historical data stored
- ✅ Auto-updates every 15 minutes
- ✅ Fallback to API for non-cached pairs

---

## 📊 Usage Stats & Monitoring

### View Data Size

```sql
-- Run in Supabase SQL Editor
SELECT 
    ticker,
    COUNT(*) as candle_count,
    MIN(timestamp) as oldest_candle,
    MAX(timestamp) as latest_candle
FROM candles_15m
GROUP BY ticker
ORDER BY candle_count DESC;
```

### Check Update Logs

```sql
SELECT 
    ticker,
    update_type,
    rows_affected,
    success,
    error_message,
    created_at
FROM update_logs
ORDER BY created_at DESC
LIMIT 20;
```

### Database Size

Supabase Dashboard → **Settings** → **Usage**
- Check "Database" size (should be <200MB for 10 pairs × 2 years)

---

## 🔧 Troubleshooting

### "Error fetching data from Supabase"

**Check:**
1. Are your environment variables set correctly?
   ```bash
   python -c "import os; print(os.getenv('SUPABASE_URL'))"
   ```
2. Is the anon key correct? (not the service key)
3. Did you run the schema SQL?

### "No data available"

**Solution:**
Run backfill for that specific ticker:
```bash
python scripts/backfill_historical_data.py --symbol ETHUSDT --days 730
```

### "GitHub Actions failing"

**Check:**
1. Secrets are set correctly (use service_role key)
2. View workflow logs: Actions → Latest run → Click on the job
3. Common issue: Wrong secret names (must be exact)

### "Supabase free tier limit reached"

**Options:**
1. Delete old candles:
   ```sql
   DELETE FROM candles_15m WHERE timestamp < NOW() - INTERVAL '1 year';
   ```
2. Reduce number of popular pairs (edit `supabase/schema.sql`)
3. Upgrade to Pro ($25/month) for 8GB database

---

## 💡 Tips & Best Practices

### Adding New Popular Pairs

1. Add to database:
   ```sql
   INSERT INTO popular_pairs (ticker, priority, auto_update) 
   VALUES ('ARBUSDT', 16, true);
   ```

2. Backfill historical data:
   ```bash
   python scripts/backfill_historical_data.py --symbol ARBUSDT --days 730
   ```

### Removing Pairs

```sql
DELETE FROM candles_15m WHERE ticker = 'DOGEUSDT';
DELETE FROM popular_pairs WHERE ticker = 'DOGEUSDT';
```

### Force Refresh Data

If you want to re-fetch all historical data:
```bash
python scripts/backfill_historical_data.py --all --force --days 730
```

### Monitor GitHub Actions

Set up email notifications:
1. GitHub repo → Settings → Notifications
2. Enable "Actions: Fail"

---

## 🚀 Performance Comparison

**Before (Direct API):**
- First load: 8-12 seconds
- Each user: Separate API calls
- Rate limits: Can be hit with many users

**After (Supabase):**
- First load: <1 second ⚡
- All users: Shared cache
- No rate limits for cached data

---

## 📈 Next Steps

### Optional Enhancements

1. **Real-time Updates**: Use Supabase Realtime to push live price updates
2. **More Pairs**: Add top 50 pairs to cache
3. **Weekly Backfill**: Run full backfill weekly to catch any missed data
4. **Monitoring Dashboard**: Create admin page to monitor cache health
5. **API Endpoints**: Expose your cache as a public API

---

## 🆘 Need Help?

- Supabase Docs: [https://supabase.com/docs](https://supabase.com/docs)
- Supabase Discord: [https://discord.supabase.com](https://discord.supabase.com)
- Check GitHub Issues in this repo

---

## 📝 Summary of Files Created

```
.
├── supabase/
│   └── schema.sql                    # Database schema
├── scripts/
│   ├── backfill_historical_data.py   # Initial data population
│   └── update_candles.py             # Continuous updates
├── utils/
│   └── supabase_client.py            # Supabase helper functions
├── .github/
│   └── workflows/
│       └── update-candles.yml        # Auto-update workflow
├── env.example                       # Environment template
└── SUPABASE_SETUP.md                 # This guide
```

Happy coding! 🎉

