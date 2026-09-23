# Changelog

## Unreleased

### Added

- Extended Streaming History import (`python -m app.import_history`)
- Next-song Markov baseline (`app/ml/`, `GET /predict/next`, `python -m app.ml.train`)
- Installable `app` package via hatchling (`uv run python -m …` from `backend/`)
- Repo Cursor rules (git workflow, concise communication) and root `AGENTS.md`

### Changed

- Bulk play upserts for large imports
- Docs: README / AGENTS aligned with ML + export import
