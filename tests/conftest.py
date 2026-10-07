"""Offline-suite hermeticity: no test depends on this host's process count.

BudgetLauncher refuses a non-fake launch before reserving when the user's
processes exceed 60% of the per-user limit. Offline tests launch fake-transport
calls on real-shaped bindings, so on a busy host they would fail for reasons
unrelated to the code. Every test under tests/ therefore sees a quiet host,
unless it is marked ``real_host_guard`` or installs its own guard.

Inert inside a paid controller process: the joint controller admits its
launcher before it runs the harness modules under pytest, and this fixture
then leaves the shipped guard untouched.
"""

import pytest

from tests import evaluation_budget as D


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "real_host_guard: keep the shipped host process guard"
    )


def quiet_host_applies(admitted_launcher, keywords) -> bool:
    return admitted_launcher is None and "real_host_guard" not in keywords


@pytest.fixture(autouse=True)
def quiet_host(request, monkeypatch):
    if quiet_host_applies(D._ADMITTED_LAUNCHER, request.keywords):
        monkeypatch.setattr(D.BudgetLauncher, "host_guard", staticmethod(lambda: None))
