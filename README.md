# django-db2-for-i-triggers

Database triggers for Django models on **Db2 for IBM i**, declared in
`Meta.triggers` and installed with migrations, in the style of
[django-pgtrigger](https://django-pgtrigger.readthedocs.io/en/4.17.0/).
It works with the [django-db2-for-i](https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i)
database backend.

**Status:** phase 0, the skeleton: no triggers yet. The plan is in
[CLAUDE.md](CLAUDE.md), the feature mapping in
[docs/pgtrigger-mapping.md](docs/pgtrigger-mapping.md). PUB400 does not allow
`CREATE TRIGGER` for its users ([docs/IBMI_NOTES.md](docs/IBMI_NOTES.md)), so
for now there are only offline tests.

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) and the step-by-step
[docs/WORKFLOW.md](docs/WORKFLOW.md) (`bin/help`).

License: [BSD-3-Clause](LICENSE).
