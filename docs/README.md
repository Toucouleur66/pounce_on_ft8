# Wait and Pounce — Documentation

This folder contains the **VitePress** user & developer guide for Wait and Pounce
(DX Pounce on FT8). Content was generated from the application source and its git history.

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
└── reference/              # settings, architecture, protocol, history, glossary
```

The static site is emitted to `docs/.vitepress/dist/` — serve that directory from any web host.
