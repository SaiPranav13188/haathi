# Deploying Haathi

| Part | Where | How |
|---|---|---|
| Website (Next.js) | Vercel project `haathi` → https://haathi-ten.vercel.app | `cd frontend && npx vercel deploy --prod` (env: `BACKEND_URL`, `NEXT_PUBLIC_BACKEND_WS`, `NEXT_PUBLIC_SITE_URL`) |
| Backend, free | Render web service `haathi-api` → https://haathi-api.onrender.com | `cd backend && uv run python ../deploy/deploy_render.py <github-user>` pushes the private bundle; Render auto-deploys it |
| Backend, full models | Hugging Face Docker Space (needs HF PRO) | `cd backend && uv run python ../deploy/deploy_hf_space.py <hf-user>` |

The Render bundle (`deploy/render/`) runs the light engine (hashing embedder, lexical reranker, NumPy vector store,
about 255 MB RAM) so it fits the 512 MB free plan. It includes the official documents, so its repository stays private.
Set `GEMINI_API_KEY` in the Render dashboard. Never commit it.
