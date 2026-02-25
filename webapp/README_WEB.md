# Agentic AI YouTube Bot - SaaS Platform

## Core Components
1. **Backend API**: `webapp/api.py` (FastAPI + JWT Auth + SQLite)
2. **Dashboard**: `webapp/index.html` (Modern UI + Phosphor Icons)
3. **Database**: `webapp/saas.db` (Auto-generated on first run)

## How to Run
1. Install new dependencies:
   ```bash
   pip install fastapi uvicorn sqlalchemy python-jose[cryptography] passlib[bcrypt] stripe python-multipart
   ```
2. Start the API server:
   ```bash
   python webapp/api.py
   ```
3. Open `webapp/index.html` in your browser.

## Features
- **User Authentication**: Secure Login/Signup.
- **Credit System**: Users get 5 free runs, then must upgrade.
- **Premium Dash**: Glassmorphism UI with real-time stats.
- **Video History**: Track all generations directly from the web.
- **Payment Success**: Integrate Stripe in `webapp/api.py` under the `/payment` endpoint.
