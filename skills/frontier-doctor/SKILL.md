---
name: frontier-doctor
description: Use when diagnosing Engineering Crew plugin packaging, personal or repo marketplace discovery, cached installation state, plugin evaluation, hook availability, or local host compatibility.
---

# Frontier Doctor

Separate package truth from host truth.

Run package validation and the internal plugin evaluator first. Then inspect the relevant marketplace, source path, installed cache and enabled/config state. `marketplace_visible`, `source_present`, `installed_copy_present` and `verified_installed` are distinct facts.

For personal installs, inspect the personal marketplace and installed cache rather than assuming the source directory is what the host executes. A local marketplace can be correct while the installed cache is absent or stale.

Hook presence is not hook execution: bundled hooks require host support and trust. Report untrusted or unobservable hook state as unknown, never verified.

When a surface cannot be observed from the current environment, return the exact verification command or UI step needed; do not upgrade the status by inference.
