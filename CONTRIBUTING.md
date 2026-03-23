# Contributing to EcoInvest

EcoInvest was originally built for **Inter-IIT Tech Meet 14.0**.  Contributions
that improve the codebase, documentation, or test coverage are welcome.

---

## Setting Up the Development Environment

### Prerequisites

- Docker & Docker Compose (for the full backend stack)
- Python 3.10+
- Node.js 18+

### Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add GOOGLE_API_KEY, TAVILY_API_KEY (required)

# Start the infrastructure (PostgreSQL, Kafka, Debezium, Redis, Pathway)
cd carbon-intelligence
docker-compose up -d --build

# Run the Flask API locally (from backend/)
python app.py
```

### Frontend

```bash
# From the repository root
npm install

# Copy and configure environment variables
cp .env.example .env
# Set VITE_API_URL=http://localhost:5001

# Start the dev server
npm run dev
```

The frontend will be available at http://localhost:5173.

---

## Branch Naming Convention

| Prefix | Purpose | Example |
|---|---|---|
| `feature/` | New features or capabilities | `feature/company-watchlist-export` |
| `fix/` | Bug fixes | `fix/rag-null-document-crash` |
| `docs/` | Documentation updates | `docs/cdc-deep-dive-corrections` |

Branch names should be lowercase and use hyphens, not underscores.

---

## Running Tests Before Submitting a PR

```bash
# Backend tests
cd backend
python -m pytest -v

# Frontend build check (catches TypeScript/JSX errors)
npm run build
```

All tests must pass before opening a pull request.  The CI workflow
(`.github/workflows/ci.yml`) runs automatically on every PR and will block
merging if either the backend tests or the frontend build fails.

---

## Pull Request Guidelines

1. Keep PRs focused — one logical change per PR.
2. Update relevant documentation in `docs/` if your change affects architecture,
   the CDC pipeline, or agent behaviour.
3. Add or update tests where appropriate.
4. Reference the related issue number in the PR description (`Closes #42`).

---

## Project Background

EcoInvest was submitted to **Inter-IIT Tech Meet 14.0** as a real-time carbon
credit market intelligence platform.  The core technical challenge was replacing
a 15–60 minute batch scraping cycle with a sub-2-second streaming CDC pipeline
using PostgreSQL WAL, Debezium, Apache Kafka, and the Pathway streaming
framework.
