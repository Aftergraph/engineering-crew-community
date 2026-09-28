---
name: frontier-review
description: Use when independently reviewing a pull request, patch, branch, release candidate, code change, contract migration, or architecture change before acceptance.
---

# Frontier Review

Review the exact current diff/head, not a stale description. Reconstruct intended behavior and acceptance criteria before reading implementation details.

Prioritize correctness, authority expansion, stale evidence, distributed-state races, failure-path handling, compatibility, secret exposure and tests that cannot falsify the claimed behavior.

Do not accept builder statements as proof. Re-run or inspect the evidence needed for each material claim. Where proof is artifact-specific, verify subject SHA/version as well as repository head.

Check capability assumptions against Reality Registry maturity. A code path depending on an unavailable or integration-partial external system is not production-ready merely because mocks pass.

Return findings by severity with file/contract evidence and a clear distinction between verified facts, plausible risks and untested assumptions.
