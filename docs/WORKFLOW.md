# Workflow

How to work on django-db2-for-i-triggers, step by step, with the exact
commands. This file is the single source: `bin/help` shows the quick start and
lists the topics, `bin/help <topic>` shows one of them. Every script in `bin/`
runs on the host, has `--help` and `--dry-run`, and never prints secrets. The
rules behind the steps are in [CONTRIBUTING.md](../CONTRIBUTING.md) and, for
Claude, in [CLAUDE.md](../CLAUDE.md). Adapted from django-db2-for-i's
docs/WORKFLOW.md; the IBM i steps (`bin/verify`, `bin/ibmi-test`, the
classification) come back with the IBM i tests.

## Quick start

A typical change, from a new branch to a pull request:

```sh
git fetch origin && git switch -c feat/<topic> origin/main   # 1. a branch from main
bin/check                                                     # 2. lint and offline tests
git add <paths> && git commit                                 # 3. signed, by explicit path
git push -u origin feat/<topic> && gh pr create               # 4. the pull request
```

Add a changelog fragment for a user-visible change (topic `commit`).

## setup: first-time installation

1. Install Docker (e.g. Docker Desktop) with the `docker compose` plugin.
   The host needs nothing else: bash 3.2 and the system `python3` are enough.
2. Run `bin/setup` **in your own terminal**:
   - it builds the images (`tests` with the IBM i Access ODBC Driver,
     `offline` without it);
   - when there is no `.env`, it copies `.env.example` and asks for the IBM i
     user, password (hidden), the two libraries and the host, and writes them
     into `.env` (mode 600, nothing printed). Use the **same** user and
     libraries as the backend's `.env`. An existing `.env` is never read or
     changed.
3. Run `bin/doctor`: Docker, the driver in the image, `.env`, the PUB400 lock.

`bin/setup` is for humans: Claude never runs it interactively and never
enters values. The image with the IBM driver is built locally and never
pushed to a public registry (IBM's license).

## branch: starting work

1. One branch per logical change, named `<type>/<topic>` (`feat/`, `fix/`,
   `docs/`, `test/`, `ci/`, `chore/`, `build/`), from an up-to-date `main`:
   `git fetch origin && git switch -c fix/<topic> origin/main`.
2. For parallel work, a worktree next to the checkout works too:
   `git worktree add ../django-db2-for-i-triggers-<topic> -b fix/<topic> origin/main`.
   Each worktree has its own nox virtualenvs (`scripts/nox_volume.sh`).
   **Never move, rename, copy, delete or link `.env`**; a worktree without it
   works offline only.

## change: the daily loop

1. Edit, then `bin/check` (what CI does: lint and the offline tests for every
   Python × Django combination). Faster for one combination:
   `bin/check --python 3.14 --django 6.1`.
2. In the container directly: `docker compose run --rm tests nox -s lint` or
   `nox -s "offline(3.14-django6.1)" -- -k <name>`.
3. Pinned tooling: after changing `[dependency-groups]` in `pyproject.toml`,
   `docker compose run --rm tests uv lock`.

## commit: signed commits and changelog fragments

1. Stage by explicit path, never `git add -A` or `git add .`.
2. Conventional commit messages: `feat(scope): ...`, `fix: ...`, `docs: ...`,
   `test: ...`, `build: ...`, `ci: ...`, `chore: ...`. One logical change per
   commit.
3. Every commit is signed (the repository's git config); `main` accepts only
   signed commits. Check with `git log --show-signature -1`.
4. A user-visible change gets a changelog fragment,
   `changelog.d/<topic>.<type>.md` (`added`, `changed`, `fixed`,
   `limitation`; see `changelog.d/README.md`). Once the pull request exists,
   rename it to `changelog.d/<PR>.<type>.md` and push.

## pr: pull requests

1. Before every push: `bin/check` passes (exit 0).
2. `git push -u origin <branch>`, then `gh pr create`. The description says
   what changed and how it was checked.
3. When the branch is behind `main`, rebase and `git push --force-with-lease`
   (pull request branches only; never `main`). Never use GitHub's "Update
   branch" button.
4. Never merge your own pull request; the maintainer reviews and merges.

## review: what the maintainer checks before merging

1. CI is green on the latest commit (`offline`).
2. Only what the description says; Django-version checks only in `compat.py`,
   no IBM i version checks (the backend's capabilities), no driver code.
3. Docs and a changelog fragment come with user-visible changes.
4. Merge with a merge commit (no squash, no rebase merge).

## probe: facts about IBM i

1. Never guess IBM i behaviour: a probe in `probes/` settles it, its finding
   goes to `docs/IBMI_NOTES.md`. First check the backend's
   `docs/IBMI_NOTES.md`: never repeat a probe it already ran.
2. `bin/probe --list` lists the probes. `bin/probe qtemp_<topic>` runs one
   that only reads or writes only in QTEMP; `bin/probe --approved <link>
   lib_<topic>` one that changes a library, only with the maintainer's
   approval comment on GitHub for that probe (dry run without `--execute`).
3. Every PUB400 run holds the lock shared with the backend
   (`~/.local/state/django-db2-for-i/pub400.lock`): one PUB400 job at a time
   on this machine; `--wait` queues behind a running one.
4. A result a decision rests on goes into the repository:
   `bin/probe --publish test-results/probes/<probe>-<utc>.json` writes
   `probes/results/<probe>.json` with host, user and library names replaced.

## troubleshooting: common problems

- **"PUB400 busy: <holder>"**: another PUB400 job (of either project) runs;
  wait, or add `--wait`. `bin/doctor` shows the holder.
- **`uv export --locked` fails**: `pyproject.toml` changed without `uv lock`.
- **An offline test fails with "offline tests must not open a database
  connection"**: the code under test connects; offline tests may not.
- **SQL0552 on `CREATE TRIGGER`**: the user lacks `*USE` on `QSYS/ADDPFTRG`
  (PUB400, `docs/IBMI_NOTES.md`).
