# MVP deployment preparation — 2026-08-12

## Public API surface

- Disabled `GET /api/v1/dashboard`; it now returns `404` because the endpoint is not needed by the public booking workflow.
- Added a regression test to ensure the dashboard route cannot be reintroduced unintentionally.

## Frontend deployment configuration

- Added ignored local file `frontend/.env.production` with `VITE_API_BASE_URL`.
- Replace `YOUR-RENDER-SERVICE` with the deployed Render service hostname before the production frontend build. Rebuild and redeploy Pages after changing it.
