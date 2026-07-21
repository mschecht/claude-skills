# hpc-jupyter-vscode

A Claude Code / Cowork plugin that launches a JupyterLab server on a SLURM compute node and
tunnels it to VSCode as a remote Jupyter kernel, without having to hand-build the
`sbatch`/log-scraping/SSH-tunnel incantation yourself.

## Skill

| Skill | What it does |
|---|---|
| `hpc-jupyter-vscode` | Submits a JupyterLab job to SLURM via `sbatch` (survives terminal/SSH disconnects), waits for it to start, opens an SSH tunnel, and prints a URL to paste into VSCode's kernel picker. Also stops a session (`scancel` + tunnel teardown). Jupyter self-shuts-down after an idle timeout (default 2h) so a forgotten session doesn't burn allocation hours. |

## Install

```
/plugin marketplace add mschechter/claude-skills
/plugin install hpc-jupyter-vscode
```

(Replace `mschechter/claude-skills` with wherever this repo ends up hosted.)

## Configuration

Needs a SLURM **partition** and **account** to submit to — cluster-specific, no sensible
default. Set them via `SLURM_PARTITION` / `SLURM_ACCOUNT` in your shell profile, or pass them as
script args. For a durable setup, copy
`skills/hpc-jupyter-vscode/config.example` somewhere like `~/.hpc_jupyter.conf`, fill it in, and
source it from your shell profile — it also covers optional node pinning
(`SLURM_NODELIST_REQUEST`), a partition/node fallback list (`NODE_CANDIDATES`), and default
resource overrides (`DEFAULT_MEM`/`DEFAULT_CPUS`/`DEFAULT_TIME`). See the skill's `SKILL.md` for
the full details.

## Why

The failure-prone part of "run Jupyter on HPC" isn't Jupyter — it's the SLURM job model. A
naive `srun`-in-the-background approach dies the moment your terminal or SSH session closes,
which defeats the point of a session meant to run for hours. This skill uses `sbatch` instead, so
the job is independent of your terminal, and adds an idle-timeout so you don't leave an
allocation running by accident.
