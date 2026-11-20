# ArkiLab changelog

## 0.1.0-rc.1 — Foundation release candidate

- Add dependency-free regression tests for branding, version, updater guards and safe Git updates (temporary local repositories).
- Add Windows/Linux CI with no model downloads or GPU dependencies.
- Make package updates explicit with --deps; refuse external Python environments.
- Align launcher version, queue branding and start-script titles.
- Add acceptance checklist and local hardware test procedure.

Release candidate: CI and local hardware validation still required before stable designation.

## 0.1.0-dev — Foundation (2026-11-20)

- Introduce independent ArkiLab SVG branding, launcher title, palette, favicon and About panel.
- Preserve upstream documentation and MIT copyright.
- Document architecture, audit, roadmap, integration contracts, dataset plan, security and development rules.
- Replace destructive updater synchronization with fast-forward-only updates of the current origin branch; ZIP installations require a clone. Dependency updates retain upstream behavior.
- Extend ignore rules for private data and model weights.

Status: development snapshot; runtime validation pending. No training engine changes.
