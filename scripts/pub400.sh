#!/bin/sh
# Run a nox session that connects to PUB400, from the host, in the tests container:
#
#   scripts/pub400.sh [--wait] <session> [<arg> ...]
#   scripts/pub400.sh probe_qtemp qtemp_create_trigger
#
# Adapted from django-db2-for-i (scripts/pub400.sh), cut down to the sessions
# this project has. On macOS the run is wrapped in caffeinate (no idle or
# system sleep while it runs): a Mac that sleeps during a long run breaks the
# TLS connection (08S01, CWBCO1034). Only sessions that connect to PUB400 are
# accepted.
#
# Every run holds the PUB400 lock (scripts/pub400_lock.py, unchanged from the
# backend), in the same directory as the backend's runs: one PUB400 job at a
# time on this machine, across both projects. A second run stops with "PUB400
# busy: <holder>", or waits with --wait (or DB2I_LOCK_WAIT=1). The container
# keeps the backend's name prefix (db2i-pub400-), so the lock also stops and
# cleans up this project's containers. The lock is released only after the
# run's container is gone.
set -eu

wait=
if [ "${DB2I_LOCK_WAIT:-}" = 1 ]; then
    wait=--wait
fi
if [ "${1:-}" = --wait ]; then
    wait=--wait
    shift
fi
if [ $# -lt 1 ]; then
    echo "usage: $0 [--wait] <nox-session> [<arg> ...]" >&2
    exit 2
fi
session=$1
shift
case $session in
    probe_qtemp|probe_lib) ;;
    *)
        echo "refused: $session does not connect to PUB400; run: docker compose run --rm tests nox -s $session" >&2
        exit 2
        ;;
esac

cd "$(dirname "$0")/.."
# Read on the host: in a git worktree the container cannot read the repository.
commit=$(git log -1 --format='%h %cs' 2>/dev/null || echo unknown)
# The state directory of the lock, outside every checkout, also holds the list
# of objects test runs create, shared with the backend (bin/ibmi-cleanup).
state=$(python3 scripts/pub400_lock.py --dir)
mkdir -p "$state"
# A named container: the lock stops it before it is released (a stopped run
# would otherwise leave the container and its PUB400 connection behind).
container="db2i-pub400-$$"
# This checkout's own nox virtualenvs (scripts/nox_volume.sh).
DB2I_NOX_ENVS=$(scripts/nox_volume.sh .)
export DB2I_NOX_ENVS
set -- docker compose run --rm --name "$container" -e DB2I_RUN_COMMIT="$commit" \
    -v "$state:/db2i-state" -e DB2I_TABLE_LIST=/db2i-state/created-objects.txt \
    tests nox -s "$session" -- "$@"
if command -v caffeinate >/dev/null 2>&1; then
    set -- caffeinate -i -s "$@"
fi
exec python3 scripts/pub400_lock.py $wait --container "$container" -- "$@"
