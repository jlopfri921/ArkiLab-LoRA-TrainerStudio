# OrkiLab 0.3.0-rc.1 — release readiness and evidence register

**Date:** 2026-11-21  
**Status:** NOT READY TO TAG. This is a release-candidate readiness record, not release notes or a declaration of acceptance.  
**Version in main at review:** `VERSION_ARKILAB = 0.2.0-rc.1`.  
**Baseline:** `main`, following merged PR #33 (commit `9f3ed80204bfeddfc6b780abc634cc2cd13de18a`). Confirm SHA again before executing local tests.

## Rules for recording evidence

- `PASS` requires an identifiable run, observed result and environment (commit SHA, Windows/Linux, GPU, ComfyUI Desktop version where relevant).
- `REPORTED` means the operator says they exercised a scenario, but no per-case pass/fail log is attached. It is **not** equivalent to `PASS`.
- `NOT VERIFIED` means no sufficient evidence has been recorded; it does not imply failure.
- `BLOCKED` means a failing critical release gate with reproducible evidence.
- `NOT APPLICABLE` requires a reason (e.g. multi-GPU on a single-GPU machine).

Do not convert reported successes into PASS by inference; do not fabricate screenshots, logs or test output.

## Candidate scope / freeze

Focus on stable ComfyUI connection, discovery, trusted workflow import/Bridge, explicit execution with cancellation/progress/history, optional resource release and diagnostics, read-only GPU Manager, standard LoRA-strength comparison, and preserved trainer launching and queue. **Do not block this RC on the full rewrite of every trainer UI, Dataset Studio, multiview, Ollama, Hub or installer.** See [roadmap](ROADMAP.md).

## Gate checklist

| Gate | Status as of review | Proof needed | Blocking when failing? |
| --- | --- | --- | --- |
| Windows CI unit tests | NOT VERIFIED | Workflow job URL + result for release SHA | Yes |
| Linux CI unit tests | NOT VERIFIED | Workflow job URL + result for release SHA | Yes |
| Browser trainer smoke test | NOT VERIFIED | `tools/smoke_test_ui.py` output + any failed engine | Yes for regression |
| Workspace/ComfyUI connection gate | REPORTED | Connect/disconnect screen evidence and route behavior | Yes |
| API-format workflow prepare/execute | REPORTED | Trusted graph identifier, status and output | Yes |
| Bridge conversion of visual workflow | REPORTED | Graph, preparation stages, actual converted run | Yes |
| Progress and safe cancel | REPORTED | Pending/active cancel evidence, preserve unrelated queue entries | Yes |
| History, result downloads, media previews | NOT VERIFIED | Image/audio/video evidence and refresh persistence | Yes for supported types |
| RAM/VRAM diagnostics and optional release | NOT VERIFIED | Before/peak/after readings + no impact on unrelated jobs | Yes for advertised scope |
| GPU Manager single-GPU RTX 3090 | REPORTED | Compare telemetry against `nvidia-smi` | Yes |
| Multi-GPU hardware | NOT VERIFIED | Two-adapter setup or explicit NOT APPLICABLE with reason | No if appropriately scoped |
| LoRA Comparator standard-loader path | NOT VERIFIED | Two strengths, sequential run, errors/cancel handling | Yes for advertised scope |
| 8-language Workspace navigation | NOT VERIFIED | Browser screenshots/smoke, English fallback | Yes for UI regression |
| Trainer representative image/video/audio | NOT VERIFIED | Brief per-family tests, saved settings parity | Yes for regression |
| Failure handling / auth / invalid node | NOT VERIFIED | Negative tests including missing ComfyUI and malformed workflow | Yes |
| Preservation and safe update | NOT VERIFIED | Clean upgrade from preceding RC, diff and data retention | Yes |
| Changelog, README, limitations | PARTIAL | Updated results and known limitations before tag | Yes |

Some user-reported hands-on runs are documented in project conversations; the evidence matrix [GPU_GENERATION_ACCEPTANCE.md](GPU_GENERATION_ACCEPTANCE.md) still shows `NOT TESTED` for the individual scenarios. Record observed outcomes there before setting this gate to PASS.

**CI observation:** GitHub's combined commit status for the examined main commit returned no statuses; commit-associated PR workflow-run query also returned no runs. These results **do not establish that CI is absent or failed**. Check GitHub Actions on the precise candidate SHA and attach run links.

## Suggested safe operator command sequence

Run in the local Windows installation with ComfyUI Desktop; stop on errors rather than resetting uncommitted work:

```powershell
git status --short
git branch --show-current
git switch main
git pull --ff-only origin main
git rev-parse HEAD
python -m unittest discover -s tests -v
python tools/smoke_test_ui.py --only sdxl,wan22,yue2
nvidia-smi
```

The browser smoke test needs a supported Chrome/Edge/Chromium and uses an isolated temporary worktree, so inspect its tool documentation if dependencies or git state are unusual. The selected three trainers are **representative**, not proof that every engine is verified.

Then follow the step-by-step [GPU/Generation acceptance matrix](GPU_GENERATION_ACCEPTANCE.md), including Bridge installation and restart, safe cancellation of only OrkiLab-owned jobs, valid/invalid sampler input, media results, RAM/VRAM and GPU sensor sampling. Keep custom workflow files, tokens and private paths out of public attachments.

## Blockers and safe scope decisions

- **Mandatory:** no critical data loss; no unwanted queue manipulation; no execution on import; canceled runs do not terminate unrelated jobs; offline/disconnected state remains usable; supported workflows complete with accurate status; tests pass.
- **Permissible with clear release notes:** unsupported third-party nodes, exact overall percentage unavailable, multi-GPU not physically tested where only one adapter exists, downloadable mesh without interactive 3D, incomplete legacy trainer translations and incomplete full trainer UI migration.
- Do not widen the feature freeze or claim every custom workflow is compatible.

## Release procedure — only after PASS evidence

1. Ensure no unresolved critical blocker; review `git status` on the candidate and confirm passing Windows/Linux CI, browser and on-device tests.
2. Update `VERSION_ARKILAB`, `GUI/launcher.json`, the README version badge and any other canonical version references **in one release PR**, avoiding inconsistent version strings.
3. Update `CHANGELOG_ARKILAB.md`, README's development/test caveats and `GPU_GENERATION_ACCEPTANCE.md` to reflect actual evidence; document limitations explicitly.
4. Merge reviewed release PR into `main`, confirm checks on exact release commit, and create Git tag `v0.3.0-rc.1` **pointing to that commit**.
5. Publish a GitHub prerelease with installation/update and rollback instructions, supported workflow examples, known issues and links to the evidence.
6. Retain prior candidate as rollback option; do not force-reset or overwrite datasets, workflows, settings or outputs.

**Next decision:** run and log the technical acceptance tests. This document alone does not unblock publishing.
