# claude-skills

Source for custom Claude skills that support reproducible, FAIR-ish data-analysis repos (the
`setup-repo` layout: `data/raw|processed|figure|final`, `code/process|figures`, `Snakefile`,
`environment.yml` + `envs/`, `notebooks/analysis.md`, `CLAUDE.md`). Each skill lives in its own
folder with a `SKILL.md` and, where useful, a bundled `scripts/` — that's the whole convention;
see `agentskills.io` for the underlying open spec if you want the full format reference.

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

`conda-manager` (an existing Anthropic-provided skill, not built here) is the actual conda
expert underneath these — it builds/audits `environment.yml` files properly. `setup-repo` only
generates a bare-bones starter (`python` + `snakemake` pinned) and defers real dependency
management to `conda-manager`. `env-audit` reuses `conda-manager`'s audit technique but adds a
real from-scratch build test, then hands fixes back to `conda-manager`. `reproduce` defers to
`env-audit` (not `conda-manager` directly) when a pipeline failure looks like an environment
problem rather than a code bug. `fair-audit` doesn't touch conda at all — it's orthogonal
(metadata/licensing/formats).

There used to be a fifth skill, **brief** (vibe-coding new figures + compiling the notebook into
a written report). It was removed from the account by request. `setup-repo`'s generated
`CLAUDE.md` now carries that guidance directly (the per-figure lineage convention, the "where
does this go?" quick reference, and the notebook entry format), so there's no gap — don't
recreate `brief` without a reason; the functionality is already covered.

## Dev workflow

1. Edit a skill's `SKILL.md` (and any bundled `scripts/`) in this repo.
2. Validate before packaging:
   ```bash
   python3 -c "
   import sys; sys.path.insert(0, '<path-to-skill-creator-skill>')
   from scripts.quick_validate import validate_skill
   print(validate_skill('<skill-folder>'))
   "
   ```
   (Path to the skill-creator skill varies by session — ask Claude to find it if starting fresh.)
3. Test any bundled scripts directly against a real or scratch-built repo before trusting them —
   don't assume a script is correct just because it parses. Several bugs in this repo's history
   (a delete call that failed on Cowork-connected folders, an `os.remove` retained after it
   became unnecessary, redundant `.gitkeep` files, a stale skill reference left in a
   `description` field after a body edit) were only caught by actually running things end to end,
   not by reading the code.
4. Package with skill-creator's `scripts/package_skill.py <skill-folder> <output-dir>` — this
   also re-validates and will refuse to package an invalid skill (e.g. description over 1024
   chars, or containing `<`/`>`).
5. Install/update via the "Save skill" button on the presented `.skill` file — this always
   overwrites the previously installed version of a skill with the same name.
6. Commit the change here once it's packaged and working.

## Known limitations worth remembering

- `env-audit`'s fresh-build script needs `conda` on PATH — it fails loudly (not silently) if
  conda isn't installed, which is correct, but means it can't be exercised in a sandbox without
  conda.
- `data/raw/` read-only permissions (set by `setup-repo`'s `lock_raw_data.sh`) block in-place
  edits but do **not** block deletion — deletion is governed by the containing directory's
  permissions, not the file's own. Git tracking is the actual safeguard; the chmod is a signal,
  not a lock.
