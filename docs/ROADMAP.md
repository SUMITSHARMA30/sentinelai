# Implementation roadmap

- [x] Starter API with schema validation, ML demo scorer, storage abstraction and basic tests
- [x] Interactive dashboard with live polling, metrics, chart, filters and investigation drawer
- [ ] Replace synthetic training labels with a public anonymized dataset; document license and provenance
- [ ] Time-aware / stratified evaluation, precision-recall curve, PR-AUC, recall at fixed precision, calibration
- [ ] Real feature store: velocity windows, account/merchant history, point-in-time correctness
- [ ] Kafka producer and consumer; idempotent writes and dead-letter topic
- [ ] Audit events, authenticated analyst roles, rate limiting and security hardening
- [ ] Model registry/versioning, drift metrics and retraining procedure
- [ ] CI pipeline, frontend tests, API integration tests, Dockerized app services
- [ ] Deploy API and UI with environment-specific secrets; configure MongoDB Atlas IP/network access
- [ ] Record demo video and publish architecture/limitations in portfolio

## Before any real-world use
This starter is not suitable for production payment decisions. Do not use real payment credentials or personal financial data. A production system needs rigorous validation, security review, privacy controls, human escalation, observability, rollback, and a compliant payment integration.
