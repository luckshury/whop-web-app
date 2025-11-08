# Next.js Migration Plan

This document outlines the steps required to migrate the current Streamlit-based analytics app into the official [Whop Next.js App Template](https://github.com/whopio/whop-nextjs-app-template).

## 1. Current Stack Summary

- **Frontend**: Streamlit (Python)
- **Features**  
  - **Home**: Landing copy.  
  - **Data Fetcher**: User inputs (exchange, ticker, date range, intervals), fetches data from Bybit V5 API or Supabase cache, allows download/export.  
  - **Volume Analysis**: Uses fetched data to compute volume percentiles, 24h price change, displays scatter/heatmap charts. Originally used Plotly and later Vega-Lite.  
  - **Pivot Analysis**: Core product. Complex layout with nested tabs (Time → Hourly/4H/Session/Daily/Weekly/Monthly, Distance → Daily/Weekly). Generates pivot tables (P1/P2 identification), key insights, candlestick mini chart, session state persistence, color themes, caching, Supabase integration, Bybit fallback.
- **Data**  
  - **Supabase**: Stores pre-fetched Bybit candles (15m) for popular pairs.  
  - **Bybit API**: Used directly for live or cache-miss data.  
  - **GitHub Actions**: Keeps Supabase fresh (`scripts/update_candles.py`).  
  - **Session State**: Streamlit `st.session_state` persists UI selections.

## 2. Target Stack

- **Frontend**: Next.js 14 (App Router) via Whop template.  
- **UI Toolkit**: Template uses Tailwind + custom components. We'll replicate the dark theme (#111 main, #000 sidebar).  
- **Charts**:  
  - Use `react-vega` (Altair/Vega-Lite) for scatter/heatmap equivalents.  
  - Use `react-plotly.js` or `lightweight-charts` for candlestick chart with annotations.  
- **State Management**: React state + URL query params for persistence. Potential use of `zustand` if global state needed.  
- **Authentication**: Leverage Whop template’s auth guard (`useWhopAuth`). Must validate membership via Whop API before rendering experiences.  
- **Backend/Data**:  
  - Option A: Build Next.js API routes that call Supabase (via `@supabase/supabase-js`) + Bybit HTTP endpoints.  
  - Option B: Continue running Streamlit backend as microservice and call via HTTP. (Recommendation: API routes in Next.js to keep single deployment.)

## 3. Migration Phases

1. **Template Setup**
   - Fork Whop template into repo (subfolder `whop-app/`).  
   - Configure `.env.local` with Whop vars and existing Supabase/Bybit credentials.  
   - Run locally, ensure Whop iframe handshake works (`pnpm dev`).

2. **Shared Utilities & Data Layer**
   - Recreate helpers: date utilities, timezone handling (UTC), percent calculations.  
   - Implement API route `/api/bybit/kline` for live data.  
   - Implement API route `/api/supabase/candles` with pagination (using existing Python logic as reference).  
   - Implement `/api/pivots/calculate` replicating `calculate_pivot_analysis` logic in TypeScript.

3. **Frontend Pages**
   - `app/(dashboard)/page.tsx`: Home introduction.  
   - `app/(dashboard)/data-fetcher/page.tsx`: Form inputs, fetch data via API, display table, download CSV.  
   - `app/(dashboard)/volume-analysis/page.tsx`: Input section (persist from session), scatter/heatmap chart, summary stats.  
   - `app/(dashboard)/pivot-analysis/page.tsx`:  
     - Build nested tabs.  
     - Render pivot table with heatmap, checkmarks, current hour highlight.  
     - Key insights panel.  
     - Mini candlestick chart (Plotly).  
     - Color theme selector with persistence.

4. **Styling & UX**
   - Port global dark theme.  
   - Build reusable components for inputs, metrics, tables.  
   - Mirror layout widths (columns ratio, spacing).

5. **Authentication & Routing**
   - Utilize Whop template’s `withAuth` HOC or middleware to enforce membership for experiences.  
   - Provide graceful fallback (link to install experience).  
   - Ensure iframe query params (`experienceId`, `userId`) propagate to API routes for per-user logging (if needed).

6. **Testing & Deployment**
   - Unit test core calculations (pivots, percentages).  
   - End-to-end check inside Whop dev environment.  
   - Deploy to Vercel; update Whop hosting base/app path.  
   - Decommission or archive Streamlit app once parity confirmed.

## 4. Outstanding Questions

1. Should analytics heavy lifting remain in Python (reused via FastAPI) or move entirely to TypeScript?  
2. Do we need historical caching beyond Supabase (e.g., Redis)?  
3. Any UX updates planned alongside migration (new features or layout changes)?

Clarifying these will inform the backend design and development timeline.

