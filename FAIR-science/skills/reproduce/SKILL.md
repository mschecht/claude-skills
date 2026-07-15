---
name: reproduce
description: Verifies that a data-analysis repo built with setup-repo (Snakefile, data/raw to data/processed to data/figure to figures/*.png) actually reproduces — either a quick spot-check of one figure's chain, or a full from-scratch regeneration of every figure. Use whenever the user asks "does this still reproduce," "check the pipeline works," "rerun everything from scratch," "verify figure N regenerates," "sanity check before I share this," "does the analysis still run end to end," or wants confidence the repo isn't secretly broken or out of date. Also trigger before publishing, sharing, or handing off a repo, and periodically while actively building one out. Not for writing new pipeline code or figures, and not for checking conda environment completeness (use "env-audit" for that) — this skill assumes the pipeline code already exists and checks whether it actually runs.
---

# Reproduce

One skill, two depths — pick based on what the user actually needs, since the full check is
slow and the quick check is fast. Don't default to full just because it's more thorough; ask if
it's not obvious which one they want, especially since full mode overwrites existing derived
files.

## Quick mode: does the DAG resolve, and does one figure actually rebuild?

This is the right default when someone just added a figure, is mid-analysis, or wants fast
confidence without burning minutes/hours re-running everything.

1. **Dry-run the whole DAG** to catch structural problems without executing anything:

   ```bash
   snakemake --use-conda -n all
   ```

   This surfaces missing rules, unresolved wildcards, and cycles even before you run a single
   command. If this fails, stop here and report the DAG error — there's no point spot-checking
   one figure if the pipeline definition itself is broken.

2. **Force-rerun one target** to prove the mechanism genuinely works, not just that Snakemake
   thinks the files are up to date:

   ```bash
   snakemake --use-conda --cores 1 --forcerun figures/figureN.png
   ```

   `--forcerun` forces just that target to rebuild while everything else stays untouched if
   it's already up to date — verified this rebuilds only the targeted figure and leaves
   sibling figures' timestamps unchanged. Pick N as the most recently added figure unless the
   user specifies one. Confirm the command actually succeeds and the PNG's modification time
   changed.

3. **Cross-check documentation matches reality**: does `notebooks/analysis.md` have a `## Figure
   N` entry for this figure, and does the `Snakefile` have both `process_N` and `figure_N` rules
   for it? A figure that renders but isn't documented, or is documented but the rule is missing,
   is a real finding worth reporting even though the "does it render" check passed.

## Full mode: does the entire analysis regenerate from raw data?

This is the real answer to "is this repo reproducible" — the quick mode above only ever proves
one figure works. Full mode proves all of them do, together, from nothing but `data/raw/`.

**Confirm with the user before running this.** `--forceall` overwrites every file in
`data/processed/`, `data/figure/`, and `figures/` and regenerates them from scratch — if someone
manually tweaked an output without updating the pipeline that produced it, this will silently
discard that tweak. That's the point of the check (a repo where manual tweaks survive but aren't
in the pipeline isn't actually reproducible), but the user should know it's about to happen.

```bash
snakemake --use-conda --cores <N> --forceall all
```

Use a reasonable core count for the machine rather than always `1` — full regeneration can be
slow, and this is the one mode where parallelism actually helps. After it finishes:

1. Confirm every figure referenced in `rule all`'s inputs and every `## Figure N` entry in
   `notebooks/analysis.md` actually exists in `figures/` with a fresh timestamp.
2. If the repo is under git, diff the regenerated files against what was committed
   (`git diff --stat data/ figures/`). Report differences neutrally, not as failures — a diff can
   mean the pipeline is now producing different (possibly better, possibly buggy) results,
   which is exactly the kind of drift this check exists to surface. Let the user judge whether
   it's expected.
3. Report any rule that failed outright, with the actual error, not just "something failed."

## Reporting results

Always end with a clear verdict — reproduces cleanly, reproduces with documentation gaps, or
doesn't reproduce (and why) — plus the single most useful next action. Don't just paste raw
Snakemake output; a wall of DAG scheduling logs is not a summary. If `environment.yml` or a file
in `envs/` looks like the actual problem (package resolution failure, missing tool) rather than
a bug in the pipeline logic itself, say so and point at "env-audit" rather than trying to
diagnose conda issues here.
