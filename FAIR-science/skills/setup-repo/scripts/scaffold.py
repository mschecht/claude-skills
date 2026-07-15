#!/usr/bin/env python3
"""
Scaffold a new data-analysis repository with the setup-repo directory
structure. Safe to re-run: it only creates what's missing, never overwrites
existing files.

Usage:
    python3 scaffold.py <path-to-new-project> --name "Project Name"
"""

import argparse
import os
import re
import sys

DIRS = [
    "data/raw",
    "data/processed",
    "data/figure",
    "data/final",
    "code/process",
    "code/figures",
    "scripts",
    "figures",
    "notebooks",
    "envs",
]


def _slugify(name):
    """Turn a project name into a conda-env-safe identifier."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return slug or "project-env"

README_TEMPLATE = """# {name}

This repo follows a fixed structure so data lineage is always traceable from a file path alone.

## Layout

- `data/raw/` — source data, never modified after it lands here.
- `data/processed/` — output of `code/process/` scripts (cleaned, merged, reshaped).
- `data/figure/` — output of `code/figures/` scripts (data reshaped for one specific plot).
- `data/final/` — final output datasets/results (deliverables, not intermediate steps).
- `code/process/` — scripts that turn raw data into processed data.
- `code/figures/` — scripts that turn processed data into figure data and render a PNG.
- `scripts/` — general utilities that support the analysis but aren't part of a figure's
  pipeline (env setup, data download, one-off cleaning, shared helpers).
- `figures/` — rendered images, one per figure, referenced from `notebooks/analysis.md`.
- `notebooks/analysis.md` — the source of truth: narrative notes with embedded figures.
  Append-only — new entries get added as the analysis grows, old ones stay.
- `Snakefile` — orchestrates the pipeline. Each figure gets a `process_N` / `figure_N` rule
  pair so the whole analysis (or just one figure) can be regenerated with one command.
- `CLAUDE.md` — the same conventions, written for an agent working in this repo.
- `environment.yml` — the conda environment you activate to run anything in this repo
  (includes `snakemake` itself).
- `envs/` — per-rule conda environments for rules with their own dependencies (e.g. an R rule
  next to a Python rule), referenced via each rule's `conda:` directive.

## Per-figure pipeline convention

For figure N:

```
data/raw/<source files>
  -> code/process/processN_<description>.py
    -> data/processed/N_<description>.<ext>
      -> code/figures/figureN_<description>.py
        -> data/figure/N_<description>.<ext>
          -> figures/figureN.png
```

Each step is also wired into the `Snakefile` as a `process_N` / `figure_N` rule pair, so
`snakemake --use-conda --cores 1 figures/figureN.png` reruns exactly that lineage, and
`snakemake --use-conda --cores 1 all` regenerates everything from raw data.

## Conda environments

Activate `environment.yml` first — it has `snakemake` itself plus anything common to the whole
project:

```bash
conda env create -f environment.yml
conda activate {slug}
```

Most rules can just run in that environment. If a specific rule needs something that would
bloat the shared environment (a different language, a package that conflicts with something
else in the repo), give it its own file in `envs/` and point the rule at it with a `conda:`
directive — Snakemake creates and uses that environment automatically when you run with
`--use-conda`. The "conda-manager" skill is the fastest way to build or audit any of these
`environment.yml` files against what the code actually imports.

## Protecting data/raw

Files in `data/raw/` are set read-only (`chmod 444`) — run `scripts/lock_raw_data.sh` any time
you add new raw files to re-lock them. This blocks accidental in-place edits (overwriting a raw
file, appending to it by mistake), but **it does not prevent deletion** — `rm` and most delete
calls check write permission on the containing *directory*, not the file's own permission bits,
so a read-only file in a writable directory can still be deleted outright. The real protection
against deletion is git: commit `data/raw/` so any deletion is trivially recoverable with `git
checkout`. `lock_raw_data.sh` checks this and warns if files aren't tracked yet.

## Notebook entry format

