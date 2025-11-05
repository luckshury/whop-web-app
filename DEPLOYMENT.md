# Deployment Guide

## Push to GitHub

1. **Create a new repository on GitHub:**
   - Go to https://github.com/new
   - Choose a repository name (e.g., "streamlit-data-fetcher")
   - Make it public or private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

2. **Connect your local repository to GitHub:**
```bash
cd "/Users/kayadacosta/streamlit for whop"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your actual GitHub username and repository name.

## Deploy to Streamlit Cloud (Easiest)

1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository
5. Set main file path to: `app.py`
6. Click "Deploy"

Your app will be live at: `https://YOUR_APP_NAME.streamlit.app`

## Alternative: Deploy with GitHub Actions

If you prefer CI/CD, you can set up GitHub Actions for automated deployment.

## Environment Variables (if needed)

If you need to add API keys or secrets later:
- Streamlit Cloud: Add them in the app settings under "Secrets"
- Create a `.streamlit/secrets.toml` file locally (not committed to git)

