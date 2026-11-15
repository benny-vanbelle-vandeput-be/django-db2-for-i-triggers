# Shared part of the bin/ scripts, sourced by each of them. Adapted from
# django-db2-for-i (bin/_common.sh), cut down to what this project uses.
#
# - --help / -h prints the script's header comment; --dry-run prints every
#   command instead of running it (run); --wait (DB2I_LOCK_WAIT=1) queues
#   behind a running PUB400 job instead of stopping.
# - container runs a command in the tests container (docker compose), with
#   the checkout's own nox-envs volume (scripts/nox_volume.sh). In a
#   git worktree it also mounts the repository's shared git directory at its
#   host path, so git works inside the container. The checkout's mount
#   (/workspace) is git's safe.directory for that one run (passed as
#   environment, never written to a config file, never '*').
# - pub400 runs a PUB400 nox session through scripts/pub400.sh, which holds
#   the PUB400 lock (one PUB400 job at a time on this machine).
#
# No secrets: the scripts never read, source or print .env; docker compose
# loads it into the container itself. Written for bash 3.2 (macOS).

set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# The checkout's mount point in the container (compose.yaml).
WORKSPACE=/workspace
DRY_RUN=0
ARGS=()

usage() {
    # The header comment of the calling script, up to the first blank line.
    awk 'NR == 1 { next } /^#/ { sub(/^# ?/, ""); print; next } { exit }' "$0"
}

# Handles --help, --dry-run and --wait; the other arguments are left in ARGS.
common_args() {
    ARGS=()
    local arg
    for arg in "$@"; do
        case $arg in
            -h | --help)
                usage
                exit 0
                ;;
            --dry-run) DRY_RUN=1 ;;
            --wait) export DB2I_LOCK_WAIT=1 ;;
            *) ARGS+=("$arg") ;;
        esac
    done
}

die() {
    echo "$(basename "$0"): $*" >&2
    exit 2
}

run() {
    if [ "$DRY_RUN" = 1 ]; then
        printf '+'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

container() {
    local common mounts=()
    common=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
    if [ -n "$common" ] && [ "$common" != "$ROOT/.git" ]; then
        mounts=(-v "$common:$common")
    fi
    # This checkout's own nox virtualenvs (scripts/nox_volume.sh).
    run env DB2I_NOX_ENVS="$("$ROOT/scripts/nox_volume.sh" "$ROOT")" \
        docker compose --project-directory "$ROOT" run --rm ${mounts[@]+"${mounts[@]}"} \
        -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0="$WORKSPACE" \
        tests "$@"
}

pub400() {
    run "$ROOT/scripts/pub400.sh" "$@"
}
