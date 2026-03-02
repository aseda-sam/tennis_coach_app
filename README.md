# S²Serve

[![CI](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aseda-sam/tennis_coach_app/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Upload a tennis serve. See what your body is actually doing. Take that back to the court.

S²Serve (Second Serve) is a serve-analysis app that turns video into biomechanics phases and raw metrics you can actually use in practice. It is built as a coach-prep tool, not a replacement for a coach.

<p align="center">
  <img src="docs/assets/landing-page.png" alt="S²Serve home page with interactive demo and upload CTAs" width="720" />
</p>

<p align="center">
  <img src="docs/assets/phase-walkthrough.gif" alt="Walkthrough of the analysis dashboard scrubbing through serve phases" width="640" />
</p>

## Why this exists

Most tennis apps either over-index on dashboards or over-promise coaching. This project aims for a simpler middle:

- clear visual feedback
- practical serve metrics
- less time in-app, more time practicing

The app started as a personal build while working through LTA coaching concepts and trying to improve my own serve with better feedback loops.

## What you can do

- Upload serve videos and keep them organized
- Detect serve windows so you skip dead footage
- Run pose estimation and phase segmentation
- Review raw biomechanics metrics per serve window
- Rewatch video with overlays for context

<p align="center">
  <img src="docs/assets/analysis-dashboard.png" alt="Analysis dashboard showing pose overlay, feature curves, and 4-phase serve breakdown" width="720" />
</p>

## Quick start

```bash
git clone https://github.com/aseda-sam/tennis_coach_app.git
cd tennis_coach_app
docker compose up --build
```

Open:

- App: http://localhost:3000
- API docs: http://localhost:8000/docs

## Documentation map

Use this README for product context and a fast start. Technical depth lives closer to each code area:

- `docs/serve-mvp.md` - what the app is building now, the serve loop, and what is out of scope
- `docs/diagrams/README.md` - architecture and flow diagrams
- `backend/README.md` - backend setup, environment, and operations
- `backend/docs/README.md` - backend topic docs (config, jobs, observability, deploy)
- `frontend/README.md` - frontend setup, architecture, and UI implementation notes
- `CONTRIBUTING.md` - contribution workflow

## Contributing

Contributions are welcome, whether that is a bug fix, docs cleanup, a test gap, or a small UX improvement.

If you are new here, start with:

1. `CONTRIBUTING.md`
2. `docs/serve-mvp.md`
3. open an issue with your idea before large changes

## License

[MIT](LICENSE)

Built by [Aseda](https://github.com/aseda-sam). If this project is useful to you, I would genuinely love to hear what you are working on.
