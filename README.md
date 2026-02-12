# Who Pays Them?

**Enter your zip code. See your candidates. See who funds them.**

100% public FEC data. Non-partisan. No spin. Updated weekly.

## How It Works

1. Enter your zip code
2. See the candidates running in your district (U.S. Senate + U.S. House)
3. For each candidate: total raised, top donors, funding breakdown (individual vs PAC vs party vs self-funded)
4. Every dollar links back to FEC.gov

## Architecture

- **Data pipeline** (Python): Fetches candidate + donor data from the FEC API, generates static JSON
- **Frontend** (Next.js): Static site that loads pre-computed JSON — zero runtime API calls, instant load
- **Hosting**: Vercel (free tier)
- **Updates**: GitHub Actions runs the pipeline weekly

## Running Locally

```bash
# Pipeline
pip install -r pipeline/requirements.txt
cd pipeline && python -m pytest tests/ -v
python generate_data.py  # Requires FEC_API_KEY env var

# Frontend
cd web && npm install && npm run dev
```

## Data Sources

- [Federal Election Commission API](https://api.open.fec.gov/developers/) — candidate + donor data
- [U.S. Census Bureau](https://www.census.gov) — zip code to congressional district mapping

## License

Public domain.

Built by W.J. Cornelius and Claude.