Each figure gets a block like this appended to `notebooks/analysis.md`:

```markdown
## Figure N: <Title>

![Figure N](../figures/figureN.png)

**What this shows:** <what's plotted and why>

**Notes:**
- <observation>
- <question raised / next step>
```
"""

CLAUDE_MD_TEMPLATE = """# CLAUDE.md — {name}

Conventions for working in this repo. Read this before adding or changing anything.

## Layout

- `data/raw/` — never modify after it lands here. Files are chmod 444 (read-only); that
  blocks in-place edits but NOT deletion, so this only matters if `data/raw/` is also
  git-tracked (the actual recoverability safeguard). Run `scripts/lock_raw_data.sh` after
  adding new raw files.
- `data/processed/` — output of `code/process/*.py`.
- `data/figure/` — output of `code/figures/*.py`, shaped for one specific plot.
- `data/final/` — final deliverable datasets/results, not intermediate steps.
- `code/process/` — raw data -> processed data.
- `code/figures/` — processed data -> figure data -> rendered PNG.
- `scripts/` — utilities that support the analysis but aren't part of a figure's lineage.
- `figures/` — rendered PNGs, one per figure.
- `notebooks/analysis.md` — the source of truth. Append-only.
- `Snakefile` — orchestrates the pipeline rules described below.
- `environment.yml` — the conda env to activate before running anything (`conda activate
  {slug}`). Has `snakemake` itself plus shared dependencies.
- `envs/` — per-rule conda environments for rules that need something the shared environment
  doesn't have, wired in via that rule's `conda:` directive.

## Where does this go? (quick reference)

Check this before creating any file. If what you're doing doesn't map cleanly onto one of
these rows, stop and ask rather than guessing — that's usually a sign it doesn't fit the N-th
figure's lineage and needs a different N, or genuinely belongs in `scripts/`.

| You're creating...                                              | Goes in                                  |
|-------------------------------------------------------------------|-------------------------------------------|
| A raw data file, exactly as received (never edited after this)    | `data/raw/`                              |
| A script that cleans/merges/reshapes raw data into general form   | `code/process/processN_<description>.py` |
| The output of that cleaning script                                | `data/processed/N_<description>.<ext>`   |
| A script that reshapes processed data for one specific plot       | `code/figures/figureN_<description>.py`  |
| The output of that figure-shaping script                          | `data/figure/N_<description>.<ext>`      |
| The rendered plot itself                                          | `figures/figureN.png`                    |
| A finished deliverable dataset/result (not an intermediate step)  | `data/final/`                            |
| A helper that isn't tied to one figure's lineage (env setup, download, shared utility function) | `scripts/` |
| A new `process_N` / `figure_N` rule pair for the pipeline you just wrote | `Snakefile`                        |
| Notes, title, and description for a figure that now exists        | append to `notebooks/analysis.md`        |
| A package needed by most/all rules (shared dependency)             | add to root `environment.yml`           |
| A package only one rule needs (different language, conflicting version) | new file in `envs/`, referenced via that rule's `conda:` directive |

The `N` in each path should be the same figure number end to end — `data/processed/3_*`,
`code/figures/figure3_*.py`, `data/figure/3_*`, and `figures/figure3.png` should all trace back
to the same figure, so anyone can follow the chain from either end.

## Adding a new figure (figure N)

1. Find the next unused N by checking `figures/` and `notebooks/analysis.md`.
2. Write `code/process/processN_<description>.py`: reads `data/raw/`, writes
   `data/processed/N_<description>.<ext>`. Keep it general-purpose cleaning, not specific to
   how the figure will look — that's what makes `data/processed` reusable across figures.
3. Write `code/figures/figureN_<description>.py`: reads the processed data, writes
   `data/figure/N_<description>.<ext>`, and renders `figures/figureN.png`.
