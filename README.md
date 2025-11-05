# Streamlit Data Fetcher & Volume Analysis App

A Streamlit application for fetching and analyzing cryptocurrency trading data from Bybit and other exchanges.

## Features

- 📥 **Data Fetcher**: Fetch historical trading data from Bybit API
  - Support for multiple categories (spot, linear, inverse, option)
  - Auto-populated ticker symbols from exchange API
  - Customizable timeframes and date ranges
  - Candlestick price charts
  - Volume analysis charts
  - CSV export functionality

- 📊 **Volume Analysis**: Analyze volume metrics and trends (coming soon)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd "streamlit for whop"
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running Locally

Run the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8502` (or the port configured in `.streamlit/config.toml`).

## Configuration

The app uses port 8502 by default. You can change this in `.streamlit/config.toml`:

```toml
[server]
port = 8502
```

## Deployment

### Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with your GitHub account
4. Click "New app"
5. Select your repository and branch
6. Set the main file path to `app.py`
7. Click "Deploy"

### Other Platforms

#### Heroku

1. Create a `Procfile`:
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

2. Deploy using Heroku CLI or dashboard

#### Docker

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8502

CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
```

## Project Structure

```
.
├── app.py                 # Main application entry point
├── pages/
│   ├── data_fetcher.py   # Data fetching page
│   └── volume_analysis.py # Volume analysis page
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## API Integration

Currently supports:
- **Bybit V5 API**: Spot, Linear, Inverse, and Options trading data
- **Hyperliquid**: Coming soon

## License

MIT License

## Contributing

Feel free to submit issues and enhancement requests!
