---
name: slurm-jupyter-tunnel
description: >
  Launches a JupyterLab server on a SLURM compute node and sets up an SSH
  tunnel so it can be attached to as a remote Jupyter kernel from VSCode.
  Use this skill whenever the user asks to "launch Jupyter on the
  cluster/HPC/SLURM", "start a JupyterLab session on a compute node", "get a
  Jupyter kernel from SLURM", "connect VSCode to an HPC notebook", or wants
  to stop/clean up an existing SLURM Jupyter session and its SSH tunnel.
  Always use this skill for these tasks instead of improvising
  srun/jupyter/ssh commands from scratch — it encodes the exact working
  incantation (log-scraping for the hostname and token, tunnel setup,
  VSCode hookup) that has already been proven to work on SLURM clusters.
---

# Slurm Jupyter Tunnel

Launch JupyterLab on a SLURM compute node and connect VSCode to it as a
remote kernel, without the user having to babysit job output or hand-build
an SSH tunnel.

## Prerequisites

This skill runs `sbatch`/`squeue`/`ssh <compute-node>` directly — it does
**not** SSH into the cluster on your behalf. The environment this skill runs
in must already be connected to the cluster's **login node**: either

- VSCode connected to the login node via the **Remote-SSH** extension, with
  Claude Code running inside that remote window, or
- An interactive terminal already SSH'd into the login node, running Claude
  Code there.

This also explains the URL this skill prints: `http://localhost:8889/?token=...`
refers to `localhost` **on the login node**, not the user's laptop. It only
becomes reachable in the user's actual VSCode because a Remote-SSH connection
auto-forwards ports it detects on the remote host back to the local machine.
If you're not running in a session connected to the cluster, none of this
works — `sbatch` won't even be on `PATH`. In that case, tell the user to open
VSCode connected to the cluster via Remote-SSH (or an equivalent SSH session)
first, rather than trying to work around it.

## Requirements

New user, nothing configured yet? Gather everything below **in one pass**
before running the launch script — don't run it, hit one missing-value
error, ask, retry, hit the next error, and repeat. You need:

- **SLURM partition** and **account** — cluster-specific, no sensible
  default. If the user doesn't know theirs offhand, help them find it (next
  section) rather than sending them off to look it up themselves.
- **Conda environment** with Jupyter installed — see "Conda environment"
  below.

Once you have them, pass them as script args/env vars for this launch. Either
way, always write them into a durable config file afterward (see
"Configuration" below) so future launches don't require asking again.

## Configuration

### Finding your partition and account

If the user doesn't already know these, run this on the login node:

```bash
sacctmgr show associations user=$USER format=Account,Partition%30
```

This lists every account/partition combination the user is actually
authorized to submit to — show them the output and ask them to pick, rather
than guessing one. If `sacctmgr` isn't available or returns nothing (some
clusters restrict it), fall back to `sinfo -s` for a general partition list
and ask the user which account their PI/lab uses, or point them at their
cluster's documentation.

### Setting them

Set them one of two ways:

- Pass them as the 4th and 5th positional args to the launch script, or
- Export `SLURM_PARTITION` and `SLURM_ACCOUNT` in your shell profile so you
  never have to type them.

