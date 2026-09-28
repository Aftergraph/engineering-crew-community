---
name: frontier-evals
description: Use when designing, running, or reviewing agent evals, regression corpora, holdouts, quality measurements, calibration, routing comparisons, or performance claims.
---

# Frontier Evals

Define the claim before the metric. Separate functional correctness, verified mission success, recovery, latency/cost proxies, calibration, and provider-backed performance evidence.

Use paired or holdout designs when comparing candidates. Bind identical task payloads, preserve execution order evidence, and keep promotion authority outside the evaluator. Synthetic, replayed, signed, authenticated, and live evidence are different classes.

When adaptive routing or competence learning is involved, update competence only from independently verified outcomes. Deduplicate evidence and keep updates bounded.

Do not convert a smoke test, one-pair proof, or successful provider call into a broad performance claim. Require preregistered gates and sufficient live evidence for comparative claims.

Return the claim, dataset/corpus identity, evidence class, run lineage, metric results, uncertainty, failed cases, and what the result does not establish.
