"""nox sessions.

Run inside the container:  docker compose run --rm tests nox -s <session>

For now only the probe sessions (phase 0); the offline and IBM i test sessions
come with the package skeleton. Adapted from django-db2-for-i (noxfile.py).
"""

import pathlib
import re

import nox

nox.options.default_venv_backend = "uv"
nox.options.error_on_missing_interpreters = True
nox.options.sessions = []

# Python versions supported by each Django version, oldest first (the
# backend's docs/DJANGO_VERSIONS.md).
DJANGO_PYTHONS = {
    "5.2": ["3.12", "3.13", "3.14"],
    "6.0": ["3.12", "3.13", "3.14"],
    "6.1": ["3.12", "3.13", "3.14", "3.15"],
}
NEWEST_DJANGO = "6.1"
NEWEST_PYTHON = DJANGO_PYTHONS[NEWEST_DJANGO][-1]

# The probes talk to the driver directly; they need nothing else.
PROBE_REQUIREMENTS = ["pyodbc>=5.3"]


def _probe(session: nox.Session, prefix: str) -> tuple[str, list[str]]:
    """The probe named in the first argument (probes/<prefix>_<topic>.py) and the rest."""
    args = list(session.posargs)
    name = args.pop(0) if args else ""
    if (
        not re.fullmatch(rf"{prefix}_[a-z0-9_]+", name)
        or not pathlib.Path(f"probes/{name}.py").is_file()
    ):
        session.error(f"not a {prefix}_ probe: {name!r} (bin/probe --list)")
    return name, args


@nox.session(python=NEWEST_PYTHON)
def probe_qtemp(session: nox.Session) -> None:
    """One qtemp_ probe (read-only, or writes only in QTEMP):
    bin/probe qtemp_<topic> [-- <options>]."""
    name, args = _probe(session, "qtemp")
    session.install(*PROBE_REQUIREMENTS)
    session.run("python", f"probes/{name}.py", *args)


@nox.session(python=NEWEST_PYTHON)
def probe_lib(session: nox.Session) -> None:
    """CHANGES THE IBM i outside QTEMP: one lib_ probe, started only by
    bin/probe --approved <link> (CLAUDE.md). Dry run unless --execute."""
    name, args = _probe(session, "lib")
    env = {}
    for option, variable in (
        ("--approved", "DB2I_PROBE_APPROVED"),
        ("--approved-by", "DB2I_PROBE_APPROVED_BY"),
    ):
        if option not in args or args.index(option) + 1 >= len(args):
            session.error(f"{name} needs {option}: run it through bin/probe --approved <link>")
        index = args.index(option)
        env[variable] = args[index + 1]
        del args[index : index + 2]
    session.install(*PROBE_REQUIREMENTS)
    session.run("python", f"probes/{name}.py", *args, env=env)
