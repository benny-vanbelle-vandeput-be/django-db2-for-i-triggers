# IBM i notes

Facts about Db2 for i that this library relies on, each from a probe (date,
system, probe file, published result in `probes/results/`). Never a guess.

The backend's [docs/IBMI_NOTES.md](https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i/blob/main/docs/IBMI_NOTES.md)
is the reference for everything that is not specific to triggers (journaling,
commitment control, CPA32B2, SQL0910, system names, PUB400's limits); this file
links to it rather than repeating it.

## Known from the backend

- `CREATE TRIGGER` is refused for the PUB400 user in the user library
  (SQL0552), backend `docs/IBMI_NOTES.md`, the `lib_column_copy` notes,
  2026-11-13.

## CREATE TRIGGER on PUB400, also in QTEMP (`probes/qtemp_create_trigger.py`)

PUB400 (IBM i 7.5), 2026-11-15, QTEMP only; published result
`probes/results/qtemp_create_trigger.json`.

- **`CREATE TRIGGER` is refused in QTEMP too**, on a table the user just
  created there: `SQL0552 - Not authorized to CREATE TRIGGER` (SQLSTATE
  `42000`, native error -552), for all four forms tried (a minimal `AFTER
  INSERT`; `AFTER INSERT` with `REFERENCING NEW`; `BEFORE UPDATE` with
  `REFERENCING OLD/NEW`, `WHEN` and `SIGNAL`; `BEFORE DELETE` with `SIGNAL`).
  The refusal is about the user, not the library or the table.
- SQL0552's second-level text (job log) names what is needed: "CREATE TRIGGER
  requires *USE authority to the ADDPFTRG command"; likewise "DROP TRIGGER
  requires *USE authority to the RMVPFTRG command" and "ALTER TRIGGER requires
  *USE authority to the CHGPFTRG command".
- `QSYS2.OBJECT_PRIVILEGES` shows `*PUBLIC *USE` on `QSYS/CHGPFTRG` and
  `QSYS/RMVPFTRG` to this user, and **no row at all for `QSYS/ADDPFTRG`**.
  That fits a missing `*USE` on `ADDPFTRG`; why the row is missing (excluded
  for `*PUBLIC`, or not visible to the user) the probe cannot tell.
- The user profile: class `*PGMR`, no special authorities, no group profile.
- QTEMP tables take no constraints (SQL7008, CPF32B0 on a `PRIMARY KEY`), as
  the backend's notes say; the probe's tables have none.
- Consequence: no trigger can be created, fired or seen in the catalog on
  PUB400 with this user. The IBM i tests need another system, or `*USE` on
  `QSYS/ADDPFTRG` (and the trigger work in a library) from the PUB400 admins.

## The authority on ADDPFTRG (`probes/qtemp_trigger_authority.py`)

PUB400 (IBM i 7.5), 2026-11-15, read-only; published result
`probes/results/qtemp_trigger_authority.json`. A follow-up to the SQL0552
above, after the maintainer's own checks showed `QSYS/ADDPFTRG` with `*PUBLIC
*EXCLUDE`, secured by the authorization list `TRIGGER`, whose `*PUBLIC` is
`*USE`.

- **The effective check refuses it:** `CHKOBJ OBJ(QSYS/ADDPFTRG) OBJTYPE(*CMD)
  AUT(*USE)` (through `QSYS2.QCMDEXC`) fails with `CPF9802 - Not authorized to
  object ADDPFTRG in QSYS`; the same check passes for `CHGPFTRG` and
  `RMVPFTRG`. `CHKOBJ` only checks; it changes nothing.
- The authorization list `TRIGGER` (owner `QSECOFR`) shows the user one entry:
  `*PUBLIC *USE` (`QSYS2.AUTHORIZATION_LIST_USER_INFO` and
  `OBJECT_PRIVILEGES`); the user is not on it by name, as far as the user can
  see.
- So the list's `*PUBLIC *USE` does not reach this user. That matches IBM i's
  authority checking, where an object's own `*PUBLIC` (here `*EXCLUDE`) is
  used unless it is `*AUTL`; the list then grants `ADDPFTRG` only to the
  profiles named on it. The `CHKOBJ` result is the fact; the rule is the
  explanation.
- `QSYS2.OBJECT_STATISTICS` has no column `AUTHORIZATION_LIST` on this
  release (SQL0206); the first query of the probe recorded that error.
- What would make triggers work on PUB400: the admins add the user to the
  authorization list `TRIGGER` (or grant `*USE` on `QSYS/ADDPFTRG`).

## From IBM's documentation, not yet run (CREATE TRIGGER, IBM i 7.5)

Not probed (no system allows `CREATE TRIGGER` yet); from IBM's `CREATE
TRIGGER` reference for 7.5, to confirm on IBM i:

- QTEMP cannot be the schema qualifier of a trigger: trigger probes need a
  library (`lib_` probes with the maintainer's approval).
- `PROGRAM NAME <name>` in the option list (before `WHEN`) names the trigger
  program; without it, a trigger name that is not a valid system name, or one
  whose program name exists, gets a generated system name.
- `OR REPLACE` is supported; `NOT SECURED` is the default; at most 300 triggers
  per table.
- `MODE DB2ROW` fires per row as it is processed, `MODE DB2SQL` (AFTER) after
  all rows.
- With several events, OLD is null for an insert and NEW for a delete; only one
  OLD and one NEW correlation name per trigger.
