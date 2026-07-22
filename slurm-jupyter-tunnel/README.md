# slurm-jupyter-tunnel

A Claude Code / Cowork plugin that launches a JupyterLab server on a SLURM compute node and
tunnels it back to you, without having to hand-build the `sbatch` SSH-tunnel incantation
yourself. Works whether you attach from VSCode as a remote kernel or just open the URL in a
plain browser over your own SSH tunnel — see "Use cases" below.

## Skill

| Skill | What it does |
|---|---|
| `slurm-jupyter-tunnel` | Submits a JupyterLab job to SLURM via `sbatch` (survives terminal/SSH disconnects), waits for it to start, opens an SSH tunnel, and prints a URL to attach to it. Also stops a session (`scancel` + tunnel teardown). Jupyter self-shuts-down after an idle timeout (default 2h) so a forgotten session doesn't burn allocation hours. |

## Install

```
/plugin marketplace add mschechter/claude-skills
/plugin install slurm-jupyter-tunnel
```

(Replace `mschechter/claude-skills` with wherever this repo ends up hosted.)

## Prerequisite: run this connected to the cluster

This skill calls `sbatch`/`squeue`/`ssh <compute-node>` directly — it does not SSH into the
cluster for you. Claude Code needs to already be running in a session connected to the cluster's
**login node**, either of the two ways described below. The script's own SSH tunnel
(`localhost:8889` on the login node -> the compute node) is the same either way; what differs is
how that login-node port reaches your laptop.

## Use cases

### VSCode (Remote-SSH)

Claude Code runs inside a VSCode window connected to the login node via the **Remote-SSH**
extension. Remote-SSH auto-forwards ports it detects open on the remote host, so once the
script's tunnel opens `localhost:8889` on the login node, VSCode forwards that same port back to
your laptop with no extra setup. Take the printed `http://localhost:8889/?token=...` URL and
either:

- Paste it into VSCode's kernel picker: **Select Another Kernel** -> **Existing Jupyter Server**, or
- Open it directly in a browser on your laptop — it works there too, since the port is already forwarded.

### Plain SSH tunnel (any terminal, any browser)

Claude Code runs in a plain terminal already SSH'd into the login node — no VSCode involved.
Nothing here auto-forwards ports, so port 8889 on the login node isn't reachable from your laptop
by itself; you have to forward it yourself, e.g. from another terminal on your laptop:

```bash
ssh -L 8889:localhost:8889 you@login-node
```

Then open the printed `http://localhost:8889/?token=...` URL in your local browser — no VSCode
needed. If you don't want to open a second connection every time, add a `LocalForward 8889
localhost:8889` line to that host's entry in `~/.ssh/config` (or pass `-L 8889:localhost:8889` on
the SSH command you already use to connect) so the forward is always live.

## Requirements

- A SLURM **partition** and **account** to submit to — cluster-specific, no sensible default.
- A conda environment with Jupyter installed — either already active, or named via `CONDA_ENV`.
  Claude will ask which one to use if it can't tell.

## Configuration

The first time you run this on a given cluster, Claude will ask for the values above. After
that, it writes them to `~/.slurm_jupyter_tunnel.conf` (from the
`skills/slurm-jupyter-tunnel/config.example` template) and keeps that file up to date on every
launch, so you shouldn't need to repeat the interview. It'll ask before adding a `source
~/.slurm_jupyter_tunnel.conf` line to your shell profile — once that's in place, the config is
picked up automatically. The file also covers optional node pinning
(`SLURM_NODELIST_REQUEST`), a partition/node fallback list (`NODE_CANDIDATES`), default resource
overrides (`DEFAULT_MEM`/`DEFAULT_CPUS`/`DEFAULT_TIME`), and where the job log goes (`LOG_DIR`,
defaults to the current directory rather than `/tmp` since `/tmp` is often node-local on HPC
clusters). See the skill's `SKILL.md` for the full details.

## Why

The failure-prone part of "run Jupyter on HPC" isn't Jupyter — it's the SLURM job model. A
naive `srun`-in-the-background approach dies the moment your terminal or SSH session closes,
which defeats the point of a session meant to run for hours. This skill uses `sbatch` instead, so
the job is independent of your terminal, and adds an idle-timeout so you don't leave an
allocation running by accident.
