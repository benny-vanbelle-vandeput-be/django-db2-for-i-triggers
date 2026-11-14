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
