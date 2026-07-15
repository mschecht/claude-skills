# FAIR-science

A Claude Code / Cowork plugin for computational biologists building reproducible, FAIR
data-analysis repos. Four skills that scaffold, audit, and verify a repo built around a
Snakemake pipeline: raw data in, figures out, with a conda-managed environment and an
append-only lab notebook as the source of truth.

## Skills

| Skill | What it does |
|---|---|
| `setup-repo` | Scaffolds a new repo: `data/raw\|processed\|figure\|final`, `code/process\|figures`, a `Snakefile`, `environment.yml` + `envs/`, `CLAUDE.md`, `notebooks/analysis.md`, and a read-only lock script for raw data. |
| `env-audit` | Checks that `environment.yml` and any per-rule files in `envs/` actually match what the code uses, and verifies they build from scratch in a disposable conda environment — not just that they look complete. |
| `reproduce` | Verifies the pipeline actually reproduces: a quick spot-check of one figure, or a full from-scratch regeneration of everything from raw data. |
| `fair-audit` | Audits the repo against the real FAIR principles (Findable, Accessible, Interoperable, Reusable — Wilkinson et al. 2016), not just whether it reproduces: license, provenance, data formats, citability. |

## Install

```
/plugin marketplace add mschechter/claude-skills
/plugin install FAIR-science
```

(Replace `mschechter/claude-skills` with wherever this repo ends up hosted.)

## Why

Reproducibility and FAIR compliance are usually treated as an afterthought — something you
scramble to fix before a paper submission or a data deposition deadline. These skills bake the
conventions in from the start of a project (`setup-repo`) and give you fast, honest checks along
the way (`env-audit`, `reproduce`, `fair-audit`) instead of a one-time audit at the end. They also
report what they *can't* verify — access restrictions, vocabulary standards, license choice — as
explicit judgment calls for you, rather than pretending to check everything.

## Related

These skills defer real conda environment management to the **conda-manager** skill rather than
duplicating that logic — install it separately if you don't already have it. See `CLAUDE.md` in
this folder for the full breakdown of how the skills hand off to each other.
