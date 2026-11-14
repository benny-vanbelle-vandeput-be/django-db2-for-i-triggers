# django-pgtrigger 4.17 → Db2 for i

Every feature of django-pgtrigger 4.17
(<https://django-pgtrigger.readthedocs.io/en/4.17.0/>) and what it becomes here.
**Nothing in the "Db2 for i" column is a fact until a probe shows it**: the
status says which probe settles it. Update this file as the probes report
(link the `docs/IBMI_NOTES.md` section), and keep it in the order of work.

Status: **to probe** (unknown), **planned** (probe done, works), **limited**
(works with a documented difference), **not supported** (`NotSupportedError`,
documented), **n/a** (PostgreSQL only).

## Declaring and installing

| pgtrigger | What it does on PostgreSQL | Db2 for i | Status |
|---|---|---|---|
| `Meta.triggers = [...]` | triggers declared on the model | the same | planned (phase 1) |
| `pgtrigger.Trigger(name=, when=, operation=, level=, func=, condition=)` | a trigger function plus a trigger | one `CREATE TRIGGER` with the body in SQL PL; no separate function | to probe (`qtemp_create_trigger`) |
| `when=Before / After` | `BEFORE` / `AFTER` | `BEFORE` / `AFTER` | to probe |
| `when=InsteadOf` | `INSTEAD OF` on views | `INSTEAD OF` on views | to probe (phase 4) |
| `operation=Insert / Update / Delete` and `|` | the events, combined | `INSERT OR UPDATE OR DELETE` | to probe |
| `operation=UpdateOf("field")` | `UPDATE OF col` | `UPDATE OF col` | to probe |
| `operation=Truncate` | `TRUNCATE` trigger | Db2 for i `TRUNCATE` does not fire delete triggers unless `RESTRICT WHEN DELETE TRIGGERS`; no truncate event | to probe, likely not supported |
| `level=Row / Statement` | `FOR EACH ROW / STATEMENT` | `FOR EACH ROW`, `FOR EACH STATEMENT` (`REFERENCING OLD TABLE / NEW TABLE`) | to probe |
| `timing=Immediate / Deferred` (deferrable triggers) | constraint triggers, deferred to commit | none expected | to probe, likely not supported |
| `func=` / `pgtrigger.Func` with `{meta}`, `{fields}`, `{columns}` | the function body, templated | the trigger body, templated the same way | planned (phase 1) |
| `declare=` | variables in the function | `DECLARE` in the body | to probe |
| installation through migrations | `makemigrations` / `migrate` | the same (`AddTrigger`, `RemoveTrigger`) | planned (phase 3) |
| `PGTRIGGER_INSTALL_ON_MIGRATE`, `PGTRIGGER_MIGRATIONS`, `PGTRIGGER_MODEL_META` and the other settings | settings | the same names with `DB2ITRIGGER_` | planned |
| the trigger name `pgtrigger_<name>_<hash>` | unique name, hash for outdated detection | name plus a hash; where the hash is stored is open (`COMMENT ON TRIGGER`, `LABEL ON TRIGGER`, `SYSTRIGGERS` columns) | to probe |
| schemas (`search_path`) | the trigger in the table's schema | the trigger in the table's library; the trigger program's library and system name | to probe |

## Conditions

| pgtrigger | Db2 for i | Status |
|---|---|---|
| `pgtrigger.Q(old__field=..., new__field=...)` | `WHEN (O.FIELD = ... AND N.FIELD = ...)` | to probe (`WHEN` syntax and limits) |
| `pgtrigger.F("old__field")` | a column of the old or new row | to probe |
| `__df` (is distinct from) lookups | `IS DISTINCT FROM` | to probe |
| `AnyChange`, `AnyDontChange`, `AllChange`, `AllDontChange` | conditions over many columns | to probe (LOB columns may not be compared) |
| `pgtrigger.Condition("raw SQL")` | raw `WHEN` | planned |
| conditions on statement-level triggers | PostgreSQL refuses them | to probe |

## Trigger classes (`contrib`)

| pgtrigger | Db2 for i | Status |
|---|---|---|
| `Protect` | `SIGNAL SQLSTATE '7xxxx' SET MESSAGE_TEXT = ...` in a `BEFORE` trigger; which Python exception it becomes depends on the backend's error mapping | to probe |
| `ReadOnly(fields= / exclude=)` | `Protect` on update with a change condition | to probe |
| `SoftDelete(field=, value=)` | a `BEFORE DELETE` cannot cancel the delete without an error; PostgreSQL returns `NULL`. Options: an `INSTEAD OF` trigger on a view, or an error plus `UPDATE` | to probe, likely limited |
| `FSM(field=, transitions=)` | `Protect` with a condition over old and new | to probe |
| `UpdateSearchVector` | PostgreSQL full-text search | n/a |
| `Composer` | several actions in one trigger | to probe |

## Runtime

| pgtrigger | Db2 for i | Status |
|---|---|---|
| `pgtrigger.ignore("app.Model:name")` | PostgreSQL: a session setting read by the function. Db2 for i candidates: a global variable (`CREATE VARIABLE`, an object in a library: `lib_` probe), the client special registers (`SYSPROC.WLM_SET_CLIENT_INFO`, `CURRENT CLIENT_APPLNAME`), a QTEMP table | to probe |
| `pgtrigger.schema()` | PostgreSQL search path | n/a (libraries are fixed per model) |
| enable / disable (`pgtrigger.enable / disable`) | `ALTER TABLE ... ENABLE/DISABLE TRIGGER` | `ALTER TRIGGER ... ENABLE / DISABLE` or `CHGPFTRG` | to probe |
| `pgtrigger.install / uninstall / prune` | the Python API | the same | planned (phase 1, 5) |

## Commands

| pgtrigger | Db2 for i | Status |
|---|---|---|
| `manage.py pgtrigger ls` (installed, outdated, orphaned, disabled) | `manage.py db2itrigger ls`, from `QSYS2.SYSTRIGGERS` | to probe (the catalog columns) |
| `install`, `uninstall`, `enable`, `disable`, `prune` | the same subcommands | planned |

## Database setups

| pgtrigger | Db2 for i | Status |
|---|---|---|
| multiple databases (`using`, routers) | the same, per library | planned (phase 5) |
| multiple schemas | models in another library (`Meta.db_library` of the backend) | to probe (phase 5) |
| partitioned tables | Db2 for i partitioned tables (DB2 Multisystem) | out of scope at first |

## Db2 for i specifics to settle in phase 0

- Who may create triggers: SQL0552 on PUB400 in the user library (backend
  `IBMI_NOTES.md`); the authority needed (`ADDPFTRG`, `*ALTER`, `*OBJMGT`).
- The trigger program: an SQL trigger is a `*PGM` object; its library and its
  system name; what `DROP TABLE` and `RENAME TABLE` do to it.
- The limits: triggers per table, per event; the size of the body.
- Commitment control: a trigger's changes run in the caller's unit of work;
  what a `SIGNAL` does to it; journaling of the tables a trigger writes.
- `MODE DB2ROW` (the IBM i default, fires per row as it is processed) or
  `MODE DB2SQL` (after all rows): which one matches PostgreSQL's row triggers.
- The catalog: `QSYS2.SYSTRIGGERS`, `SYSTRIGCOL`, `SYSTRIGDEP`, `SYSTRIGUPD`
  (which columns exist on 7.5).
