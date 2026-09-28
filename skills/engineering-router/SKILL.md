---
name: engineering-router
description: Use when an engineering request needs to be classified, scoped, reality-checked, or delegated before implementation, debugging, review, research, release, integration, browser work, evals, autonomy, or recovery.
---

# Engineering Router

Start from current system truth. Identify the desired outcome, source-of-truth repository/artifact, acceptance evidence, authority boundary and external capabilities the mission depends on.

When shell execution exists, use `crewctl route`, `crewctl reality`, and `crewctl knowledge` as deterministic baselines. The packaged knowledge snapshot is release-time context, not a substitute for fresh reads when repository heads, infrastructure, credentials, availability or maturity may have changed.

Select the minimum sufficient crew and topology. Load only chosen role references. Use capability maturity as a blocker: `integration_partial`, `beta`, or `unavailable` never silently becomes `verified`.

Adaptive/JEV-style routing is advisory. Feed its proposal through the existing authority envelope; recommended tools, backends, models, memory or external context cannot expand scopes.

For consequential work, preserve independent builder/verifier roles. Return a compact mission frame: outcome, workflow, topology, roles, acceptance criteria, capability blockers, authority boundary, source identity and next safe work unit.
