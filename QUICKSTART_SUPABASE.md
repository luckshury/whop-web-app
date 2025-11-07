# Quick Start: Supabase Integration

## 🚀 5-Minute Setup

### 1. Create Supabase Project
- Go to [app.supabase.com](https://app.supabase.com) → New Project
- Save your password!

### 2. Run Database Schema
- Supabase → SQL Editor → New Query
- Copy contents of `supabase/schema.sql` → Run

### 3. Get API Keys
- Settings → API
- Copy **URL** and **anon key**

### 4. Set Environment Variables

**Local (.env file):**
```bash
cp env.example .env
# Edit .env with your keys
```

**Streamlit Cloud (Secrets):**
```toml
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_ANON_KEY = "your-anon-key"
```

**GitHub (for auto-updates):**
- Settings → Secrets → Actions
- Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`

### 5. Install Dependencies
```bash
pip install supabase python-dotenv
```

### 6. Backfill Data (15-20 min one-time)
```bash
python scripts/backfill_historical_data.py --all --days 730
```

### 7. Test It! 
```bash
streamlit run app.py
```

Go to Pivot Analysis → Select BTCUSDT → Analyze

You should see: ✨ **Instant load from cache!**

---

## 📊 What You Get

- ⚡ Sub-second loading for popular pairs
- 📅 2 years of historical 15m data
- 🔄 Auto-updates every 15 minutes (via GitHub Actions)
- 💰 Free (Supabase free tier)
- 👥 Shared cache for all users

---

## 🔍 Verify Setup

**Check data in Supabase:**
```sql
SELECT ticker, COUNT(*) FROM candles_15m GROUP BY ticker;
```

**Check app:**
- Try BTCUSDT (should be instant)
- Try obscure pair (falls back to API)

---

## 📚 Full Documentation
See `SUPABASE_SETUP.md` for detailed setup, troubleshooting, and advanced features.

---

## 🎯 Popular Pairs Pre-configured

| Ticker | Priority | Auto-Update |
|--------|----------|-------------|
| BTCUSDT | 1 | ✅ |
| ETHUSDT | 2 | ✅ |
| SOLUSDT | 3 | ✅ |
| BNBUSDT | 4 | ✅ |
| XRPUSDT | 5 | ✅ |
| +10 more | - | ✅ |

Add more pairs via SQL or backfill script!

