# Changelog

## Unreleased

### Added

- Predictor breadth: `popularity`, `artist`, `cooccurrence`, sklearn `item_knn`
- Model registry + `GET /predict/models`; `GET /predict/next?model=`
- `PredictContext` shared across models; `train --model all|id`
- Extended Streaming History import (`python -m app.import_history`)
- Installable `app` package; Cursor rules + root `AGENTS.md`

### Changed

- Bulk play upserts for large imports
- Docs aligned with multi-model ML + export import
