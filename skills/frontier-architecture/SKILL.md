---
name: frontier-architecture
description: Use when designing or changing system architecture, module ownership, APIs, schemas, contracts, data flow, authority boundaries, or multi-agent topology.
---

# Frontier Architecture

Design ownership before files. Define composition roots, reusable boundaries, allowed dependency directions and serialized contracts. Prefer package/feature boundaries that can be machine-checked.

Keep the Aftergraph non-equivalences explicit: cognition ≠ authority, selection ≠ admission, completion ≠ verification, learning ≠ promotion, UI projection ≠ canonical truth.

Use typed Mission Graph edges for dependencies that matter to correctness. Make side effects, authority, temporal ordering, verification and joins explicit rather than burying them in prose.

Preserve wire/schema compatibility through versioned contracts and staged adapters. Feature manifests describe ownership but never grant authority.

Deliver the architecture with invariants, component contracts, failure modes, migration path, verification strategy and which rules are executable rather than documentary.
