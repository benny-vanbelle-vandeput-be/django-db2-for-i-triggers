# django-db2-for-i-triggers — database triggers for Django models on Db2 for IBM i

## 1. Goal

A Django library that declares, installs and manages **Db2 for i triggers** from
Django models, the way [django-pgtrigger](https://django-pgtrigger.readthedocs.io/en/4.17.0/)
does it for PostgreSQL:

```python
import db2itrigger

class Order(models.Model):
    status = models.CharField(max_length=10)

    class Meta:
        triggers = [
            db2itrigger.Protect(name="protect_deletes", operation=db2itrigger.Delete),
            db2itrigger.ReadOnly(name="status_read_only", fields=["status"]),
        ]
```

- `makemigrations` and `migrate` install, change and remove the triggers like
  other database objects.
- The **public API follows django-pgtrigger** (class names, arguments, conditions,
  `Meta.triggers`, the management command, `ignore()`), so a project can move
  from PostgreSQL to Db2 for i with as few changes as possible. Where Db2 for i
  cannot do what PostgreSQL does, the library raises `NotSupportedError` with
  the reason, and `docs/user/Known-Limitations.md` says so. The mapping, item by
  item, is in [docs/pgtrigger-mapping.md](docs/pgtrigger-mapping.md).
- It works only with the backend of the sister project
  [django-db2-for-i](../django-db2-for-i) (`ENGINE = "django_db2_for_i"`); other
  engines are refused with a system check error.
- Names (proposal, the maintainer confirms in phase 0): distribution
  `django-db2-for-i-triggers`, import package `db2itrigger` (as `pgtrigger`),
  app label `db2itrigger`, management command `manage.py db2itrigger`.

### Relation to django-pgtrigger
- django-pgtrigger is BSD-3-Clause (verify the exact license and copyright
  holder in phase 0, from its repository). Read it freely for the API, the
  behaviour and its tests. Prefer writing the code anew for Db2 for i; where
  code or tests are adapted from it, keep its copyright notice in that file and
  name it in `NOTICE`.
- Its tests are the model for ours: port the test cases (the behaviour they
  check), not the PostgreSQL SQL.

### Relation to django-db2-for-i (the backend)
- A runtime dependency, pinned to a released tag (`v0.1.0b4` or later), not
  PyPI (the backend is on GitHub only for now).
- Never change the backend from this repository. A backend change this library
  needs (a capability, a hook in the schema editor, an error mapping) is an
  issue or pull request in the backend's repository, with its own process.
- Reuse the backend's facts: its `docs/IBMI_NOTES.md` (journaling, commitment
  control, CPA32B2, SQL0910, system names, PUB400's limits) is the reference.
  Never repeat a probe that the backend already ran; link to its result.

### License
- **BSD-3-Clause**, copyright **Benny Van Belle** (`LICENSE`, as the backend).
- `pyproject.toml`: `license = "BSD-3-Clause"`, `license-files = ["LICENSE"]`
  (plus `NOTICE` if code is adapted from django-pgtrigger).

## 2. Working rules (read first)

These are the backend's rules, unchanged unless stated. In phase 0 they are
written into this repository's `CONTRIBUTING.md` and `docs/WORKFLOW.md`, which
this file then imports (`@CONTRIBUTING.md`, `@docs/WORKFLOW.md`), as the
backend's CLAUDE.md does.

### Process
- **Plan before code.** For every phase: propose a plan, wait for approval,
  then implement.
- **Small, reviewable commits.** One logical change per commit; conventional
  commit messages (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`).
- **Never guess IBM i behaviour.** When uncertain, write a tiny probe in
  `probes/`, run it, and record the finding in `docs/IBMI_NOTES.md`.
- Record non-obvious design decisions in `docs/DECISIONS.md` (date, decision,
  why, alternatives).
- Never mark a test as skipped or expected failure without a one-line reason.
- All code, comments and docs in English.

### Talking with the maintainer
- The maintainer is Benny Van Belle (GitHub `benny-vanbelle-vandeput-be`).
  Answer in **Dutch**, in plain language; code, docs and GitHub texts stay
  English.
- Ask clarifying questions **one at a time**, not as a list.
- When the maintainer is away, questions and approvals go through **GitHub
  issues**; they answer and merge remotely.
- During long runs (PUB400 runs, long work): a short status with an ETA every
  15 minutes.

### Credentials and `.env`
- No credentials in the repo, the image, logs or issues. Connection settings
  come from environment variables / `.env` (gitignored, with `.env.example`).
- **Never read, print, log or echo `.env` or its values**; scripts load it
  themselves. Never move, rename, copy, delete or re-link `.env` or its
  symlink. Never cat settings or credential files (key names only, with `jq`).
  `.claude/settings.json` denies the commands for it.
- `bin/setup` is for humans in their own terminal; Claude never runs it
  interactively and never enters values.
- `.env` holds the **same** IBM i user and the **same two libraries** as the
  backend's `.env` (the PUB400 user has only two). The maintainer writes it
  with `bin/setup`; Claude never copies the backend's `.env`.

### PUB400 (shared community IBM i 7.5)
- Never the full Django suite; `--parallel=1`; one connection per run; no
  retry storms; fail fast when the system is unreachable.
- **One PUB400 job at a time on this machine, across both projects.** Every
  PUB400 run goes through `scripts/pub400.sh` and the **same lock file as the
  backend**: `~/.local/state/django-db2-for-i/pub400.lock`
  (`scripts/pub400_lock.py`, copied unchanged from the backend). A run of
  either project waits for (`--wait`) or refuses while the other holds it.
- The test libraries are shared with the backend's runs: use the same marker
  table (`DJDB2I_TEST_MARKER`) and the same created-objects list
  (`~/.local/state/django-db2-for-i/created-objects.txt`), so that
  `bin/ibmi-cleanup` of either project can drop what a crashed run of the
  other left. Never drop a table that is not on that list.
- **Probes are read-only by default.** `probes/qtemp_<topic>.py` only reads,
  or writes only in QTEMP (job-scoped, gone when the job ends): no approval
  needed. `probes/lib_<topic>.py` creates or changes anything outside QTEMP:
  **only with the maintainer's approval comment on GitHub, for that probe**,
  checked by `bin/probe --approved <comment link>` (dry run included). A
  session answer is not enough.
- **Known blocker:** the backend found that `CREATE TRIGGER` is not allowed for
  the PUB400 user in the user library (SQL0552, backend `docs/IBMI_NOTES.md`,
  the `lib_column_copy` notes, 2026-11-13). Phase 0 must find out whether it
  works in QTEMP and what authority it needs, **before** any other work: see
  section 9.

### Git and GitHub
- Claude works on GitHub only as the machine account `claude-v-belle-net`
  (`GH_TOKEN`), never with the maintainer's account.
- Commits: author the maintainer (noreply address), committer the machine
  account (noreply address), every commit signed with the machine account's
  SSH key (the repository's local git config, as in the backend). Stage by
  explicit path, never `git add -A` or `git add .`.
- End commit messages with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and pull request
  bodies with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- `main` is protected: pull requests only, one approval by the maintainer,
  merge commits only, signed commits. Never push to `main`, never force-push it.
- One branch per change, `<type>/<topic>` from the current `origin/main`. Push
  early as a draft pull request; ready for review only after its IBM i run.
- `bin/check` passes before every push (exit 0, or 3 = only the verification
  gate); push only inside an `if` on its exit code. Rebase onto `origin/main`
  first, then one `bin/check`.
- Claude never merges, never creates, moves or deletes tags or releases, and
  never triggers the IBM i gate's `workflow_dispatch`.
- `gh pr edit` fails for the machine account; use `gh api -X PATCH`.
- After `gh pr create`, rename the changelog fragment to `<PR>.<type>.md`.

## 3. Supported versions

The same as the backend, and they move with it:
- **Django** 5.2 LTS, 6.0, 6.1 (6.2 LTS when the backend adds it).
- **Python** 3.12, 3.13, 3.14, and 3.15 with Django 6.1 only.
- **IBM i** 7.5 and later (the backend's minimum). Trigger features that depend
  on the release or the Db2 PTF Group go through the backend's capabilities
  (`connection.capabilities`), never through version checks here.

## 4. Architecture

```
db2itrigger/
├── __init__.py        # the public API, as pgtrigger's: Trigger, Protect, ReadOnly,
│                      # SoftDelete, FSM, Composer, Q, F, Condition, Before, After,
│                      # InsteadOf, Insert, Update, Delete, Row, Statement, ignore, ...
├── core.py            # Trigger: its SQL (CREATE TRIGGER), its name and hash
├── conditions.py      # Q / F / Condition -> a WHEN clause on OLD / NEW
├── contrib.py         # Protect, ReadOnly, SoftDelete, FSM, Composer
├── installation.py    # install / uninstall / enable / disable / prune, in a library
├── introspection.py   # installed triggers from QSYS2.SYSTRIGGERS (and SYSTRIGCOL, SYSTRIGDEP)
├── migrations.py      # AddTrigger / RemoveTrigger and the autodetector hook
├── runtime.py         # ignore(): skipping triggers for one block of code
├── management/commands/db2itrigger.py
├── checks.py          # system checks (ENGINE, names, unsupported options)
├── compat.py          # the Django-version axis (no django.VERSION checks elsewhere)
└── apps.py
```

Rules:
- No `django.VERSION` checks outside `compat.py`.
- No IBM i version checks here at all: ask the backend's capabilities.
- No driver-specific code: everything goes through Django's connection and the
  backend's error mapping.
- SQL is built in one place per statement (`core.py` for `CREATE TRIGGER`),
  with quoting from the backend (`connection.ops.quote_name`), so goldens can
  check it.
- A trigger has a stable **hash** of its definition; the installed trigger
  carries it (where Db2 for i can store it: a `COMMENT ON TRIGGER` / `LABEL`,
  to probe) so `db2itrigger ls` can tell installed, outdated and orphaned
  triggers apart, as pgtrigger does.
- Trigger names: Db2 for i SQL names (up to 128) plus a system name (10
  characters) for the trigger program; how the system name is chosen and
  kept unique is decided after the phase 0 probes (the backend's system-name
  work, #253, is the reference).

## 5. Feature strategy

- Start with the smallest useful slice: `Trigger` with raw SQL, `Protect`,
  `ReadOnly`, installed through migrations. Add the rest one item at a time,
  in the order of [docs/pgtrigger-mapping.md](docs/pgtrigger-mapping.md).
- Each item comes with: the implementation, offline tests (golden SQL), IBM i
  tests (the trigger fires, or refuses, as documented), the pgtrigger test cases
  ported, user docs, and a changelog fragment (`changelog.d/`).
- What Db2 for i cannot do (for example deferrable triggers) is refused with
  `NotSupportedError` and documented; never emulated silently.

## 6. Test tiers

Named as in the backend (CONTRIBUTING.md, "Test sets"):

- **Offline tests** (no IBM i, CI on every commit): the generated SQL of every
  trigger class and condition against **golden files** in
  `tests/offline/golden/`, each with a verification stamp (`-- verified:`), the
  migration operations and autodetector, the checks. A fixture fails loudly if
  a connection is opened.
- **IBM i tests** (`tests/ibmi/`): install the triggers in a marked test library
  and check that they fire: a protected delete fails with the documented error,
  a read-only field cannot change, a soft delete sets the field, `ignore()`
  skips, the migration installs and removes them. Executes every golden once
  (verification stamps). Only on a system where `CREATE TRIGGER` is allowed
  (section 9, phase 0).
- **No Django suite tier**: Django's own tests do not cover triggers. Instead,
  pgtrigger's test cases are ported into the IBM i tests.
- The IBM i gate, the PR classification and the labels (`run-ibmi`,
  `needs-full-ibmi-run`) work as in the backend, with this repository's paths.

Version matrix: offline on every Python × Django combination; IBM i tests on the
newest Python × newest Django during development, every Django version before a
release.

## 7. Containerized environment

As the backend: all runs in a container (`docker/Dockerfile` with the targets
`offline` and `full`, the IBM i Access ODBC Driver installed from IBM's
repository in `full`, `uv`, `nox`), `compose.yaml` with a project name of its
own, `.devcontainer/`, volumes for `test-results/` and the `uv` cache, and one
entry point: `docker compose run --rm tests nox -s <session>`. The image is built
locally and never pushed to a public registry (IBM's license). The backend is
installed from its git tag in the image's test environment (or from the sibling
checkout `../django-db2-for-i` in editable mode, an option of `bin/setup`).

## 8. Directory structure (target)

```
django-db2-for-i-triggers/
├── CLAUDE.md, README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE, NOTICE (if needed)
├── pyproject.toml, uv.lock, noxfile.py, compose.yaml, .env.example
├── .claude/settings.json      # the deny rules (copied from the backend)
├── .devcontainer/, .github/workflows/ (offline CI, classify, ibmi-gate, wiki)
├── bin/                       # check, doctor, help, ibmi-test, ibmi-cleanup, probe,
│                              # setup, status, verify, release-prepare, worktree-remove
├── changelog.d/
├── docker/
├── docs/
│   ├── user/                  # Installation, Usage, Conditions, Ignoring triggers,
│   │                          # Migrations, Commands, Known-Limitations, Troubleshooting
│   ├── pgtrigger-mapping.md   # every pgtrigger feature and its Db2 for i status
│   ├── DECISIONS.md, IBMI_NOTES.md, TEST_STATUS.md, WORKFLOW.md, status.toml
│   └── phases/
├── db2itrigger/
├── probes/                    # qtemp_* and lib_* probes; results/
├── scripts/                   # pub400.sh, pub400_lock.py (unchanged), classify_pr.py, ...
└── tests/ (offline/, ibmi/, testapp/, django_settings/)
```

Copy the tooling from `../django-db2-for-i` and cut it down: keep what this
project needs (`pub400.sh` and the lock, the probe approval check, `bin/check`,
the golden files with their stamps and gate, the classification and the IBM i
gate, changelog fragments, `bin/ibmi-cleanup`), leave out what only a backend
needs (the Django suite runner, the replay tests, the status run per Django
module).

## 9. Phases

0. **Skeleton, probes and the blocker.**
   1. First, before anything else: `probes/qtemp_create_trigger.py` on PUB400:
      can the PUB400 user `CREATE TRIGGER` on a table in QTEMP (a `BEFORE` and
      an `AFTER` trigger, `FOR EACH ROW`, `REFERENCING OLD AS O NEW AS N`, a
      `WHEN`, a `SIGNAL SQLSTATE`)? Which SQLCODE, and which authority is
      missing if not (`ADDPFTRG`, `*ALTER` on the file, the trigger program's
      library)? Report to the maintainer before going on: if triggers cannot
      be created on PUB400 at all, the IBM i tests need another system, or the
      PUB400 admins' help, and the maintainer decides how to continue.
   2. The repository skeleton (section 8), CONTRIBUTING.md and WORKFLOW.md
      adapted from the backend, the GitHub repository (the maintainer creates
      it; Claude never creates repositories), CI with the offline tier.
   3. QTEMP probes for the open points of docs/pgtrigger-mapping.md (catalog
      columns, `ALTER TRIGGER` enable/disable, storing the hash, statement-level
      triggers, `INSTEAD OF` on views, `IS DISTINCT FROM` in `WHEN`, how a
      `SIGNAL` reaches Django through the backend's error mapping, the ways to
      pass an "ignore" flag into a trigger).
1. **Trigger core.** `Trigger` with raw SQL, `Before`/`After`, `Insert`/`Update`/
   `Delete`, `Row`; install and uninstall; `Protect` and `ReadOnly`;
   introspection; the `db2itrigger ls / install / uninstall` command.
2. **Conditions.** `Q`, `F` on `old__` / `new__`, `Condition` with raw SQL,
   `UpdateOf` / `AnyChange` / `AnyDontChange` (as far as Db2 for i allows).
3. **Migrations.** `Meta.triggers` in migrations (`AddTrigger`,
   `RemoveTrigger`, changes as remove + add), the autodetector, `sqlmigrate`.
4. **More trigger classes.** `SoftDelete`, `FSM`, `Composer`, statement-level
   triggers, `INSTEAD OF` triggers on views (if the probes allow).
5. **Runtime.** `ignore()` (the mechanism chosen after the probes), enable /
   disable, `prune`, multi-database (the `other` library) and models in another
   library (`Meta.db_library` of the backend).
6. **Docs and release.** User docs, the Known Limitations, the README, the first
   alpha release on GitHub (the maintainer tags and releases).

## 10. Open questions for the maintainer

Ask one at a time, in Dutch, when the work reaches them:
1. The names: distribution `django-db2-for-i-triggers`, package `db2itrigger`?
2. The GitHub repository: name and owner (the maintainer creates it), and the
   machine account's access to it.
3. If PUB400 does not allow `CREATE TRIGGER`: which system for the IBM i tests?
4. Which pgtrigger features matter most for the first release (the order of
   phases 1–5)?
