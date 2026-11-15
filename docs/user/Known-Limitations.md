# Known limitations

## Not yet run on IBM i

The `CREATE TRIGGER` statements this library builds have **not run on an
IBM i yet**: the test system (PUB400) does not allow `CREATE TRIGGER` for its
users ([IBM i notes](../IBMI_NOTES.md)). They follow IBM's `CREATE TRIGGER`
documentation for IBM i 7.5, and every golden file in
`tests/offline/golden/` says `-- verified: no` until it ran. Open points that
only a run on IBM i can settle:

- `OLD` and `NEW` as the correlation names (`REFERENCING OLD ROW AS OLD NEW ROW
  AS NEW`), and both declared for every event;
- `PROGRAM NAME` for the trigger program's system name;
- `IS DISTINCT FROM` in a trigger's `WHEN`, in particular on LOB columns
  (`TextField`, `BinaryField`), which `ReadOnly` compares when it protects
  every field;
- which Python exception the `SIGNAL SQLSTATE '75001'` of `Protect` becomes
  through the backend's error mapping.

## Refused

These raise `NotSupportedError` when the trigger is declared:

| What | Why |
|---|---|
| `operation=Truncate` | Db2 for i has no truncate trigger event |
| `timing=Immediate` / `Deferred` | Db2 for i has no triggers deferred to the commit |
| `level=Statement` | not supported yet (phase 4) |
| `when=InsteadOf` | not supported yet (phase 4) |

## Not available yet

Installing triggers (migrations, `install`, `uninstall`), the management
command, `ignore()`, enable and disable, the conditions `Q`, `F`,
`AnyChange` and the others, and `SoftDelete`, `FSM`, `Composer`. The order is
in [docs/pgtrigger-mapping.md](../pgtrigger-mapping.md).
