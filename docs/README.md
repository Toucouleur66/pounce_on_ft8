# Wait and Pounce — Documentation

This folder contains the **VitePress** user guide for Wait and Pounce. This README is for whoever
builds and deploys the docs — the guide itself is entirely user-facing.

## Local preview / build

```bash
cd docs
npm install
npm run docs:dev      # live dev server at http://localhost:5173
npm run docs:build    # static build → docs/.vitepress/dist
npm run docs:preview   # preview the built site
```

## Structure

```
docs/
├── .vitepress/config.mjs   # site config, nav & sidebar
├── index.md                # landing page
├── guide/                  # user guide (features, workflows)
└── reference/              # settings, shortcuts, what's new, glossary
```

The static site is emitted to `docs/.vitepress/dist/` — serve that directory from any web host.

## Deploying to f5ukw.com

The guide is published at **https://f5ukw.com/wait-and-pounce/**. To build and deploy:

```bash
cd docs
./deploy-docs.sh             # build + rsync to the server
./deploy-docs.sh --dry-run   # preview what would change, deploy nothing
./deploy-docs.sh --no-build  # deploy the existing build without rebuilding
```

How it works:

- The site is built with `base: '/wait-and-pounce/'` (see `.vitepress/config.mjs`) so all asset
  paths match the sub-path.
- `deploy-docs.sh` rsyncs `dist/` to `/var/www/wait-and-pounce/` on the server via the
  `stl-reporting` SSH alias.
- nginx serves that directory as **plain static files** under `location /wait-and-pounce/`
  (placed above the Node proxy). The telemetry API and PM2 processes are never touched.

The server-side nginx block lives in the live config
(`/etc/nginx/sites-available/f5ukw.com`) and is mirrored for reference in
`f5ukw.com/telemetry-api/nginx.conf`.