If neither is set (and `NODE_CANDIDATES` isn't set either — see below), the
script exits with an error rather than guessing.

For a durable per-cluster setup, copy `config.example` to somewhere like
`~/.slurm_jupyter_tunnel.conf`, fill in your values, and source it from your shell
profile. It covers everything above plus two optional extras, both env-var
only (no positional args for these):

- `SLURM_NODELIST_REQUEST` — pin to one specific compute node within
  `SLURM_PARTITION` (used only if `NODE_CANDIDATES` is unset).
- `NODE_CANDIDATES` — an ordered, space-separated list of `partition:node`
  pairs (e.g. `"lbarreiro:midway3-0323 lbarreiro-hm:midway3-0436"`) to try
  in turn. Takes priority over `SLURM_PARTITION`/`SLURM_NODELIST_REQUEST`.
  The script moves to the next pair only if `sbatch` itself rejects the
  submission — a job that's merely `PENDING` is left alone, not skipped.

It also lets you override the script's resource defaults via `DEFAULT_MEM`,
`DEFAULT_CPUS`, and `DEFAULT_TIME`, so you don't have to pass `MEM`/`CPUS`/
`TIME` every time either.

### Conda environment

The script needs Jupyter to be on `PATH` in the shell it runs in — `sbatch`
inherits that shell's environment, so the right conda environment has to be
active *before* submission, not inside the job. Before running the launch
script:

1. Check whether a conda environment is already active
   (`echo $CONDA_DEFAULT_ENV`). If so, nothing to do — the script will use it.
2. If not, **ask the user which conda environment has Jupyter installed**
   (suggest `conda env list` if they're not sure) rather than guessing one.
3. Pass their answer via `CONDA_ENV=<env-name>` when invoking the script, or
   set it in `config.example`/`~/.slurm_jupyter_tunnel.conf` for a durable default.

If you skip this and the script isn't given `CONDA_ENV`, it exits with an
error explaining exactly this — at that point, ask the user and retry rather
than guessing an environment name.

### Job log location

The job's log (allocated hostname + Jupyter token URL, which this script
polls to know the session is up) is written to `LOG_DIR/jupyter_hpc_<job_id>.log`.
`LOG_DIR` defaults to `$HOME/.cache/hpc_jupyter` — not `/tmp` — because
`/tmp` is frequently node-local scratch on HPC clusters, not shared between
the login node (where this script polls) and the compute node (where the
job writes). The script creates `LOG_DIR` automatically if it doesn't
exist. Override it with `LOG_DIR` if `$HOME` isn't shared storage on your
cluster (uncommon, but possible) — point it at project or scratch space
instead.

### Saving your config for next time

After every successful launch, write (or update) `~/.slurm_jupyter_tunnel.conf`
with the values that worked — partition, account, conda env, and any node
targeting used — using `config.example` as the template. Do this
unconditionally, every launch, not just the first time a config file is
missing: it's this skill's own file, so keep it current rather than only
offering to create it once. It's fine to overwrite it silently with the
latest working values.

Adding the `source ~/.slurm_jupyter_tunnel.conf` line to the user's shell
profile (`~/.bashrc`/`~/.zshrc`) is different — that edits a file outside
this skill's own scope, so still ask before doing that, and only do it once.
Once that line is in place, the next launch on this cluster needs no
interview at all, since the config file is already kept up to date.

## Launching a session

Before running this for the first time in a session (or whenever partition/
account/conda env aren't already known), complete the Configuration
interview above first — don't discover missing values one script failure at
a time.

Run the bundled script:

```bash
bash scripts/hpc_jupyter.sh [MEM] [CPUS] [TIME] <PARTITION> <ACCOUNT> [IDLE_TIMEOUT]
```

Defaults if `MEM`/`CPUS`/`TIME` are omitted: `64G` memory, `8` CPUs,
`4:00:00` time. `PARTITION` and `ACCOUNT` are required (or read from
`SLURM_PARTITION` / `SLURM_ACCOUNT`). `IDLE_TIMEOUT` defaults to `7200`
(2h) seconds of Jupyter inactivity before it shuts itself down — `0`
disables it — and can also be set via `JUPYTER_IDLE_TIMEOUT`. Example on a
cluster with partition `my-lab-hm` and account `pi-mylab`:

```bash
bash scripts/hpc_jupyter.sh 256G 16 8:00:00 my-lab-hm pi-mylab
```

What the script does, in order:
1. If no conda environment is already active, activates `CONDA_ENV` (erroring
   out with instructions to ask the user if it isn't set — see Configuration
   above).
2. Submits the Jupyter job via `sbatch` — an independent batch job that
   keeps running even if this terminal or SSH session closes.
3. Polls `squeue` for the job's state and prints it as it changes
   (`PENDING` → `RUNNING`); queue wait time is unbounded and depends on
   cluster load, so watch the terminal for updates rather than assuming
   it's stuck.
4. Once running, polls the job's log for the allocated hostname and the
   Jupyter token URL (bounded to ~2 minutes after the job starts running).
5. Once both are found, opens a local SSH tunnel (`localhost:8889 ->
   <node>:8889`) so the notebook server is reachable from the login node /
   your laptop without needing direct access to the compute node.
6. Prints the final `http://localhost:8889/?token=...` URL and the SLURM job
   ID.

Tell the user up front that this runs in the background and to watch the
terminal — don't block waiting for it silently. Once the URL and job ID
print:

1. Copy the `http://localhost:8889/?token=...` URL.
2. In VSCode: kernel picker (top right of a notebook) → **Select Another
   Kernel** → **Existing Jupyter Server** → paste the URL.

Remind the user to hold onto the printed **SLURM job ID** — it's needed to
stop the session cleanly later, and isn't recoverable after the terminal
scrolls past it (though it's also embedded in the job's log file path,
`LOG_DIR/jupyter_hpc_<job_id>.log`).

## Stopping a session

When the user is done, or asks to stop/kill/clean up the Jupyter session,
run:

```bash
bash scripts/stop_jupyter.sh <SLURM_JOB_ID>
```

This cancels the SLURM job via `scancel` and closes the local SSH tunnel on
port 8889. If the user only has the log file path and not the job ID, it's
embedded in the filename: `jupyter_hpc_<job_id>.log`.

## Notes

- The default port is 8889. If the user needs to run two sessions at once,
  edit `PORT` in `scripts/hpc_jupyter.sh` for the second invocation to avoid
  a collision on both the tunnel and the notebook server.
- This assumes passwordless SSH between the login node and compute nodes
  (standard on most SLURM clusters) — if the tunnel step fails, that's the
  first thing to check.
