# Architecture

## Project Goal

Build a serverless machine-learning pipeline that produces weekly FBS college-football win probabilities using only information available before kickoff.

## Planned Data Sources

- College Football Data API
- The Odds API
- National Weather Service API

## Planned Pipeline

1. Collect scheduled FBS games and pre-kickoff feature data.
2. Validate timestamps to prevent post-kickoff data leakage.
3. Store and transform historical and current data.
4. Generate model-ready features.
5. Produce win-probability forecasts.
6. Compare forecasts with sportsbook market probabilities.
7. Evaluate prediction performance and monitor data/model drift.
8. Retrain or flag the model when performance degrades.

## Planned Components

- `src/ingestion/` — API and data ingestion
- `src/features/` — feature engineering
- `src/models/` — model training and prediction
- `src/evaluation/` — forecast evaluation
- `src/monitoring/` — drift and model-health monitoring
- `src/pipeline/` — orchestration of the end-to-end workflow

## Deployment

The final system is intended to run as a serverless or event-driven AWS pipeline. Specific AWS services and deployment details will be finalized as the project architecture develops.
