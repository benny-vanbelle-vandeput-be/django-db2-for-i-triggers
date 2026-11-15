# Contributing

Thank you for your interest in django-db2-for-i-triggers. These rules follow
those of the backend, [django-db2-for-i](https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i),
cut down to what this project has today.

## License of contributions

This project is licensed under the [BSD 3-Clause License](LICENSE). By
submitting a contribution (pull request, patch, or any other form), you agree
that it is licensed under the same BSD 3-Clause License.

- Code or tests adapted from django-pgtrigger (BSD-3-Clause) keep its
  copyright notice in the file, and the project names it in `NOTICE`.
- Do not submit code copied from projects with an incompatible license.
- The IBM i Access ODBC Driver is not part of this project and must never be
  committed or redistributed.

## Ground rules

- No credentials in commits, logs, or issue reports. Connection settings come
  from environment variables or a local `.env` file (gitignored).
- One logical change per commit, with a
  [Conventional Commits](https://www.conventionalcommits.org/) message
  (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`).
- Claims about IBM i behaviour must be backed by a probe script in `probes/`
  and a note in `docs/IBMI_NOTES.md`; facts the backend already probed are
  linked, not probed again.
- Non-obvious design decisions go to `docs/DECISIONS.md` (date, decision,
  why, alternatives).
- Every test skip or expected failure carries a one-line reason.
- The backend is never changed from this repository: what this library needs
  from it is an issue or pull request there.
- On PUB400: one connection per run, `--parallel=1`, no retries, and one
  PUB400 job at a time on the machine, across this project and the backend
  (the shared lock, see below).

## Development environment

All development and test runs happen in a container
(`docker compose run --rm tests nox -s <session>`). The routine tasks have
scripts in `bin/`, run from the host; each has `--help` and `--dry-run` and
none prints secrets. The workflow, step by step, is in
[docs/WORKFLOW.md](docs/WORKFLOW.md) (`bin/help`, `bin/help <topic>`).

| Script | What it does |
|---|---|
| `bin/help` | the workflow guide: the quick start and the topics (`bin/help <topic>`) |
| `bin/setup` | first-time setup: the images and `.env` (asked in your own terminal) |
| `bin/doctor` | checks Docker, the driver in the image, `.env` and the PUB400 lock |
| `bin/check` | what CI does, locally: lint and the offline tests |
| `bin/probe` | IBM i probes: `qtemp_` probes (read-only or QTEMP); `lib_` probes only with `--approved <link>` to the maintainer's approval; `--publish` puts a result into the repository |

`bin/setup` is for humans in their own terminal: it asks for the `.env`
values (the password hidden) and writes them with mode 600; an existing
`.env` is never read or changed.

**One PUB400 job at a time on this machine**, across both projects. Every
PUB400 run goes through `scripts/pub400.sh`, which holds the backend's lock
(`scripts/pub400_lock.py`, copied unchanged:
`~/.local/state/django-db2-for-i/pub400.lock`). A second job stops with
"PUB400 busy: <holder>", or waits with `--wait`.

### Pinned tooling

The dev and test tooling (pytest, pytest-django, ruff) is pinned in
`uv.lock`; the nox sessions install exactly those versions.
`pyproject.toml` keeps open ranges in `[dependency-groups]`. The backend is
pinned to a git tag in `dependencies`; Django is not pinned: the sessions
install the newest release of each supported version. Dependabot
(`.github/dependabot.yml`) proposes tooling updates as pull requests.

## Test sets

Named as in the backend.

| Name | What it is | In the code |
|---|---|---|
| Offline tests | unit tests and (from phase 1) golden SQL checks; no IBM i, CI on every commit; a test that opens a connection fails | `nox -s offline`, `tests/offline/`, marker `offline` |
| IBM i tests | the triggers installed and fired on a real Db2 for i | not yet: PUB400 does not allow `CREATE TRIGGER` (docs/IBMI_NOTES.md) |

## Branches, commits and `main`

- `main` is protected by a ruleset: changes only through pull requests with
  one approval by the maintainer, merge commits only (no rebase or squash
  merging), signed commits required. Never push to `main` directly and never
  force-push it.
- One branch per logical change, named `<type>/<topic>`, created from the
  current `origin/main`.
- Before every push: `bin/check` passes.

## Changelog

Do not edit `CHANGELOG.md` in a pull request. Add a fragment instead, so
parallel pull requests do not conflict:

    changelog.d/<pull request number>.<type>.md

with `<type>` one of `added`, `changed`, `fixed`, `limitation`, and one entry
in Markdown (or several as `- ` items) as the content. Details in
[changelog.d/README.md](changelog.d/README.md);
`python3 scripts/assemble_changelog.py check` validates the fragments (the
offline tests run the same check) and `draft` shows the resulting section.
