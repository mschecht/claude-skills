#!/bin/bash
# Launch JupyterLab on a SLURM compute node and set up an SSH tunnel.
#
# Usage: hpc_jupyter.sh [MEM] [CPUS] [TIME] [PARTITION] [ACCOUNT] [IDLE_TIMEOUT]
#   MEM          default 64G
#   CPUS         default 8
#   TIME         default 4:00:00
#   PARTITION    required (arg 4, or set SLURM_PARTITION env var)
#   ACCOUNT      required (arg 5, or set SLURM_ACCOUNT env var)
#   IDLE_TIMEOUT default 7200 (2h) seconds of Jupyter inactivity before it
#                shuts itself down; 0 disables it. (arg 6, or set
#                JUPYTER_IDLE_TIMEOUT env var)
#
# PARTITION and ACCOUNT are cluster-specific and have no sane default —
# set them via args or export SLURM_PARTITION / SLURM_ACCOUNT in your shell
# profile so you don't have to pass them every time.
#
# The job is submitted via sbatch, so it runs as an independent batch job:
# it keeps running even if this terminal/SSH session closes. Use
# stop_jupyter.sh <SLURM_JOB_ID> to cancel it.

MEM="${1:-64G}"
CPUS="${2:-8}"
TIME="${3:-4:00:00}"
PARTITION="${4:-$SLURM_PARTITION}"
ACCOUNT="${5:-$SLURM_ACCOUNT}"
IDLE_TIMEOUT="${6:-${JUPYTER_IDLE_TIMEOUT:-7200}}"
PORT=8889
LOG="/tmp/jupyter_hpc_%j.log"

if [ -z "$PARTITION" ] || [ -z "$ACCOUNT" ]; then
  echo "ERROR: PARTITION and ACCOUNT are required."
  echo "  Usage: hpc_jupyter.sh [MEM] [CPUS] [TIME] <PARTITION> <ACCOUNT> [IDLE_TIMEOUT]"
  echo "  Or export SLURM_PARTITION and SLURM_ACCOUNT in your shell profile."
  exit 1
fi

if ! command -v sbatch >/dev/null 2>&1; then
  echo "ERROR: 'sbatch' not found on PATH. Load your cluster's Slurm module first"
  echo "  (e.g. 'module load slurm') or add it to PATH, then retry."
  exit 1
fi

echo "Submitting batch job (partition=$PARTITION, account=$ACCOUNT, mem=$MEM, cpus=$CPUS, time=$TIME, idle_timeout=${IDLE_TIMEOUT}s)..."
SBATCH_OUT=$(sbatch --partition="$PARTITION" --account="$ACCOUNT" \
  --mem="$MEM" --cpus-per-task="$CPUS" --time="$TIME" \
  --job-name=hpc_jupyter --output="$LOG" \
  --wrap="echo HOSTNAME:\$(hostname); jupyter lab --no-browser --port=$PORT --ServerApp.shutdown_no_activity_timeout=$IDLE_TIMEOUT" 2>&1)

JOBID=$(echo "$SBATCH_OUT" | grep -oE '[0-9]+' | head -1)
if [ -z "$JOBID" ]; then
  echo "ERROR: sbatch submission failed:"
  echo "$SBATCH_OUT"
  exit 1
fi

REAL_LOG="/tmp/jupyter_hpc_${JOBID}.log"
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
