---
name: env-audit
description: Verifies that a data-analysis repo's conda environments (a root environment.yml plus any per-rule files in envs/, following the setup-repo/Snakefile convention) are complete and can actually be rebuilt from scratch by someone else — not just that they look plausible on paper. Use whenever the user asks "is my environment reproducible," "can someone else rebuild this env," "audit environment.yml," "check my envs folder," "does this actually install cleanly," or wants to verify a conda environment before sharing/publishing a repo. Also trigger after several new dependencies have been added ad hoc, or before a "reproduce" run, to catch drift early. For general conda troubleshooting not tied to one specific repo's environment.yml (broken imports, pip/conda conflicts, HPC reproduction), defer to the "conda-manager" skill instead — this skill is specifically the "does a fresh build of this repo's declared environment(s) actually work" check.
---

# Env Audit

Answers one question with certainty, not a guess: if a stranger cloned this repo today with
nothing installed, would `conda env create -f environment.yml` actually give them everything
the code needs? A `environment.yml` that "looks complete" because nobody's hit a missing-import
error yet is not the same as one that's actually been rebuilt from zero.

This skill does two things: an **audit** (does the declared environment match what the code
actually uses) and a **fresh-build verification** (does building it from scratch actually
succeed). Do both — a repo can pass one and fail the other, and each catches different bugs.

## Step 1: Find what needs auditing

Look for a root `environment.yml` and any files under `envs/`. For each file in `envs/`, find
which Snakefile rule(s) reference it via a `conda:` directive — that tells you which specific
scripts that environment needs to satisfy (as opposed to `environment.yml`, which needs to
satisfy everything *not* covered by a per-rule environment).

## Step 2: Audit declared vs. actual dependencies

This is the same technique the "conda-manager" skill uses — don't reinvent it, apply it here:

```bash
# Python imports across the codebase (or the subset of scripts one envs/*.yml covers)
grep -rh "^import \|^from " --include="*.py" . \
  | sed 's/import \([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/; s/from \([a-zA-Z_][a-zA-Z0-9_]*\).*/\1/' \
  | sort -u

# CLI tools invoked from Snakefile shell blocks — these won't show up as Python imports
grep -rh "shell:" --include="Snakefile" --include="*.smk" . -A2 | grep -v "shell:" | grep -v "^--$"
```

Cross-reference against the environment file's `dependencies:` list. Report three buckets:
missing (imported/invoked but not declared), unused (declared but never referenced — flag
gently, since CLI tools and transitive deps won't show up as imports and aren't necessarily
dead weight), and unpinned (present but no version, where the rest of the file pins versions).

## Step 3: Verify it actually builds from scratch

The audit in step 2 only catches *known* problems — packages someone forgot to add. It won't
catch a channel typo, a version that no longer resolves, or a package that was only ever
installed manually into someone's existing environment and never made it into the file. Only
an actual fresh build catches those.

Run the bundled script, which builds the environment under a disposable, randomly-suffixed name
so it never touches the user's active or base environment, and always tears the temp environment
down afterward whether the build succeeded or failed:

```bash
scripts/verify_fresh_env.sh environment.yml "snakemake --version"
```

Do this for the root `environment.yml` and, if the user wants full coverage, for each file in
`envs/` too (pass a smoke-test command relevant to that rule, e.g. `Rscript -e 'library(ggplot2)'`
for an R environment — ask the user what a reasonable smoke test is if it's not obvious from the
rule's `shell:` command). This step downloads and installs real packages, so it takes real time
and disk — tell the user roughly what's about to happen before running it on more than one file,
and let them decide if they want to check every `envs/*.yml` or just `environment.yml`.

If a build fails, the script prints the tail of conda's actual error output — read it and explain
in plain terms what's wrong (unresolvable package, channel missing, version conflict) rather than
just reporting "it failed." Fixing the file itself is "conda-manager" territory: hand off to that
skill for rebuilding the dependency list once you know what's broken.

## Reporting results

Summarize clearly: what was audited, what's missing/unused/unpinned, whether the fresh build(s)
passed or failed, and — if something failed — the one concrete next step (usually: add the
missing package to the right file, or run "conda-manager" to rebuild it properly). Don't just
dump raw script output; translate it into what the user should actually do next.

## Step 4: Offer to fix missing dependencies

If Step 2 found missing packages, don't stop at reporting them — ask the user whether they want
you to add them to the environment file now. Give them the actual choice, not just a fait
accompli:

- **Install now** — add the missing entries to the right `dependencies:` list (root
  `environment.yml` or the specific `envs/*.yml`) and, if the user also wants it verified, rerun
  `scripts/verify_fresh_env.sh` against the updated file to confirm it actually builds.
- **Just show me the command** — print the exact lines/command to add (e.g. the `dependencies:`
  entries to paste in, or the equivalent `conda install -n <env> -c bioconda -c conda-forge
  <pkgs>`) and let the user run it themselves.

Never edit the file or run an install without the user picking one of these first — this is the
one step in the skill that changes repo state or installs packages, so treat it like any other
action with a real (if small) blast radius.
