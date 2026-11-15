"""Which authority does the PUB400 user have on the trigger commands (follows qtemp_create_trigger)?

qtemp_create_trigger found SQL0552 on ``CREATE TRIGGER``, also in QTEMP, and
the job log says it needs ``*USE`` on ``QSYS/ADDPFTRG``. The maintainer's
checks on PUB400 show ``ADDPFTRG`` with ``*PUBLIC *EXCLUDE``, secured by the
authorization list ``TRIGGER``, whose ``*PUBLIC`` is ``*USE``. This probe reads
what decides the user's effective authority, and checks it:

1. The command objects (``QSYS2.OBJECT_STATISTICS``): owner and authorization
   list of ``ADDPFTRG``, ``CHGPFTRG`` and ``RMVPFTRG``.
2. The authorities on the commands and on the authorization list ``TRIGGER``
   (``QSYS2.OBJECT_PRIVILEGES``, ``QSYS2.AUTHORIZATION_LIST_USER_INFO``), as far
   as the user may read them.
3. The effective authority: ``CHKOBJ ... AUT(*USE)`` on each command through
   ``QSYS2.QCMDEXC``. ``CHKOBJ`` only checks; it changes nothing.

Read-only: nothing is created or changed, not even in QTEMP.

Usage (from the host, through the PUB400 lock):
    bin/probe qtemp_trigger_authority
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

from _common import (
    ProbeError,
    Settings,
    connect,
    print_query,
    run_query,
    run_statement,
    write_result,
)

NAME = "qtemp_trigger_authority"
COMMANDS = ("ADDPFTRG", "CHGPFTRG", "RMVPFTRG")
_IN = ", ".join(f"'{c}'" for c in COMMANDS)

QUERIES = [
    (
        "command objects (OBJECT_STATISTICS)",
        "SELECT OBJNAME, OBJOWNER, AUTHORIZATION_LIST "
        "FROM TABLE(QSYS2.OBJECT_STATISTICS('QSYS', '*CMD')) X "
        f"WHERE OBJNAME IN ({_IN}) ORDER BY OBJNAME",
    ),
    (
        "authorities on the commands (OBJECT_PRIVILEGES)",
        "SELECT SYSTEM_OBJECT_NAME, AUTHORIZATION_NAME, OBJECT_AUTHORITY, AUTHORIZATION_LIST "
        "FROM QSYS2.OBJECT_PRIVILEGES WHERE SYSTEM_OBJECT_SCHEMA = 'QSYS' "
        f"AND OBJECT_TYPE = '*CMD' AND SYSTEM_OBJECT_NAME IN ({_IN}) "
        "ORDER BY SYSTEM_OBJECT_NAME, AUTHORIZATION_NAME",
    ),
    (
        "authorization list TRIGGER (OBJECT_PRIVILEGES, *AUTL)",
        "SELECT SYSTEM_OBJECT_NAME, AUTHORIZATION_NAME, OBJECT_AUTHORITY "
        "FROM QSYS2.OBJECT_PRIVILEGES WHERE SYSTEM_OBJECT_SCHEMA = 'QSYS' "
        "AND OBJECT_TYPE = '*AUTL' AND SYSTEM_OBJECT_NAME = 'TRIGGER' "
        "ORDER BY AUTHORIZATION_NAME",
    ),
    (
        "authorization list TRIGGER (AUTHORIZATION_LIST_USER_INFO)",
        "SELECT * FROM QSYS2.AUTHORIZATION_LIST_USER_INFO "
        "WHERE AUTHORIZATION_LIST = 'TRIGGER' ORDER BY AUTHORIZATION_NAME",
    ),
]


def run(settings: Settings) -> dict[str, Any]:
    results: dict[str, Any] = {"scope": "read-only (catalog views and CHKOBJ)"}
    conn = connect(settings)
    try:
        results["queries"] = []
        for label, sql in QUERIES:
            query = run_query(conn, label, sql)
            print_query(query)
            results["queries"].append(query)
        checks = {}
        for command in COMMANDS:
            step = run_statement(
                conn,
                f"CHKOBJ {command} *USE",
                "CALL QSYS2.QCMDEXC(?)",
                (f"CHKOBJ OBJ(QSYS/{command}) OBJTYPE(*CMD) AUT(*USE)",),
            )
            checks[command] = step
        results["chkobj"] = checks
        results["conclusion"] = {
            command: "authorized (*USE)" if step["ok"] else f"not authorized: {step['message']}"
            for command, step in checks.items()
        }
    finally:
        with contextlib.suppress(Exception):
            conn.close()
    return results


def main() -> int:
    try:
        settings = Settings.from_env(need_credentials=True)
        result = run(settings)
        for command, verdict in result["conclusion"].items():
            print(f"{command}: {verdict}")
        print(f"result saved to {write_result(NAME, result, settings)}")
    except ProbeError as exc:
        print(f"\nPROBE FAILED [{exc.category}]: {exc}", file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == "__main__":
    sys.exit(main())
