# Usage: declaring triggers on a model

## Based on django-pgtrigger

This library follows the public API of
[django-pgtrigger](https://django-pgtrigger.readthedocs.io/en/4.17.0/)
(version 4.17.0): the same class names, arguments and `Meta.triggers`. The aim
is that a model and its triggers are written once and work on PostgreSQL with
django-pgtrigger and on Db2 for IBM i with this library, with as few changes
as possible. Where Db2 for i cannot do what PostgreSQL does, the library
refuses it with `NotSupportedError` and says why; it never does something
else silently. The differences are listed [below](#differences-from-django-pgtrigger)
and in the [Known limitations](Known-Limitations.md).

This project is not affiliated with or endorsed by django-pgtrigger or its
authors; the parts adapted from it keep its BSD-3-Clause notice (`NOTICE`).

## A first example

```python
from django.db import models

import django_db2_for_i_triggers as triggers


class Order(models.Model):
    status = models.CharField(max_length=10)
    amount = models.DecimalField(max_digits=9, decimal_places=2)

    class Meta:
        triggers = [
            # Rows of this table cannot be deleted.
            triggers.Protect(name="protect_deletes", operation=triggers.Delete),
            # The status cannot change once a row exists.
            triggers.ReadOnly(name="status_read_only", fields=["status"]),
        ]
```

With django-pgtrigger the same model reads `import pgtrigger` and
`pgtrigger.Protect(...)`; a project that runs on both can import one of the two
under a common name:

```python
try:
    import django_db2_for_i_triggers as triggers
except ImportError:
    import pgtrigger as triggers
```

## Protect

`Protect(name=, operation=, condition=, system_name=)` refuses an operation
with an error. It is a `BEFORE ... FOR EACH ROW` trigger that runs
`SIGNAL SQLSTATE '75001'` with the message
`django_db2_for_i_triggers: Cannot <operation> rows from <table> table`.

```python
triggers.Protect(name="no_deletes", operation=triggers.Delete)
triggers.Protect(name="frozen", operation=triggers.Update | triggers.Delete)
triggers.Protect(
    name="no_paid_deletes",
    operation=triggers.Delete,
    condition=triggers.Condition("OLD.STATUS = 'paid'"),
)
```

## ReadOnly

`ReadOnly(name=, fields=, exclude=, condition=, system_name=)` refuses an
`UPDATE` that changes the protected fields:

- `fields=["status", "amount"]`: only these fields;
- `exclude=["note"]`: every field except these;
- neither: every field.

It compares the old and the new value with `IS DISTINCT FROM`, so a change
from or to `NULL` counts as a change.

## Trigger: your own SQL

`Trigger(name=, when=, operation=, level=, condition=, func=, declare=, system_name=)`
runs your own SQL. The body (`func`) is **Db2 for i SQL PL**, the statements
between `BEGIN ATOMIC` and `END`, each ending with `;`. The old and new row are
`OLD` and `NEW`, as in PostgreSQL.

```python
triggers.Trigger(
    name="double_total",
    when=triggers.Before,
    operation=triggers.Insert | triggers.UpdateOf("amount"),
    condition=triggers.Condition("NEW.AMOUNT > 0"),
    declare=[("factor", "INTEGER")],
    func=triggers.Func("SET factor = 2; SET NEW.{columns.total} = NEW.{columns.amount} * factor;"),
)
```

- `when`: `Before` or `After`.
- `operation`: `Insert`, `Update`, `Delete` or `UpdateOf("column", ...)`,
  combined with `|`.
- `level`: `Row` (the default).
- `condition`: `Condition("raw SQL")`, the trigger's `WHEN`; it only fires when
  the condition is true.
- `declare`: `[(name, type), ...]`, written as `DECLARE name type;` at the
  start of the body.
- `func`: the body as a string, or `Func(...)` with `{meta}` (the model's
  `_meta`), `{fields}` and `{columns}` (by field name) filled in. Column names
  are inserted as they are, without quotes.

## IBM i system name: `system_name`

Every trigger accepts `system_name=`: the IBM i system name of its trigger
program, at most 10 characters, letters, digits or `_`, starting with a
letter. It is written as `PROGRAM NAME <name>` in `CREATE TRIGGER`. Without
it, Db2 for i chooses a name. Set it when operators work with the program in
CL commands (`WRKPGM`, `DSPPGM`) or when the name must stay the same across
installations.

```python
triggers.Protect(name="protect_deletes", operation=triggers.Delete, system_name="ORDNODEL")
```

This argument does not exist in django-pgtrigger; leave it out in code that
must run there too, or pass it only on Db2 for i.

## The trigger's SQL name

The trigger is created as `DJTRG_<NAME>_<HASH>` in the table's library, where
`<HASH>` is five characters of a hash of `<app>.<Model>:<name>` (pgtrigger:
`pgtrigger_<name>_<hash>`). Names have at most 116 characters: letters, digits,
`-` and `_`.

## System checks

`manage.py check` reports, without connecting:

| Id | Problem |
|---|---|
| `django_db2_for_i_triggers.E001` | models declare triggers, but no database uses `ENGINE = "django_db2_for_i"` |
| `E002` | `Meta.triggers` is not a list of triggers |
| `E003` | two triggers of one model have the same name |
| `E004` | two triggers have the same `system_name` |
| `E005` | a trigger's SQL cannot be built (for example a `ReadOnly` field that does not exist) |

## Differences from django-pgtrigger

| django-pgtrigger | Here |
|---|---|
| `func` in PL/pgSQL (`RAISE EXCEPTION`, `RETURN NEW`) | `func` in Db2 for i SQL PL (`SIGNAL SQLSTATE`, `SET NEW.x = ...`); no `RETURN` |
| `Protect` raises with `RAISE EXCEPTION` | `SIGNAL SQLSTATE '75001'`; the Python exception it becomes is not settled yet |
| `level=Statement`, `Referencing` | not supported yet (`NotSupportedError`) |
| `when=InsteadOf` | not supported yet (`NotSupportedError`) |
| `operation=Truncate` | not supported: Db2 for i has no truncate trigger event |
| `timing=Immediate/Deferred` | not supported: Db2 for i has no deferred triggers |
| `Q`, `F`, `AnyChange`, ... | not yet (phase 2); use `Condition("raw SQL")` |
| `SoftDelete`, `FSM`, `Composer` | not yet (phase 4) |
| installation, migrations, `ignore()`, the management command | not yet (phases 3 and 5) |
| — | `system_name=` for the IBM i program name |
