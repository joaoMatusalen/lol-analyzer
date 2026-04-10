# LoL Analyzer

A web platform for performance analysis in League of Legends, using the official Riot Games API.

> **Developed by:** João Victor Magalhães Matusalen  
> &nbsp;[![GitHub](https://img.shields.io/badge/GitHub-joaoMatusalen-181717?logo=github)](https://github.com/joaoMatusalen)
> [![LinkedIn](https://img.shields.io/badge/LinkedIn-joaomatusalen-0A66C2?logo=linkedin)](https://www.linkedin.com/in/joaomatusalen/)


Project link: https://joaovictor-lolanalyzer.dev/


## About the Project

**LoL Analyzer** collects and processes data from your League of Legends matches directly from the Riot API, transforming raw statistics into clear visual insights. Just enter your summoner name, tag and region to get a full analysis of your match history.



## Features

- **General Statistics** — Average KDA, win rate, total damage, gold, farm and time played
- **Champion Analysis** — Detailed performance on your most played champion, with portrait via Data Dragon
- **Lane Performance** — Win rate and matches per position (Top, Jungle, Mid, Adc, Support)
- **Interactive Charts** — Daily evolution, patterns by time of day/day of week, stats by champion class and game mode
- **Match History** — The 20 most recent matches with color-coded KDA, gold, damage, CS and duration
- **Vision Score & Pings** — Full breakdown of wards and all 12 ping types
- **Incremental Updates** — Fetches only new matches since the last access, without reprocessing everything
- **Smart Cache** — Result stored for 30 days; automatic update every 2 hours
- **i18n Support** — Interface available in Portuguese (PT-BR) and English (EN)



## Technologies

**Backend**
- Python 3.11+
- Flask + Flask-Caching + Flask-Limiter
- Pandas + SciPy
- Gunicorn + Gevent
- Riot Games API (Account v1, Match v5, Summoner v4) + Data Dragon

**Frontend**
- HTML5, CSS3, JavaScript (ES Modules)
- Chart.js (via CDN)
- Font Awesome + Google Fonts (Cinzel, Inter)

**Infrastructure**
- Docker
- FileSystem Cache (`/tmp/cache`)



## Project Structure

```
lol-analyzer/
├── app.py                           # Main Flask file - defines routes, cache, rate limiting and integrations
├── dockerfile                       # Docker configuration for containerizing the application
├── gunicorn_conf.py                 # Gunicorn server configuration for production
├── requirements.txt                 # Python dependencies list (Flask, pandas, etc.)
├── .github/
│   └── workflows/
│       └── deploy.yml               # CI/CD pipeline for automatic deployment
├── api/                             # Python package with business logic
│   ├── __init__.py                  # API package initialization
│   ├── analytics.py                 # Statistical analysis functions (KDA, winrate, charts)
│   ├── client.py                    # HTTP client for Riot Games and Data Dragon APIs
│   ├── parser.py                    # Match data parsing and processing
│   └── service.py                   # Main orchestration for data collection and analysis
├── server/                          # Server configurations and async jobs
│   ├── jobs.py                      # Background job system for async processing
│   └── wsgi.py                      # WSGI entry point for the server
├── static/                          # Static files served by Flask
│   ├── css/
│   │   ├── dashboard.css            # CSS styles for the analysis dashboard
│   │   └── style.css                # CSS styles for the home page
│   ├── img/                         # Project images and icons
│   │   ├── about/                   # Images for the "About" section
│   │   ├── class/                   # Champion class icons (Tank, Mage, etc.)
│   │   ├── logo/                    # Site logo and favicon
│   │   ├── objectives/              # Objective icons (Baron, Dragon, Tower, etc.)
│   │   ├── pings/                   # In-game ping type icons
│   │   └── roles/                   # Position/lane icons (Top, Jungle, etc.)
│   └── js/                          # JavaScript scripts
│       ├── dashboard.js             # Dashboard logic (Chart.js charts, bindings)
│       └── main.js                  # Home page logic (form, polling)
└── templates/                       # HTML templates rendered by Jinja2
    ├── dashboard.html               # Dashboard page with statistics and charts
    └── index.html                   # Home page with search form
```



## How to Run

### Prerequisites

- Python 3.11+ or Docker
- Riot Games API key ([get one here](https://developer.riotgames.com/))

### With Python (development)

```bash
# 1. Clone the repository
git clone https://github.com/joaoMatusalen/lol-analyzer.git
cd lol-analyzer

# 2. Create and activate the virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set the environment variable with your Riot API key
export RGAPI_TOKEN="RGAPI-your-key-here"

# 5. Start the server
python wsgi.py
```

Access at `http://localhost:5000`

### With Docker

```bash
# Build the image
docker build -t lol-analyzer .

# Run
docker run -p 8000:8000 -e RGAPI_TOKEN="RGAPI-your-key-here" lol-analyzer
```

Access at `http://localhost:8000`



## Cache Architecture

The system uses a three-tier strategy to minimize API calls:

```
Request received
        │
        ▼
┌───────────────────────┐
│  Cache exists?        │  NO → Full analysis (up to 20 matches)
│  Is it recent (< 2h)?│
└───────────────────────┘
        │ YES
        ▼
  Returns cache
  immediately
        │
        │ Stale cache (> 2h) or force=true
        ▼
┌───────────────────────┐
│ Incremental analysis  │  Fetches only new matches,
│ (new matches only)    │  merges with cache and reprocesses
└───────────────────────┘
```


## Contributing

Contributions are welcome! Feel free to open issues to report bugs or suggest new features, and submit pull requests with improvements.



## License

This project is for personal/portfolio use. It is not affiliated with Riot Games.  
*"LoL Analyzer isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties."*
