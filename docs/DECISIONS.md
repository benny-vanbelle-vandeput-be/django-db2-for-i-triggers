# Design decisions

Non-obvious decisions, newest last: date, decision, why, alternatives.

## 2026-11-15: the names

**Decision.** The distribution is `django-db2-for-i-triggers`; the import
package, the app label and the management command are all
`django_db2_for_i_triggers` (`import django_db2_for_i_triggers`,
`INSTALLED_APPS = [..., "django_db2_for_i_triggers"]`,
`manage.py django_db2_for_i_triggers ls`).

**Why.** The maintainer's choice (open question 1 of CLAUDE.md): one name
everywhere, the same as the distribution, with no short alias to learn. It
follows the backend, whose package is `django_db2_for_i`.

**Alternatives.** `db2itrigger` for the package, app label and command (the
proposal in CLAUDE.md, after `pgtrigger`): shorter in `Meta.triggers`, but a
second name next to the distribution's. `db2i_trigger`, and a short command
name (`db2i_triggers`) next to the long package name.

**Open.** The prefix of the settings (pgtrigger: `PGTRIGGER_*`) is asked in
phase 1, when the first setting is added.

## 2026-11-15: the probe tooling before the skeleton

**Decision.** The first pull request brings only what one QTEMP probe needs:
the container (`docker/`, `compose.yaml`), the nox sessions `probe_qtemp` and
`probe_lib`, `scripts/pub400.sh` with the backend's lock
(`scripts/pub400_lock.py`, unchanged), `bin/probe`, `bin/setup` and
`probes/_common.py`. The package skeleton, the offline tests and CI follow in
the next pull request.

**Why.** CLAUDE.md puts the `CREATE TRIGGER` probe before anything else: if
PUB400 refuses triggers in QTEMP too, the IBM i tests need another system and
the plan may change. The probe must still run through the shared PUB400 lock
and the container, so that much tooling comes first.

**Alternatives.** Running the probe from the backend's checkout (changes the
backend's repository, which this project never does); the full skeleton first
(work that may need to change with the probe's answer).

**Details.** The PUB400 container keeps the backend's name prefix
(`db2i-pub400-`): `scripts/pub400_lock.py` stops and cleans up containers by
that prefix, so a run of either project also sees the other's containers. The
probes install only `pyodbc` (no `pyproject.toml` yet).