4. Add a `process_N` / `figure_N` rule pair to the `Snakefile` (see the commented example
   already in it) and add `figures/figureN.png` to `rule all`'s inputs. If either script needs
   a package not already in `environment.yml`, either add it there (if other rules would
   reasonably want it too) or give the rule its own file in `envs/` and a `conda:` directive
   pointing at it — don't just `pip install` into whatever environment happens to be active.
5. Run `snakemake --use-conda --cores 1 figures/figureN.png` and confirm the PNG renders.
6. Append an entry to `notebooks/analysis.md` — never edit or reorder existing entries:

   ```markdown
   ## Figure N: <Title>

   ![Figure N](../figures/figureN.png)

   **What this shows:** <what's plotted and why>

   **Notes:**
   - <observation>
   ```

   Draft the title and "what this shows" from the code and data. Ask the user for the actual
   notes rather than inventing scientific commentary — that's their reasoning, not a caption.

## Rules

- Never modify, overwrite, or delete files in `data/raw/` — including when asked to "clean up"
  or "reorganize" the repo. These files are set read-only (`chmod 444`) as a guard against
  accidental in-place edits, but that does NOT stop deletion (permission bits on a file don't
  block `rm`/`os.remove` — only the containing directory's permissions do). Treat the read-only
  bit as a signal, not the actual safeguard: if you find yourself needing write access to
  `data/raw/`, stop and ask, don't chmod around it. The actual safeguard is git — `data/raw/`
  should be committed, so a deletion is recoverable even though it isn't blocked outright.
- After adding new files to `data/raw/`, run `scripts/lock_raw_data.sh` to lock them down and
  check they're git-tracked.
- Never delete or reorder entries in `notebooks/analysis.md`.
- Match whatever language/libraries are already used in `code/process/` and `code/figures/` —
  don't introduce a new stack partway through a repo without asking.
- Regenerate everything from raw data with `snakemake --use-conda --cores 1 all` to
  sanity-check the pipeline still reproduces before treating a figure as done.
- Never `pip install` or `conda install` directly into whatever environment happens to be
  active. Add the package to `environment.yml` (shared) or a file in `envs/` (rule-specific)
  so the dependency is recorded and reproducible, not just installed in one session. The
  "conda-manager" skill can build or audit these files against what the code actually imports.
"""

SNAKEFILE_TEMPLATE = """# Snakefile — orchestrates the raw -> processed -> figure -> png pipeline.
#
# Add a process_N / figure_N rule pair for each new figure (copy the commented example
# below), then add its PNG to rule all's inputs.
#
# Run everything:      snakemake --use-conda --cores 1 all
# Run one figure:       snakemake --use-conda --cores 1 figures/figureN.png
#
# --use-conda tells Snakemake to build/activate each rule's `conda:` environment automatically.
# Rules with no `conda:` directive just run in whatever environment invoked snakemake (i.e.
# the one from the repo's root environment.yml) — that's the common case; only add a per-rule
# conda: directive when a rule genuinely needs something the shared environment doesn't have.

rule all:
    input:
        [],  # e.g. "figures/figure1.png", "figures/figure2.png", ...


# --- Example rule pair for Figure 1 — copy this pattern for each new figure ---
#
# rule process_1:
#     input:
#         "data/raw/example.csv"
#     output:
#         "data/processed/1_example.csv"
#     shell:
#         "python3 code/process/process1_example.py {input} {output}"
#
# rule figure_1:
#     input:
#         "data/processed/1_example.csv"
#     output:
#         figure_data="data/figure/1_example.csv",
#         png="figures/figure1.png"
#     shell:
#         "python3 code/figures/figure1_example.py {input} {output.figure_data} {output.png}"
#
# --- Same example, but figure_1 needs its own environment (e.g. an R plotting stack) ---
#
# rule figure_1:
#     input:
#         "data/processed/1_example.csv"
#     output:
#         figure_data="data/figure/1_example.csv",
#         png="figures/figure1.png"
#     conda:
#         "envs/figure1.yml"
#     shell:
#         "Rscript code/figures/figure1_example.R {input} {output.figure_data} {output.png}"
"""

ENVIRONMENT_YML_TEMPLATE = """name: {slug}
channels:
  - conda-forge
  - bioconda
  - defaults
dependencies:
  - python>=3.10
  - snakemake>=7.0
  # add shared dependencies here (packages most/all rules need).
  # for a package only one rule needs, prefer a dedicated file in envs/ instead —
  # see the Snakefile and CLAUDE.md for the convention.
  # - pip:
  #   - <pip-only-package>==<version>
"""

LOCK_RAW_DATA_SCRIPT = """#!/usr/bin/env bash
# Lock down data/raw/ so files can't be silently edited in place, and check that git is
# actually tracking them.
#
# Important: read-only permissions (chmod 444) block in-place edits, but do NOT block deletion —
# `rm` and most delete calls check write permission on the *containing directory*, not the
# file's own permission bits, so a read-only file in a writable directory can still be deleted
# without any prompt in a non-interactive context. The real protection against deletion is git:
# commit data/raw/ so any deletion is trivially recoverable with `git checkout`.
#
# Run this any time new files are added to data/raw/ — it's safe to re-run.
#
# Usage:
#   scripts/lock_raw_data.sh [path-to-data-raw]   # defaults to data/raw

set -uo pipefail

RAW_DIR="${1:-data/raw}"

if [ ! -d "$RAW_DIR" ]; then
  echo "No such directory: $RAW_DIR" >&2
  exit 2
fi

count=0
while IFS= read -r -d '' f; do
  chmod 444 "$f"
  count=$((count + 1))
done < <(find "$RAW_DIR" -type f ! -name ".gitkeep" -print0)

echo "Locked $count file(s) in $RAW_DIR to read-only (chmod 444)."

if git -C "$RAW_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  untracked=$(git -C "$RAW_DIR" ls-files --others --exclude-standard -- . 2>/dev/null)
  if [ -n "$untracked" ]; then
    echo
    echo "WARNING: these files in $RAW_DIR aren't tracked by git yet. chmod alone does NOT"
    echo "protect against deletion (only against in-place edits) — commit them so a deletion"
    echo "is actually recoverable:"
    echo "$untracked"
  else
    echo "All files in $RAW_DIR are tracked by git — deletions are recoverable via git checkout."
  fi
else
  echo
  echo "WARNING: $RAW_DIR doesn't appear to be inside a git repo. Read-only permissions do NOT"
  echo "prevent deletion — without git tracking, a deleted raw file is gone for good. Initialize"
  echo "git and commit data/raw/ for real protection."
fi
"""

ANALYSIS_MD_TEMPLATE = """# {name} — Analysis Notebook

This is the source of truth for this analysis. Every figure gets an entry below: the rendered
image, a title, what it shows, and running notes. Append new entries as the analysis grows —
never delete old ones, since this file is the narrative record of how the analysis evolved.

---

<!-- Example entry — copy this block for each new figure, then delete this comment
     once the first real entry is added.

## Figure 1: <Title>

![Figure 1](../figures/figure1.png)

**What this shows:** <one or two sentences on what's plotted and why>

**Notes:**
- <observation>
- <next step / question raised>

-->
"""


def _report(project_name, project_path, created, skipped):
    print(f"Project: {project_name}")
    print(f"Location: {project_path}\n")
    if created:
        print("Created:")
        for c in sorted(created):
            print(f"  {c}")
    if skipped:
        print("\nSkipped (already existed):")
        for s in sorted(skipped):
            print(f"  {s}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Path to the new project directory (created if missing)")
    parser.add_argument("--name", default=None, help="Project name (defaults to the folder name)")
    args = parser.parse_args()

    project_path = os.path.abspath(args.path)
    project_name = args.name or os.path.basename(project_path.rstrip("/"))
    slug = _slugify(project_name)

    created = []
    skipped = []

    # Everything below only ever creates new files/dirs, never deletes or overwrites — some
    # mounted/synced filesystems (e.g. a folder connected to a cloud-desktop session) reject
    # deletes and renames even when the account otherwise has write access. If a step still
    # fails (permissions, disk full, etc.), report what succeeded before re-raising, rather
    # than leaving the user with just a bare traceback and no idea what state the repo is in.
    try:
        for d in DIRS:
            full = os.path.join(project_path, d)
            if not os.path.isdir(full):
                os.makedirs(full, exist_ok=True)
                created.append(d + "/")
            # add a .gitkeep so empty dirs survive a git commit — except notebooks/ and
            # scripts/, which are about to get analysis.md / lock_raw_data.sh written into
            # them below, so they're never actually empty.
            if d in ("notebooks", "scripts"):
                continue
            gitkeep = os.path.join(full, ".gitkeep")
            if not os.listdir(full):
                open(gitkeep, "a").close()

        readme_path = os.path.join(project_path, "README.md")
        if not os.path.exists(readme_path):
            with open(readme_path, "w") as f:
                f.write(README_TEMPLATE.format(name=project_name, slug=slug))
            created.append("README.md")
        else:
            skipped.append("README.md (already exists)")

        claude_md_path = os.path.join(project_path, "CLAUDE.md")
        if not os.path.exists(claude_md_path):
            with open(claude_md_path, "w") as f:
                f.write(CLAUDE_MD_TEMPLATE.format(name=project_name, slug=slug))
            created.append("CLAUDE.md")
        else:
            skipped.append("CLAUDE.md (already exists)")

        snakefile_path = os.path.join(project_path, "Snakefile")
        if not os.path.exists(snakefile_path):
            with open(snakefile_path, "w") as f:
                f.write(SNAKEFILE_TEMPLATE)
            created.append("Snakefile")
        else:
            skipped.append("Snakefile (already exists)")

        environment_yml_path = os.path.join(project_path, "environment.yml")
        if not os.path.exists(environment_yml_path):
            with open(environment_yml_path, "w") as f:
                f.write(ENVIRONMENT_YML_TEMPLATE.format(slug=slug))
            created.append("environment.yml")
        else:
            skipped.append("environment.yml (already exists)")

        analysis_path = os.path.join(project_path, "notebooks", "analysis.md")
        if not os.path.exists(analysis_path):
            with open(analysis_path, "w") as f:
                f.write(ANALYSIS_MD_TEMPLATE.format(name=project_name))
            created.append("notebooks/analysis.md")
        else:
            skipped.append("notebooks/analysis.md (already exists)")

        lock_script_path = os.path.join(project_path, "scripts", "lock_raw_data.sh")
        if not os.path.exists(lock_script_path):
            with open(lock_script_path, "w") as f:
                f.write(LOCK_RAW_DATA_SCRIPT)
            os.chmod(lock_script_path, 0o755)
            created.append("scripts/lock_raw_data.sh")
        else:
            skipped.append("scripts/lock_raw_data.sh (already exists)")

        # Lock down whatever's already sitting in data/raw/ (e.g. re-running scaffold against
        # a repo that already has raw files). Read-only permissions block in-place edits; they
        # do NOT block deletion (that's governed by the containing directory's permissions, not
        # the file's own) — data/raw/ still needs to be git-tracked for real delete protection.
        raw_dir = os.path.join(project_path, "data", "raw")
        locked = 0
        if os.path.isdir(raw_dir):
            for fn in os.listdir(raw_dir):
                if fn == ".gitkeep":
                    continue
                full = os.path.join(raw_dir, fn)
                if os.path.isfile(full):
                    os.chmod(full, 0o444)
                    locked += 1
        if locked:
            created.append(f"(locked {locked} existing file(s) in data/raw/ to read-only)")
    except OSError as e:
        _report(project_name, project_path, created, skipped)
        print(f"\nStopped after a filesystem error: {e}")
        print("Everything listed under 'Created' above did succeed — check what's still")
        print("missing against the structure in SKILL.md and retry (the script is safe to")
        print("re-run; it only fills in what's missing).")
        return 1

    _report(project_name, project_path, created, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
