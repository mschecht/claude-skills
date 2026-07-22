#!/bin/bash
# Stop a JupyterLab session started by hpc_jupyter.sh: cancels the SLURM
# job and closes the local SSH tunnel on the given port.
#
# Usage: stop_jupyter.sh <SLURM_JOB_ID> [PORT]

JOBID="$1"
PORT="${2:-8889}"

if [ -z "$JOBID" ]; then
  echo "Usage: stop_jupyter.sh <SLURM_JOB_ID> [PORT]"
  exit 1
fi

echo "Cancelling SLURM job $JOBID..."
scancel "$JOBID" && echo "Sent cancel request for job $JOBID." \
  || echo "scancel failed for job $JOBID (it may have already finished)."

echo "Closing SSH tunnel on port $PORT..."
TUNNEL_PID=$(pgrep -f "ssh -f -N -L $PORT:localhost:$PORT" | head -1)
if [ -n "$TUNNEL_PID" ]; then
  kill "$TUNNEL_PID" && echo "Closed tunnel (PID $TUNNEL_PID)."
else
  echo "No matching SSH tunnel process found for port $PORT."
fi

echo "Done. If the job doesn't disappear from 'squeue' within a minute, check its state with: squeue -j $JOBID"
