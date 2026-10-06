# MVP production infrastructure and R2 media — 2026-08-14

## Deployment

- Configured the public `vinfastbooking-media` Cloudflare R2 bucket for the Vercel and Cloudflare Pages production origins plus local Vite development origins.
- Published and uploaded 233 generated catalogue, content, gallery, and video objects (about 145 MB), plus 12 standardized brochure objects; verified 245 objects in the bucket.
- Added `frontend/r2-cors.json` so the CORS policy can be reapplied with Wrangler.
- Added `frontend/scripts/upload-r2-media.mjs` for repeatable, concurrent, retryable R2 uploads with the correct content type and cache metadata.
- Prepared the main-only frontend deployment workflow for the existing `vinfast-mvp` Cloudflare Pages project. The deploy job reuses the `dist` artifact produced by the build job instead of rebuilding it.
- Limited push-triggered frontend and backend workflows to `main`; pull requests into `testing`, `develop`, or `main` still run validation without duplicating a simultaneous `push` run on `develop`.

## Media catalogue compatibility

- Cloudflare rejected eight historical filenames containing double dots such as `VF3/2..png`.
- `backend/scripts/publish_site_media.py` now creates CDN-safe aliases without renaming the original frontend assets.
- `backend/src/services/site_catalog.py` now returns the CDN-safe alias paths for VF 3 and VF 5 catalogue media.
- The media publisher now rejects identical or nested source/destination trees before any cleanup, preventing CDN alias cleanup from deleting frontend source files.

## Production configuration

- Render requires `MEDIA_BASE_URL=https://pub-216eea433b9e4529979ce534d5ce0ae1.r2.dev` and `CORS_ORIGINS` containing `https://vinfast-mvp.pages.dev`, followed by a service restart.
- A live health request returned HTTP 200 but initially omitted `Access-Control-Allow-Origin` for Cloudflare Pages, confirming that the remaining frontend availability error was Render CORS configuration rather than Neon or FastAPI health.
- The `r2.dev` endpoint is suitable for the MVP; replace it with an R2 custom domain before a longer-lived production release.

## Frontend R2 runtime configuration

- Added `VITE_MEDIA_BASE_URL` to the Cloudflare Pages production build so frontend marketing assets prefer their public R2 object URLs.
- Added the same public media origin to the ignored local `frontend/.env.production` for reproducible production-mode builds.
- Neon remains unchanged: R2 stores media objects while the existing source catalogue maps vehicle and content identifiers to object paths.

## Neon initialization

- Added per-file and per-5,000-row progress logs for long-running dataset imports.
- Replaced per-row dataset inserts with 5,000-row `executemany` batches for both legacy and V5 datasets while preserving the all-or-nothing transaction and progress reporting.
- Integrated the latest `testing` importer and Internal Portal changes; admin import routes now require an authenticated Operations Admin, while the legacy public dashboard remains unavailable.
- Completed the initial Neon import with 159,127 rows and no missing expected CSV files.
- Kept `AUTO_LOAD_EVAL_DATA=false` for Render so deploys do not reseed production.
- Documented that later booking writes happen automatically and catalogue/schema changes require incremental import or migration instead of a full production reset.

## Documentation

- Replaced the outdated root README deployment description with the current Cloudflare Pages, R2, Render, Docker Hub and Neon architecture.
- Added reproducible WSL and PowerShell Neon seed instructions, verification SQL, production environment variables, media upload steps and data safety rules.
- Removed the public `/api/v1/dashboard` and unauthenticated `/api/v1/admin/import/*` surface; added API regression tests requiring all three paths to return 404.
