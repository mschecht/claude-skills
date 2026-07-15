#!/usr/bin/env bash
#
# Verify that a conda environment file can be built from scratch, in a disposable,
# randomly-suffixed environment, then tear it down. Never touches the caller's active
# or base environment, and always cleans up (even on failure or interrupt).
#
# Usage:
#   verify_fresh_env.sh <path-to-environment.yml> [smoke-test-command]
#
# Examples:
#   verify_fresh_env.sh environment.yml "snakemake --version"
#   verify_fresh_env.sh envs/figure3.yml "Rscript -e 'library(ggplot2)'"

set -uo pipefail

ENV_FILE="${1:-}"
SMOKE_CMD="${2:-}"

if [ -z "$ENV_FILE" ] || [ ! -f "$ENV_FILE" ]; then
  echo "Usage: $0 <path-to-environment.yml> [smoke-test-command]" >&2
  exit 2
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "FAIL: conda is not on PATH — can't verify anything without conda itself installed." >&2
  exit 2
fi

BASENAME="$(basename "$ENV_FILE" | sed 's/\.[^.]*$//')"
TMP_ENV_NAME="_envaudit_${BASENAME}_$$_$RANDOM"
CREATE_LOG="$(mktemp)"
SMOKE_LOG="$(mktemp)"

cleanup() {
  conda env remove -n "$TMP_ENV_NAME" -y >/dev/null 2>&1
  rm -f "$CREATE_LOG" "$SMOKE_LOG"
}
trap cleanup EXIT

echo "Building '$TMP_ENV_NAME' from $ENV_FILE (this installs real packages — may take a while) ..."
if ! conda env create -f "$ENV_FILE" -n "$TMP_ENV_NAME" >"$CREATE_LOG" 2>&1; then
  echo "FAIL: environment could not be created from scratch."
  echo "--- last 40 lines of conda output ---"
  tail -40 "$CREATE_LOG"
  exit 1
fi
echo "PASS: environment builds cleanly from $ENV_FILE."

if [ -n "$SMOKE_CMD" ]; then
  echo "Running smoke test: $SMOKE_CMD"
  if conda run -n "$TMP_ENV_NAME" bash -c "$SMOKE_CMD" >"$SMOKE_LOG" 2>&1; then
    echo "PASS: smoke test succeeded."
  else
    echo "FAIL: environment built, but the smoke test failed."
    echo "--- last 40 lines of smoke test output ---"
    tail -40 "$SMOKE_LOG"
    exit 1
  fi
fi

echo "RESULT: $ENV_FILE is verified reproducible from scratch."
