#!/bin/bash
# Launch JupyterLab on a SLURM compute node and set up an SSH tunnel.
#
# Usage: hpc_jupyter.sh [MEM] [CPUS] [TIME] [PARTITION] [ACCOUNT] [IDLE_TIMEOUT]
#   MEM          default 64G (or DEFAULT_MEM env var)
#   CPUS         default 8 (or DEFAULT_CPUS env var)
#   TIME         default 4:00:00 (or DEFAULT_TIME env var)
#   PARTITION    required (arg 4, or set SLURM_PARTITION env var) unless
#                NODE_CANDIDATES is set (see below)
#   ACCOUNT      required (arg 5, or set SLURM_ACCOUNT env var)
#   IDLE_TIMEOUT default 7200 (2h) seconds of Jupyter inactivity before it
#                shuts itself down; 0 disables it. (arg 6, or set
#                JUPYTER_IDLE_TIMEOUT env var)
#
# PARTITION and ACCOUNT are cluster-specific and have no sane default —
# set them via args or export SLURM_PARTITION / SLURM_ACCOUNT in your shell
# profile so you don't have to pass them every time. See config.example for
# a template covering all of the env vars below — copy it, fill it in, and
# source it from your shell profile.
#
# Optional node targeting (env vars only, no positional args):
#   SLURM_NODELIST_REQUEST  pin to one specific compute node within
#                           PARTITION (used only if NODE_CANDIDATES is unset)
#   NODE_CANDIDATES         ordered "partition:node" pairs, space-separated
#                           (e.g. "lbarreiro:midway3-0323 lbarreiro-hm:midway3-0436").
#                           Takes priority over PARTITION/SLURM_NODELIST_REQUEST.
#                           Tried in order; falls through to the next pair
#                           only if sbatch itself rejects the submission (not
#                           if the job merely sits PENDING).
#
# Conda environment (env var only, no positional arg):
#   CONDA_ENV   name of the conda environment that has Jupyter installed.
#               Required unless a conda environment is already active
#               (CONDA_DEFAULT_ENV set) in the shell running this script —
#               sbatch inherits this shell's environment, so activation must
#               happen here, not inside the job. If neither is set, the
#               script exits with an error asking for one.
#
# Job log directory (env var only, no positional arg):
#   LOG_DIR     directory to write the job's log (hostname + Jupyter token
#               URL) to. Defaults to the current directory ($PWD) rather
#               than /tmp, since /tmp is often local, per-node scratch on
#               HPC clusters — not shared between the login node (where
#               this script polls the log) and the compute node (where the
#               job writes it). Must already exist and be writable; the
#               script does not create it.
#
# The job is submitted via sbatch, so it runs as an independent batch job:
# it keeps running even if this terminal/SSH session closes. Use
# stop_jupyter.sh <SLURM_JOB_ID> to cancel it.

MEM="${1:-${DEFAULT_MEM:-64G}}"
CPUS="${2:-${DEFAULT_CPUS:-8}}"
TIME="${3:-${DEFAULT_TIME:-4:00:00}}"
PARTITION="${4:-$SLURM_PARTITION}"
ACCOUNT="${5:-$SLURM_ACCOUNT}"
IDLE_TIMEOUT="${6:-${JUPYTER_IDLE_TIMEOUT:-7200}}"
PORT=8889
LOG_DIR="${LOG_DIR:-$PWD}"

if [ ! -d "$LOG_DIR" ]; then
  echo "ERROR: LOG_DIR '$LOG_DIR' does not exist."
  echo "  Create it first, or set LOG_DIR to an existing directory."
  exit 1
fi
if [ ! -w "$LOG_DIR" ]; then
  echo "ERROR: LOG_DIR '$LOG_DIR' is not writable."
  exit 1
fi
LOG="$LOG_DIR/jupyter_hpc_%j.log"

