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
