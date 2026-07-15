#!/usr/bin/env python3
"""
Mechanical FAIR checks for a setup-repo-style data-analysis repository.

Checks what can actually be checked by inspecting the filesystem — file existence, formats,
and whether the figure/notebook/Snakefile provenance chain is intact. Anything that requires
judgment (is this the right license, is this vocabulary standard, is the access process
adequate) is reported as "needs review," not silently passed or failed.

Usage:
    python3 fair_checklist.py <path-to-repo>

Writes <repo>/FAIR_AUDIT.md and also prints a summary to stdout.
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone

OPEN_FORMATS = {
    ".csv", ".tsv", ".txt", ".json", ".jsonl", ".parquet", ".fasta", ".fa", ".fastq", ".fq",
    ".bam", ".sam", ".vcf", ".h5ad", ".yaml", ".yml", ".md", ".xml", ".gff", ".gff3", ".bed",
}
FLAGGED_FORMATS = {
    ".xlsx", ".xls", ".doc", ".docx", ".sav", ".mat", ".rds", ".rdata",
}


def check(label, passed, detail=""):
    icon = "PASS" if passed else "FAIL"
    return {"label": label, "status": icon, "detail": detail}


def review(label, detail):
    return {"label": label, "status": "REVIEW", "detail": detail}


def run(cmd, cwd):
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=10)
        return out.returncode, out.stdout.strip()
    except Exception as e:
        return 1, str(e)


def find_license(repo):
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
        if os.path.exists(os.path.join(repo, name)):
            return name
    return None


def scan_formats(repo, subdir):
    flagged, open_found, other = [], [], []
    full = os.path.join(repo, subdir)
    if not os.path.isdir(full):
        return flagged, open_found, other
    for root, _, files in os.walk(full):
        for fn in files:
            if fn == ".gitkeep":
                continue
            ext = os.path.splitext(fn)[1].lower()
            rel = os.path.relpath(os.path.join(root, fn), repo)
            if ext in FLAGGED_FORMATS:
                flagged.append(rel)
            elif ext in OPEN_FORMATS:
                open_found.append(rel)
            else:
                other.append(rel)
    return flagged, open_found, other


def check_provenance_chain(repo):
    """For each figures/figureN.png, confirm a Snakefile rule pair and a notebook entry exist."""
    figures_dir = os.path.join(repo, "figures")
    snakefile_path = os.path.join(repo, "Snakefile")
    notebook_path = os.path.join(repo, "notebooks", "analysis.md")

    figure_ns = []
    if os.path.isdir(figures_dir):
        for fn in os.listdir(figures_dir):
            m = re.match(r"figure(\d+)\.png$", fn)
            if m:
                figure_ns.append(int(m.group(1)))
    figure_ns.sort()

    snakefile_text = ""
    if os.path.exists(snakefile_path):
        snakefile_text = open(snakefile_path).read()

    notebook_text = ""
    if os.path.exists(notebook_path):
        notebook_text = open(notebook_path).read()

    gaps = []
    for n in figure_ns:
        has_process_rule = bool(re.search(rf"rule\s+process_{n}\b", snakefile_text))
        has_figure_rule = bool(re.search(rf"rule\s+figure_{n}\b", snakefile_text))
        has_notebook_entry = bool(re.search(rf"##\s*Figure\s+{n}\b", notebook_text))
        missing = []
        if not has_process_rule:
            missing.append("process_N rule")
        if not has_figure_rule:
            missing.append("figure_N rule")
        if not has_notebook_entry:
            missing.append("notebook entry")
        if missing:
            gaps.append((n, missing))
    return figure_ns, gaps


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fair_checklist.py <path-to-repo>", file=sys.stderr)
        return 2

    repo = os.path.abspath(sys.argv[1])
    if not os.path.isdir(repo):
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 2

    results = {"Findable": [], "Accessible": [], "Interoperable": [], "Reusable": []}

    # --- Findable ---
    rc, remote = run(["git", "remote", "-v"], repo)
    results["Findable"].append(
        check("F1: git remote configured", rc == 0 and bool(remote), remote or "no remote found")
    )
    rc, tags = run(["git", "tag"], repo)
    results["Findable"].append(
        review("F1: tagged release / DOI", "no git tags found — consider a release or "
               "Zenodo DOI if this needs to be citable" if not tags else f"tags: {tags}")
    )
    readme_path = os.path.join(repo, "README.md")
    readme_text = open(readme_path).read() if os.path.exists(readme_path) else ""
    results["Findable"].append(
        check("F2: README describes the analysis", len(readme_text.strip()) > 0, readme_path)
    )
    results["Findable"].append(
        review("F4: indexed/searchable host", "verify the repo lives on a git host with a "
               "descriptive name/topics, not just locally")
    )

    # --- Accessible ---
    raw_flagged, raw_open, raw_other = scan_formats(repo, "data/raw")
    results["Accessible"].append(
        review("A1: raw data retrieval documented", "if data/raw/ isn't in git, confirm there's "
               "a documented/scriptable way to obtain it (download script, accession number)")
    )
    results["Accessible"].append(
        review("A1.2: access restrictions documented", "if data has legitimate access "
               "restrictions (human subjects, embargo), confirm the access process is written "
               "down somewhere, not just enforced silently")
    )
    results["Accessible"].append(
        check("A2: metadata independent of raw data", len(readme_text.strip()) > 0,
              "README exists independently of data/raw/ files" if readme_text.strip()
              else "no README to carry metadata if raw data becomes unavailable")
    )

    # --- Interoperable ---
    all_flagged = raw_flagged + scan_formats(repo, "data/final")[0]
    results["Interoperable"].append(
        check("I1: open data formats", len(all_flagged) == 0,
              f"flagged (proprietary/closed) files: {all_flagged}" if all_flagged
              else "no proprietary formats detected in data/raw or data/final")
    )
    results["Interoperable"].append(
        review("I2: standard vocabularies", "domain-specific — not mechanically checkable "
               "(e.g. gene symbols, ontology terms); review manually")
    )
    figure_ns, gaps = check_provenance_chain(repo)
    results["Interoperable"].append(
        check("I3: derived data references its source (provenance chain intact)", len(gaps) == 0,
              f"figures with gaps: {gaps}" if gaps
              else f"all {len(figure_ns)} figure(s) have matching Snakefile rules + notebook entries")
    )

    # --- Reusable ---
    results["Reusable"].append(
        review("R1: column-level documentation", "check data/final/ outputs have documented "
               "columns/units, not just filenames")
    )
    license_file = find_license(repo)
    results["Reusable"].append(
        check("R1.1: LICENSE file present", license_file is not None,
              license_file or "no LICENSE/LICENSE.md/LICENSE.txt found — highest-impact easy fix")
    )
    results["Reusable"].append(
        check("R1.2: provenance chain (same check as I3)", len(gaps) == 0,
              f"figures with gaps: {gaps}" if gaps else "provenance chain intact")
    )
    results["Reusable"].append(
        review("R1.3: community/domain standards", "check against field-specific reporting "
               "guidelines or journal data policies relevant to this project")
    )

    # --- Write report ---
    lines = [f"# FAIR Audit — {os.path.basename(repo)}",
              "",
              f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by the "
              "fair-audit skill. PASS/FAIL are mechanical checks; REVIEW items need a human "
              "judgment call and are not automatically scored.",
              ""]
    counts = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    for section, items in results.items():
        lines.append(f"## {section}")
        lines.append("")
        for item in items:
            counts[item["status"]] += 1
            icon = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}[item["status"]]
            lines.append(f"- {icon} **{item['label']}** — {item['detail']}")
        lines.append("")

    report = "\n".join(lines)
    out_path = os.path.join(repo, "FAIR_AUDIT.md")
    with open(out_path, "w") as f:
        f.write(report)

    print(report)
    print(f"\nWrote {out_path}")
    print(f"Summary: {counts['PASS']} pass, {counts['FAIL']} fail, {counts['REVIEW']} need review")
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