if [ -z "$ACCOUNT" ]; then
  echo "ERROR: ACCOUNT is required."
  echo "  Usage: hpc_jupyter.sh [MEM] [CPUS] [TIME] <PARTITION> <ACCOUNT> [IDLE_TIMEOUT]"
  echo "  Or export SLURM_ACCOUNT in your shell profile."
  exit 1
fi

# sbatch inherits this shell's environment (including PATH), so a conda env
# must be activated here, before submission — activating it inside the job
# itself would be too late for sbatch to see it.
if [ -z "$CONDA_DEFAULT_ENV" ]; then
  if [ -z "$CONDA_ENV" ]; then
    echo "ERROR: no conda environment is active, and CONDA_ENV is not set."
    echo "  Ask the user which conda environment has Jupyter installed (they can"
    echo "  check with 'conda env list'), then re-run with:"
    echo "    CONDA_ENV=<env-name> bash scripts/hpc_jupyter.sh ..."
    exit 1
  fi
  CONDA_BASE=$(conda info --base 2>/dev/null)
  if [ -z "$CONDA_BASE" ] || [ ! -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    echo "ERROR: could not locate conda (needed to activate CONDA_ENV=$CONDA_ENV)."
    echo "  Make sure 'conda' is on PATH, or load your cluster's conda/anaconda module first."
    exit 1
  fi
  # shellcheck disable=SC1091
  source "$CONDA_BASE/etc/profile.d/conda.sh"
  if ! conda activate "$CONDA_ENV" 2>/dev/null; then
    echo "ERROR: 'conda activate $CONDA_ENV' failed. Check the environment name with 'conda env list'."
    exit 1
  fi
  echo "Activated conda environment: $CONDA_ENV"
fi

# Build the ordered list of "partition:node" candidates to try. NODE_CANDIDATES
# wins if set (it supplies its own partitions); otherwise fall back to a
# single candidate built from PARTITION [+ SLURM_NODELIST_REQUEST].
CANDIDATES=()
if [ -n "$NODE_CANDIDATES" ]; then
  read -ra CANDIDATES <<< "$NODE_CANDIDATES"
elif [ -n "$PARTITION" ]; then
  CANDIDATES=("$PARTITION:$SLURM_NODELIST_REQUEST")
else
  echo "ERROR: PARTITION is required (unless NODE_CANDIDATES is set)."
  echo "  Usage: hpc_jupyter.sh [MEM] [CPUS] [TIME] <PARTITION> <ACCOUNT> [IDLE_TIMEOUT]"
  echo "  Or export SLURM_PARTITION (or NODE_CANDIDATES) in your shell profile."
  exit 1
fi

if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: 'sbatch' not found on PATH. Load your cluster's Slurm module first"
  echo "  (e.g. 'module load slurm') or add it to PATH, then retry."
  exit 1
fi

JOBID=""
for CAND in "${CANDIDATES[@]}"; do
  CAND_PARTITION="${CAND%%:*}"
  CAND_NODE="${CAND#*:}"
  [ "$CAND_NODE" = "$CAND" ] && CAND_NODE=""
  NODE_FLAG=()
  [ -n "$CAND_NODE" ] && NODE_FLAG=(--nodelist="$CAND_NODE")

  echo "Submitting batch job (partition=$CAND_PARTITION${CAND_NODE:+, node=$CAND_NODE}, account=$ACCOUNT, mem=$MEM, cpus=$CPUS, time=$TIME, idle_timeout=${IDLE_TIMEOUT}s)..."
  SBATCH_OUT=$(sbatch --partition="$CAND_PARTITION" --account="$ACCOUNT" \
    --mem="$MEM" --cpus-per-task="$CPUS" --time="$TIME" \
    "${NODE_FLAG[@]}" \
    --job-name=hpc_jupyter --output="$LOG" \
    --wrap="echo HOSTNAME:\$(hostname); jupyter lab --no-browser --port=$PORT --ServerApp.shutdown_no_activity_timeout=$IDLE_TIMEOUT" 2>&1)

  CAND_JOBID=$(echo "$SBATCH_OUT" | grep -oE '[0-9]+' | head -1)
  if [ -n "$CAND_JOBID" ]; then
    JOBID="$CAND_JOBID"
    PARTITION="$CAND_PARTITION"
    break
  fi
  echo "  Rejected: $SBATCH_OUT"
done

if [ -z "$JOBID" ]; then
  echo "ERROR: sbatch submission failed for every candidate tried."
  exit 1
fi

REAL_LOG="$LOG_DIR/jupyter_hpc_${JOBID}.log"
echo "SLURM job ID: $JOBID (log: $REAL_LOG)"
echo "This job runs independently of this terminal — it will keep running"
echo "even if you close this session."

# Cancel the job if we're interrupted before the session is confirmed up,
# so an aborted launch doesn't leave an orphaned queued/running job.
CONFIRMED=0
cleanup_on_interrupt() {
  if [ "$CONFIRMED" -eq 0 ]; then
    echo ""
    echo "Interrupted before Jupyter was confirmed up — cancelling job $JOBID."
    scancel "$JOBID" 2>/dev/null
    exit 130
  fi
}
trap cleanup_on_interrupt INT TERM

echo "Waiting for the job to start running (queue wait is unbounded — this"
echo "depends on cluster load)..."

LAST_STATE=""
while true; do
  STATE=$(squeue -j "$JOBID" -h -o "%T" 2>/dev/null)
  if [ -z "$STATE" ]; then
    # Job no longer in the queue — it either never ran or already finished.
    if [ -f "$REAL_LOG" ] && grep -q "token=" "$REAL_LOG" 2>/dev/null; then
      break
    fi
    echo "ERROR: job $JOBID is no longer in the queue and never produced a"
    echo "  Jupyter token. Check $REAL_LOG for details."
    trap - INT TERM
    exit 1
  fi
  if [ "$STATE" != "$LAST_STATE" ]; then
    echo "Job $JOBID: $STATE"
    LAST_STATE="$STATE"
  fi
  [ "$STATE" = "RUNNING" ] && break
  sleep 10 &
  wait $!
done

echo "Job is running. Waiting for Jupyter to start..."

NODE=""
TOKEN_URL=""
for i in $(seq 1 24); do
  if [ -f "$REAL_LOG" ]; then
    if [ -z "$NODE" ]; then
      NODE=$(grep "^HOSTNAME:" "$REAL_LOG" 2>/dev/null | head -1 | sed 's/HOSTNAME://')
      [ -n "$NODE" ] && echo "Allocated node: $NODE"
    fi
    TOKEN_URL=$(grep "http://127.0.0.1:$PORT" "$REAL_LOG" 2>/dev/null | grep "token=" | tail -1 | tr -d ' ')
    [ -n "$TOKEN_URL" ] && break
  fi
  sleep 5 &
  wait $!
done

if [ -z "$TOKEN_URL" ]; then
  echo "ERROR: Jupyter did not start within 2 minutes of the job running. Check $REAL_LOG"
  scancel "$JOBID" 2>/dev/null
  trap - INT TERM
  exit 1
fi

CONFIRMED=1
trap - INT TERM

echo "Setting up SSH tunnel: localhost:$PORT -> $NODE:$PORT"
ssh -f -N -L $PORT:localhost:$PORT "$NODE"

# Convert 127.0.0.1 to localhost for VSCode compatibility
VSCODE_URL=$(echo "$TOKEN_URL" | sed "s/127.0.0.1/localhost/")

echo ""
echo "================================================"
echo "Jupyter is ready! Connect VSCode to:"
echo "$VSCODE_URL"
echo "================================================"
echo ""
echo "In VSCode: kernel picker -> Select Another Kernel"
echo "        -> Existing Jupyter Server -> paste URL above"
echo ""
echo "Jupyter will auto-shutdown after ${IDLE_TIMEOUT}s of inactivity."
echo "SLURM job ID: $JOBID"
echo "To stop: bash scripts/stop_jupyter.sh $JOBID"
