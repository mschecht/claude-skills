---
name: setup-repo
description: Scaffolds a new data-analysis repository with a standardized folder structure — raw data, processed data, figure-ready data, final data, pipeline code, and a markdown lab notebook that acts as the single source of truth for the analysis. Use this skill whenever the user wants to start a new data analysis, computational/scientific research project, or asks to "set up an analysis repo," "scaffold a new project," "create a data science folder structure," or "give me my usual analysis layout." Also trigger on softer phrasing like "I'm starting a new analysis and want it organized" or "I need raw/processed/figure folders for this" — the user doesn't have to say "setup" or "repo" explicitly. This is the skill that creates the repo; once it exists, the generated CLAUDE.md has the conventions needed to write pipeline code and update the notebook directly.
---

# Setup Repo

Scaffolds a data-analysis repository with a fixed, opinionated structure. The whole point of
this structure is to make the *data lineage* obvious just by looking at file paths: you should
always be able to tell, for any file, whether it's raw, processed, figure-ready, or final, and
which figure or step it belongs to.

## Before creating anything

Ask the user two things if they aren't already clear from context:

1. **Project name** — used as the folder name and as the title in the notebook.
2. **Where to create it** — inside the current working directory, or at some other path the user
   specifies. Don't assume; confirm the target location before writing files, since this creates
   a fair number of files and directories.

## The structure

```
<project-name>/
├── README.md              — explains the conventions below, for future-you
├── CLAUDE.md               — the same conventions, written for an agent working in the repo
├── Snakefile                — orchestrates the pipeline (process_N / figure_N rule pairs)
├── data/
│   ├── raw/                — source data, never modified after it lands here
│   ├── processed/          — output of code/process/ scripts (cleaned, merged, reshaped)
│   ├── figure/              — output of code/figures/ scripts (data reshaped specifically for one plot)
│   └── final/               — final output datasets/results of the analysis (deliverables, not intermediate steps)
├── code/
│   ├── process/             — scripts: raw data -> data/processed/
│   └── figures/             — scripts: data/processed/ -> data/figure/ -> rendered PNG in figures/
├── scripts/                 — general-purpose utilities that aren't part of one figure's pipeline
│                              (env setup, data download, one-off cleaning, shared helper functions)
├── figures/                  — rendered images (PNG etc.), one per figure, referenced by the notebook
├── notebooks/
│   └── analysis.md           — the source of truth: narrative notes + embedded figures, append-only
├── environment.yml           — the conda env to activate before running anything (has snakemake itself)
└── envs/                     — per-rule conda envs for rules that need something the shared env doesn't
```

### Why code/ and scripts/ are separate

`code/` holds the actual pipeline for producing figures — it's meant to be re-run and
reproducible, and every file in it should trace back to a specific processed dataset or figure.
`scripts/` is a junk drawer for things that support the analysis but aren't part of that
lineage (e.g. a script that downloads the raw data in the first place, or a helper module
imported by multiple pipeline scripts). If the user's project doesn't need this distinction,
it's fine to leave `scripts/` empty — don't force things into it just because the folder exists.

### The per-figure pipeline convention

For figure N, the naming should make the chain traceable end to end:

```
data/raw/<source files>
  -> code/process/processN_<short description>.py
    -> data/processed/N_<short description>.<ext>
      -> code/figures/figureN_<short description>.py
        -> data/figure/N_<short description>.<ext>
          -> figures/figureN.png
```

Raw data can be shared across multiple figures' pipelines; processed/figure data and code should
generally be numbered per figure so anyone can trace `figures/figure3.png` back through
`data/figure/3_*`, `code/figures/figure3_*.py`, `data/processed/3_*`, `code/process/process3_*.py`,
to the raw source. Use this convention as a strong default, but adapt the numbering if the
user's project has a different natural unit (e.g. per-dataset instead of per-figure).

Each step is also wired into the `Snakefile` as a `process_N` / `figure_N` rule pair, so the
lineage isn't just a naming convention — it's actually re-runnable. `snakemake --use-conda
--cores 1 all` regenerates everything from raw data; `snakemake --use-conda --cores 1
figures/figureN.png` reruns just one figure's chain. This is what makes the repo trustworthy
months later: anyone (including you) can reproduce every figure from raw data with one command
instead of hunting down the right sequence of scripts and environments to run by hand.

### Conda environments

Two layers, matching the two conda strategies documented in the "conda-manager" skill:

- **`environment.yml`** at the repo root is the environment you activate before doing anything
  in the repo (`conda env create -f environment.yml && conda activate <slug>`). It ships with
  `snakemake` itself and is meant to also hold whatever most/all rules need.
- **`envs/`** holds per-rule environments for the exception cases — a rule that needs a
  different language (R next to Python is common) or a package that would conflict with
  something else in the shared environment. A rule opts into its own environment with a
  `conda:` directive pointing at a file in `envs/`; running with `snakemake --use-conda` makes
  Snakemake build and activate it automatically for just that rule.

Don't default to putting everything in `envs/` — most projects never need a second environment.
Start everything in the shared `environment.yml` and only split out a per-rule env when there's
an actual conflict or a genuinely different toolchain.

### The notebook is the source of truth

`notebooks/analysis.md` is not a dev journal on the side — it's the primary artifact of the
analysis. Every figure gets an entry with the rendered image embedded, a title, a description of
what it shows, and notes, in this exact format:

```markdown
## Figure N: <Title>

![Figure N](../figures/figureN.png)

**What this shows:** <what's plotted and why>

**Notes:**
- <observation>
```

New entries get appended as the analysis grows; existing entries are not deleted, since the
file is the running narrative of how the analysis evolved. This skill only creates the initial
template — when a figure is added later, append its entry here using the format above, draft
the title and "what this shows" from the code and data, and ask the user for the actual notes
rather than inventing scientific commentary.

## How to scaffold

Run the bundled script rather than creating directories by hand — it keeps the structure
consistent and creates `.gitkeep` placeholders so empty directories survive a git commit:

```bash
python3 scripts/scaffold.py <path-to-new-project> --name "<Project Name>"
```

If `<path-to-new-project>` already exists and has content, the script won't overwrite existing
files — it's safe to re-run against a partially-set-up directory, since it only fills in what's
missing (this also means it's safe to run against a repo that predates the conda/Snakefile
conventions — it'll just add whatever's missing without touching existing files). After running
it, briefly tell the user what was created (`README.md`, `CLAUDE.md`, `Snakefile`,
`environment.yml`, and the directory tree). The generated `CLAUDE.md` has everything needed to
start writing pipeline code and adding figures directly — the per-figure lineage convention, the
"where does this go?" quick reference, and the notebook entry format — so there's no separate
skill needed for that next step; just follow `CLAUDE.md`'s conventions when the user is ready to
add the first figure.

The generated `environment.yml` only has `python` and `snakemake` pinned — it's a starting
point, not a finished environment. Once the user knows what packages the analysis actually
needs, point them at the "conda-manager" skill to build it out properly (correct channels,
version pins, auditing against actual imports) rather than hand-editing it yourself.
