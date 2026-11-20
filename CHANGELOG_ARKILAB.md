# OrkiLab changelog

## Unreleased — Workspace and ComfyUI development (2026-11-20)

- Introduce a separate, multilingual ComfyUI Zone with its own navigation and a return-to-Workspace action.
- Add ComfyUI connection modes, read-only model and node inventories, and a searchable/favouritable workflow library with folder synchronization and collapsible tools.
- Add OrkiLab Bridge frontend integration for UI-workflow conversion through ComfyUI; requires a ComfyUI restart and real workflow testing.
- Add Generation Studio graph review, editable parameters, random seed control and browser-local presets.
- Add persistent generation history, safe media descriptors, image/audio/video previews and output downloads; mesh downloads do not yet have an interactive viewer.
- Add sequential LoRA strength comparison for standard loader nodes and an integrated workflow picker with compatibility hints.
- Add read-only GPU Manager using NVIDIA telemetry, automatic visible-page refresh, VRAM warnings and training-activity hints.
- Extend interface translations to the new modules. Full translations of custom-node inputs are not guaranteed.
- Document feature workflows, code map and validation limitations in [Workspace feature guide](docs/arkilab/WORKSPACE_FEATURES.md).

**Status:** implemented on the default branch, not yet released as a new version. `VERSION_ARKILAB` remains `0.2.0-rc.1`. ComfyUI Desktop, GPU and end-to-end regression tests remain pending; the entries above are not claims of production validation.

## 0.2.0-rc.1 — Workspace closeout candidate

- Make the modern Workspace the sole launcher entry point, including old `/legacy` bookmarks.
- Remove the preview label and update the documented launch flow.
- Preserve trainer engines and shared compatibility assets.
- User smoke testing reported successful trainer navigation; comprehensive regression and GPU validation remain pending.

## 0.2.0-dev.1 — Workspace preview

- Add opt-in dashboard, engine filters, hardware summary and local SQLite project metadata.
- Create, archive and restore projects without modifying training files.
- Preserve classic launcher and all existing trainers. Foundation runtime validation remains pending.

## 0.1.0-rc.2 — Foundation identity and validation candidate

- Original OrkiLab engine covers and README banner.
- English public README and personal maintainer attribution.
- Remove promotional links from launcher; retain original credits and model identifiers.

## 0.1.0-rc.1 — Foundation release candidate

- Add dependency-free regression tests for branding, version, updater guards and safe Git updates (temporary local repositories).
- Add Windows/Linux CI with no model downloads or GPU dependencies.
- Make package updates explicit with --deps; refuse external Python environments.
- Align launcher version, queue branding and start-script titles.
- Add acceptance checklist and local hardware test procedure.

Release candidate: CI and local hardware validation still required before stable designation.

## 0.1.0-dev — Foundation (2026-11-20)

- Introduce independent OrkiLab SVG branding, launcher title, palette, favicon and About panel.
- Preserve upstream documentation and MIT copyright.
- Document architecture, audit, roadmap, integration contracts, dataset plan, security and development rules.
- Replace destructive updater synchronization with fast-forward-only updates of the current origin branch; ZIP installations require a clone. Dependency updates retain upstream behavior.
- Extend ignore rules for private data and model weights.

Status: development snapshot; runtime validation pending. No training engine changes.

### Interface branding follow-up

- Unify the launcher, queue and all 21 launcher covers with the orbital O vector identity.
- Preserve legacy asset paths as compatibility aliases; use OrkiLab paths for new UI links.

- Rebrand all trainer interfaces and Dataset Forge; remove inherited promotional social links from trainer pages.
- Add regression checks for model-local branding assets and engine covers.

## Community links

- Disable inherited social links in documentation; reserve unlinked placeholders for future OrkiLab channels.
