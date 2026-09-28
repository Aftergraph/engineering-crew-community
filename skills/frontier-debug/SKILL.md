---
name: frontier-debug
description: Use when a service, test, workflow, agent, integration, browser, or runtime fails, crashes, hangs, regresses, or behaves intermittently and the root cause must be proven.
---

# Frontier Debug

Reproduce before repairing. Separate product defect, environment defect, stale state, integration failure, policy denial and unavailable capability.

Build a causal timeline from logs/traces/evidence rather than a list of guesses. Inspect the actual path that failed: request → routing → authority → tool/runtime → effect → readback → verification.

Create a regression test or deterministic probe that fails for the observed cause. For browser/runtime problems, use the dedicated Browser Doctor/recovery primitives instead of assuming application code is responsible.

After a fix, rerun the reproducer plus the relevant broader suite. Re-read the live state when the bug involved cross-process files, leases, credentials or external effects.

Report root cause, evidence, patch, regression proof, exact source identity and any unverified environmental dependency.
