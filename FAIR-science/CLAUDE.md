# FAIR-science (plugin dev notes)

This is a Claude Code plugin (`.claude-plugin/plugin.json`) bundling four skills that support
reproducible, FAIR data-analysis repos for computational biology — specifically the `setup-repo`
layout: `data/raw|processed|figure|final`, `code/process|figures`, `Snakefile`,
`environment.yml` + `envs/`, `notebooks/analysis.md`, `CLAUDE.md`. Skills live under `skills/`,
one folder per skill, each with a `SKILL.md` and, where useful, a bundled `scripts/`.

This repo (`claude-skills`, the parent of this plugin folder) is a **marketplace**: its root
`marketplace.json` lists this plugin by path. Unrelated future plugins get their own sibling
folder at the repo root with their own `.claude-plugin/plugin.json`, added as a new entry in the
same `marketplace.json` — they don't belong inside `FAIR-science/`.

## The skills

**setup-repo** — Scaffolds a new data-analysis repo: the data layout, `Snakefile`, conda
`environment.yml` + `envs/`, `CLAUDE.md`, and `scripts/lock_raw_data.sh`. Re-running it against
an existing repo only fills in what's missing; it never overwrites. 859-char description.

**env-audit** — Verifies that `environment.yml` + any files in `envs/` are complete (import/
shell-usage audit, reusing conda-manager's technique) and actually buildable from scratch, via a
bundled script that builds each one in a disposable temp-named conda env and tears it down.
Defers actual fixes to the "conda-manager" skill. 949-char description.

**reproduce** — One skill, two depths. Quick mode dry-runs the Snakemake DAG and force-reruns
one target figure to prove the mechanism works. Full mode force-regenerates everything from raw
data (`--forceall`) — confirm with the user first, since it overwrites existing derived files.
875-char description.

**fair-audit** — Audits the repo against the actual FAIR principles (Wilkinson et al. 2016) —
Findable, Accessible, Interoperable, Reusable — not just "does it reproduce." Checks for a
license file, git remote, open vs. proprietary data formats, and whether every figure's
provenance chain (Snakefile rules + notebook entry) is intact. Bundled script writes
`FAIR_AUDIT.md` into the audited repo. 815-char description.

## How they hand off to each other

`conda-manager` (an existing Anthropic-provided skill, not built here — not bundled in this
plugin, so anyone installing FAIR-science needs it separately if they want the handoffs below to
resolve) is the actual conda expert underneath these — it builds/audits `environment.yml` files
properly. `setup-repo` only generates a bare-bones starter (`python` + `snakemake` pinned) and
defers real dependency management to `conda-manager`. `env-audit` reuses `conda-manager`'s audit
technique but adds a real from-scratch build test, then hands fixes back to `conda-manager`.
`reproduce` defers to `env-audit` (not `conda-manager` directly) when a pipeline failure looks
like an environment problem rather than a code bug. `fair-audit` doesn't touch conda at all —
it's orthogonal (metadata/licensing/formats).

There used to be a fifth skill, **brief** (vibe-coding new figures + compiling the notebook into
a written report). It was removed by request. `setup-repo`'s generated `CLAUDE.md` now carries
that guidance directly (the per-figure lineage convention, the "where does this go?" quick
reference, and the notebook entry format), so there's no gap — don't recreate `brief` without a
reason.

## Dev workflow (plugin form)

1. Edit a skill's `skills/<name>/SKILL.md` (and any bundled `scripts/`).
2. Test locally without installing anything, using Claude Code's dev flag from the repo root:
   ```bash
   claude --plugin-dir ./FAIR-science
   ```
   Then exercise the skill and run `/reload-plugins` after further edits to pick up changes
   without restarting.
3. Validate before publishing:
   ```bash
   claude plugin validate
   ```
   Run this from a context where the plugin/marketplace structure is visible — it's the same
   check the community-marketplace review pipeline runs on submissions, so passing it locally
   catches problems before anyone else sees them.
4. Test any bundled scripts directly against a real or scratch-built repo before trusting them —
   don't assume a script is correct just because it parses or validates. Several bugs in this
   plugin's history (a delete call that failed on Cowork-connected folders, an `os.remove`
   retained after it became unnecessary, redundant `.gitkeep` files, a stale skill reference left
   in a `description` field after a body edit) were only caught by actually running things end to
   end, not by reading the code or passing validation.
5. Commit and push. Anyone with the repo added as a marketplace
   (`/plugin marketplace add <this-repo>`) picks up changes on `/plugin marketplace update`,
   unless `version` in `plugin.json` is pinned — bump it to force a version bump for installed
   users rather than relying on commit-SHA versioning.
6. To reach a wider audience than people who already know this repo exists, submit to the
   community marketplace via `platform.claude.com/plugins/submit` (individual-author path,
   since this isn't a Team/Enterprise org) once it's validated and stable.

## Known limitations worth remembering

- `env-audit`'s fresh-build script needs `conda` on PATH — it fails loudly (not silently) if
  conda isn't installed, which is correct, but means it can't be exercised in a sandbox without
  conda.
- `data/raw/` read-only permissions (set by `setup-repo`'s `lock_raw_data.sh`) block in-place
  edits but do **not** block deletion — deletion is governed by the containing directory's
  permissions, not the file's own. Git tracking is the actual safeguard; the chmod is a signal,
  not a lock.
- This plugin doesn't bundle `conda-manager` — the handoffs described above only resolve if
  whoever installs `FAIR-science` also has `conda-manager` available. Worth deciding later
  whether to bundle a copy, depend on it explicitly in documentation, or accept the gap.
