"""Block real sockets for every unit test, whatever the pytest invocation.

The Makefile and CI pass ``--disable-socket``, but enforcing it here means a
plain ``pytest tests/unit_tests/`` is hermetic too: a stray network call in a
unit test fails locally, not only in CI. Integration tests live in a separate
directory and are unaffected.
"""

from __future__ import annotations

from pytest_socket import disable_socket


def pytest_runtest_setup() -> None:
    disable_socket(allow_unix_socket=True)
