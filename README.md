# Weather-Aware Truck Routing

React + Django app that helps a truck driver compare up to three route alternatives using weather, load weight, and estimated travel time.

## What it does

1. Driver enters origin, destination, departure time, load weight, and checkpoint interval (10 / 25 / 50 miles).
2. The backend requests route alternatives, samples weather at checkpoints using each checkpoint’s ETA, classifies risk, and ranks routes.
3. The results workspace shows route cards, a recommendation, an interactive map, checkpoint details, and a 0–48 hour corridor weather overlay.

Stage 1 is the trip form only. The map is not mounted until analysis starts.

## Stack

- Frontend: React 19, Vite, MapLibre GL JS, OpenFreeMap tiles
- Backend: Django, httpx
- Routing: public OSRM (default) or OpenRouteService (`driving-hgv` with an API key)
- Geocoding: Photon for address/place search, with Open-Meteo city search as a fallback when Photon is unavailable
- Weather: Open-Meteo hourly wind, precipitation, and snowfall

Free-tier providers have rate limits and no uptime guarantee. Confirm current terms before a public deployment.

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py runserver 127.0.0.1:8000
```

Optional: set `ROUTING_PROVIDER=ors` and `ORS_API_KEY` in `backend/.env` for truck-profile routing.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to the Django server.

## Deploy to Vercel + Render

The frontend is a Vite static site for Vercel; the Django API runs as a Render web service. The API is stateless and does not require a database.

### 1. Push the repository to GitHub

Commit and push the project, including `render.yaml` and `frontend/vercel.json`. Do not commit `.env` files or API keys.

### 2. Deploy the API on Render

1. In Render, choose **New → Blueprint** and connect this repository. Render reads the root `render.yaml` and creates the Django web service.
2. In the Blueprint settings, replace `https://your-vercel-project.vercel.app` in `CORS_ALLOWED_ORIGINS` with the exact Vercel production origin after you create the Vercel project (step 3). An origin is just scheme + hostname: no path or trailing slash.
3. Wait for the service to deploy. Its health check is `https://<render-service>.onrender.com/api/health/`; a successful response is `{"status":"ok"}`.

Render generates `DJANGO_SECRET_KEY`. `DJANGO_DEBUG` is disabled. No database or provider secret is needed for the default OSRM, Photon, Open-Meteo, and OpenFreeMap endpoints. For OpenRouteService instead, set `ROUTING_PROVIDER=ors` and add `ORS_API_KEY` as a secret in the Render service environment; redeploy after changing environment variables.

### 3. Deploy the frontend on Vercel

1. In Vercel, import the same repository and set **Root Directory** to `frontend`.
2. Vercel uses `frontend/vercel.json`: build command `npm run build`, output directory `dist`, and SPA fallback rewrites.
3. In the Vercel project’s **Settings → Environment Variables**, add `VITE_API_BASE_URL` with the Render API origin, for example `https://<render-service>.onrender.com` (no trailing slash). Set it for Production and any other environments you intend to use.
4. Deploy or redeploy the Vercel project. Vite embeds `VITE_API_BASE_URL` at build time, so changing it requires a new deployment.

### 4. Confirm production CORS

In Render’s service environment, set `CORS_ALLOWED_ORIGINS` to the exact frontend origin shown by Vercel, for example `https://<project>.vercel.app`. For a custom Vercel domain, include that origin too; multiple origins are comma-separated. Save and redeploy the API. Vercel preview deployments use different origins, so add the specific preview origin when testing previews, or test against the production domain.

### Environment variables at a glance

| Service | Variable | Value |
| --- | --- | --- |
| Render API | `DJANGO_SECRET_KEY` | Generated securely by the Blueprint; do not share or commit it. |
| Render API | `DJANGO_DEBUG` | `false` |
| Render API | `CORS_ALLOWED_ORIGINS` | Exact Vercel site origin(s), comma-separated. |
| Vercel frontend | `VITE_API_BASE_URL` | Render service origin, without a trailing slash. |
| Render API, optional | `ROUTING_PROVIDER` | `ors` to use OpenRouteService instead of OSRM. |
| Render API, optional | `ORS_API_KEY` | Secret key required only when `ROUTING_PROVIDER=ors`. |

Render's free web services may spin down when idle, so the first API request after inactivity may take longer. The app uses public routing, geocoding, weather, and map services; those providers can rate-limit requests and do not guarantee uptime. The default OSRM profile is car routing, not HGV-restricted routing.

### Tests

```bash
cd backend && .venv\Scripts\python -m pytest
cd frontend && npm test
```

## Risk rules

Bands are half-open at the lower bound so every value maps to one level. Rain/snow No Travel is strictly greater than 1.00 / 3.0 in/hr.

| Condition | Low | Moderate | High | Severe | No Travel |
| --- | --- | --- | --- | --- | --- |
| Wind | < 25 mph | 25–34 | 35–44 | 45–54 | ≥ 55 mph |
| Rain | < 0.10 in/hr | 0.10–0.25 | 0.25–0.50 | 0.50–1.00 | > 1.00 |
| Snow | < 0.5 in/hr | 0.5–1.0 | 1.0–2.0 | 2.0–3.0 | > 3.0 |

Load overrides (wind only):

- ≥ 55 mph → No Travel for any load
- 45–54 mph and load > 30,000 lb → No Travel
- 35–44 mph and load > 40,000 lb → Severe

Overall checkpoint risk is the worst known condition. Missing forecast is `UNKNOWN`, never Low.

Mileage is assigned from the previous checkpoint to the current one. Average risk is distance-weighted (Low=0 … Severe=3). No Travel is a hard-stop flag, not folded into the average.

Ranking (lexicographic): routes without No Travel first, then fewest Severe miles, fewest High miles, lowest average risk, shortest duration, then provider order. If every route has No Travel, the least-bad option is shown with a warning that none is fully safe.

## Assumptions

- ETAs spread the provider duration along the route by distance (uniform-speed approximation, not certified truck navigation).
- Forecast timestamps are hourly; a checkpoint uses the hour containing its ETA.
- The 0–48h slider is relative to departure and only changes the corridor overlay. Route risk still uses ETA-based weather.
- If the router returns fewer than three alternatives, those routes are shown; extras are not invented.
- The app can be hosted as a Vercel frontend and Render API using the deployment configuration above.

## Known limitations

- Public OSRM is car routing, not HGV-restricted.
- Photon and Open-Meteo public endpoints may throttle, especially from shared hosting IPs. The geocoder falls back to Open-Meteo place search when Photon is unreachable, which may be less precise for street addresses. Forecast HTTP 429 responses are retried using the provider's `Retry-After` value (bounded to 30 seconds); recurring limits require lower request volume or a weather provider plan with dedicated quota.
- OpenFreeMap tiles are used without a private key; they can fail or change.
- Analysis is on-demand and stateless (no trip database).
