# django-db2-for-i-triggers

Database triggers for Django models on **Db2 for IBM i**, declared in
`Meta.triggers` and installed with migrations, in the style of
[django-pgtrigger](https://django-pgtrigger.readthedocs.io/en/4.17.0/).
It works with the [django-db2-for-i](https://github.com/benny-vanbelle-vandeput-be/django-db2-for-i)
database backend.

**Status:** phase 1, pre-alpha: triggers can be declared and their SQL is
built and checked offline; installing them comes next. The plan is in
[CLAUDE.md](CLAUDE.md), the feature mapping in
[docs/pgtrigger-mapping.md](docs/pgtrigger-mapping.md). PUB400 does not allow
`CREATE TRIGGER` for its users ([docs/IBMI_NOTES.md](docs/IBMI_NOTES.md)), so
for now there are only offline tests.

## Based on django-pgtrigger

This library follows the public API of
[django-pgtrigger](https://github.com/Opus10/django-pgtrigger) 4.17.0, so that
Django models and their triggers can be written once and run on PostgreSQL
(with django-pgtrigger) and on Db2 for IBM i (with this library), as
database-independently as the two databases allow. What Db2 for i cannot do is
refused with an explanation, never emulated. It is not affiliated with or
endorsed by django-pgtrigger; adapted parts keep its BSD-3-Clause notice
([NOTICE](NOTICE)).

User documentation: [Installation](docs/user/Installation.md),
[Usage](docs/user/Usage.md), [Known limitations](docs/user/Known-Limitations.md).

Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) and the step-by-step
[docs/WORKFLOW.md](docs/WORKFLOW.md) (`bin/help`).

License: [BSD-3-Clause](LICENSE).
