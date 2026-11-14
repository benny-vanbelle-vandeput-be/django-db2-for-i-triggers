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
