---
name: fair-audit
description: Audits a data-analysis repo against the actual FAIR data principles (Findable, Accessible, Interoperable, Reusable — Wilkinson et al. 2016) rather than just checking that the pipeline runs. Use whenever the user asks to "make this repo FAIR," "check FAIR compliance," "is my data FAIR," "audit for FAIR principles," wants a license/metadata/citation check, or is preparing a repo for publication, sharing, or data deposition. This is distinct from reproducibility — a pipeline can reproduce perfectly and still fail FAIR (no license, no data dictionary, proprietary formats, no way to cite it). For "does the pipeline actually run" checks use "reproduce"; for "is the conda environment complete and buildable" use "env-audit"; this skill is specifically about metadata, licensing, identifiers, and format standards.
---

# FAIR Audit

FAIR is four distinct concerns, and it's easy to accidentally only check one of them
(usually Reusable, since provenance overlaps with reproducibility work people already do).
Go through all four. This skill assumes a repo with the setup-repo layout (`data/raw`,
`data/processed`, `data/figure`, `data/final`, `Snakefile`, `notebooks/analysis.md`), but the
principles apply regardless of layout — adapt the checks if the repo looks different.

## Findable

- **F1 (persistent identifier):** Does the repo have a stable, citable identifier — a GitHub
  remote at minimum, ideally a tagged release or a Zenodo/OSF DOI? A repo that only exists as an
  uncommitted folder on one laptop isn't findable by anyone else. Check `git remote -v` and
  `git tag`.
- **F2 (rich metadata):** Does `README.md` actually describe what the analysis is, where the raw
  data came from, and what each `data/raw/` file contains? A structural README (just the folder
  layout) satisfies Reusable's provenance concerns but not Findable's "can someone figure out
  what this *is* without opening every file" concern.
- **F3 (metadata references the data):** Does documentation for a dataset actually name the
  specific file(s) it describes, rather than describing the project in the abstract? Check
  whether `data/raw/` files are individually referenced somewhere (README, a data dictionary,
  or comments in the process script that reads them) rather than just existing.
- **F4 (indexed/searchable):** Is the repo somewhere indexed — a git host, an institutional
  archive — with a descriptive name and topics/keywords, not just a local path?

## Accessible

- **A1 (retrievable via a standard protocol):** If `data/raw/` isn't checked into git (common
  for large files), is there a documented, scriptable way to get it — a download script in
  `scripts/`, a documented URL, an accession number — rather than "ask so-and-so for the files"?
- **A1.1/A1.2 (open protocol, documented access control):** If the data has legitimate access
  restrictions (patient data, embargoed results, IRB constraints — worth checking for explicitly
  in a clinical/human-subjects context), FAIR doesn't require throwing it open; it requires the
  *access process* to be documented (who to contact, what approval is needed) rather than
  restricted-and-undocumented. Flag this as a judgment call for the user, not an automatic fail.
- **A2 (metadata survives even if data doesn't):** Is the description of what the raw data
  contains stored independently of the raw files themselves (in README/data dictionary), so the
  record of what existed survives even if the files are later deleted or embargoed?

## Interoperable

- **I1 (formal, shared representation):** Scan `data/raw/` and `data/final/` for file formats.
  Open, standard formats (csv, tsv, json, parquet, fasta, fastq, bam, vcf, h5ad) are fine.
  Proprietary or closed formats (xlsx, docx, sav, unexplained binary blobs) are a flag — not
  necessarily wrong if that's what the instrument/source produced, but worth noting, and ideally
  paired with an open-format export.
- **I2 (FAIR vocabularies):** Domain-specific and usually not mechanically checkable — e.g. gene
  symbols against a standard nomenclature, cell types against a standard ontology. Note as a
  manual-review item rather than trying to verify it programmatically. For single-cell/genomics
  conventions specifically, the "cellranger-integrator" skill's conventions are the relevant
  standard to check against.
- **I3 (qualified references between metadata):** Does derived data actually reference what
  produced it? This is where the setup-repo lineage convention pays off directly — check that
  `data/processed/N_*` and `data/figure/N_*` trace back to a `process_N`/`figure_N` rule pair in
  the `Snakefile`, which in turn names its raw input. If that chain is intact, I3 is satisfied
  structurally; if any N is missing a rule or the rule's input doesn't match what's actually in
  `data/raw/`, flag it.

## Reusable

- **R1 (richly described):** Do output datasets (especially `data/final/`) have column-level
  documentation — units, meaning, valid ranges — not just a filename?
- **R1.1 (clear license):** Is there a `LICENSE` (or `LICENSE.md`/`LICENSE.txt`) file in the repo
  root? This is usually the single highest-impact, easiest-to-fix gap — flag it prominently if
  missing, and ask what license the user wants rather than picking one for them (license choice
  has real legal implications).
- **R1.2 (detailed provenance):** This overlaps heavily with what "reproduce" checks
  mechanically — the `Snakefile` + `notebooks/analysis.md` + the N-numbering convention *are*
  the provenance record here. Confirm every figure in `figures/` has both a Snakefile rule pair
  and a notebook entry; a figure with one but not the other has a provenance gap.
- **R1.3 (community standards):** Domain-specific, same caveat as I2 — note relevant standards
  the user should check against (field-specific reporting guidelines, journal data policies)
  rather than asserting compliance.

## Running the check

Use the bundled script for the mechanical parts (file existence, format scanning, provenance
cross-referencing) rather than eyeballing the repo by hand — it's faster and won't miss a file:

```bash
python3 scripts/fair_checklist.py <path-to-repo>
```

It writes `FAIR_AUDIT.md` in the repo root: a checklist with ✅ / ❌ / ⚠️ (needs human judgment)
for each sub-principle, plus what was found. Read the output, then explain it to the user in
plain terms — lead with the highest-impact easy fixes (license file is the classic one), and be
explicit about which items are automatic findings versus which need the user's judgment (access
restrictions, vocabulary standards, license choice). Don't create or guess at content for
judgment-call items yourself — surface them and ask.
