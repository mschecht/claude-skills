---
name: hpc-jupyter-vscode
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

# HPC Jupyter + VSCode

Launch JupyterLab on a SLURM compute node and connect VSCode to it as a
remote kernel, without the user having to babysit job output or hand-build
an SSH tunnel.

## Configuration

This skill needs to know which SLURM **partition** and **account** to submit
to — these are specific to each cluster/lab and have no sensible default.
Set them one of two ways:

- Pass them as the 4th and 5th positional args to the launch script, or
- Export `SLURM_PARTITION` and `SLURM_ACCOUNT` in your shell profile so you
  never have to type them.

If neither is set, the script exits with an error rather than guessing.

## Launching a session

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
1. Submits the Jupyter job via `sbatch` — an independent batch job that
   keeps running even if this terminal or SSH session closes.
2. Polls `squeue` for the job's state and prints it as it changes
   (`PENDING` → `RUNNING`); queue wait time is unbounded and depends on
   cluster load, so watch the terminal for updates rather than assuming
   it's stuck.
3. Once running, polls the job's log for the allocated hostname and the
   Jupyter token URL (bounded to ~2 minutes after the job starts running).
4. Once both are found, opens a local SSH tunnel (`localhost:8889 ->
   <node>:8889`) so the notebook server is reachable from the login node /
   your laptop without needing direct access to the compute node.
5. Prints the final `http://localhost:8889/?token=...` URL and the SLURM job
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
`/tmp/jupyter_hpc_<job_id>.log`).

## Stopping a session

When the user is done, or asks to stop/kill/clean up the Jupyter session,
run:

```bash
bash scripts/stop_jupyter.sh <SLURM_JOB_ID>
```

This cancels the SLURM job via `scancel` and closes the local SSH tunnel on
port 8889. If the user only has the log file path and not the job ID, it's
embedded in the filename: `/tmp/jupyter_hpc_<job_id>.log`.

## Notes

- The default port is 8889. If the user needs to run two sessions at once,
  edit `PORT` in `scripts/hpc_jupyter.sh` for the second invocation to avoid
  a collision on both the tunnel and the notebook server.
- This assumes passwordless SSH between the login node and compute nodes
  (standard on most SLURM clusters) — if the tunnel step fails, that's the
  first thing to check.
