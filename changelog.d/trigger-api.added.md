- Triggers in `Meta.triggers`, with django-pgtrigger's API: `Trigger`
  (`when=Before/After`, `operation=Insert/Update/Delete/UpdateOf(...)`
  combined with `|`, `condition=Condition(...)`, `func=` / `Func(...)`,
  `declare=`), `Protect` and `ReadOnly(fields=/exclude=)`. Their
  `CREATE TRIGGER` SQL is built and checked offline; installing them comes
  in a later release.
- `system_name=` on every trigger: the IBM i system name of its program
  (`PROGRAM NAME`).
- System checks `django_db2_for_i_triggers.E001` to `E005`.
