"""Negative examples for the checker itself.

A check that has never failed proves nothing, so each case below breaks a
copy of a project in a way that is different from the shipped violating patch.
"""
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench"))
import archcheck  # noqa: E402


def project(task_id, tmp_path):
    task_dir = ROOT / "tasks" / task_id
    workspace = tmp_path / "workspace"
    shutil.copytree(task_dir / "repo", workspace)
    task = yaml.safe_load((task_dir / "task.yaml").read_text(encoding="utf-8"))
    return workspace, task, task_dir / "repo"


def add_env(workspace, service, line):
    path = workspace / "deploy" / f"{service}.yaml"
    text = path.read_text(encoding="utf-8")
    if "environment:" not in text:
        text += "environment:\n"
    path.write_text(text + f"  {line}\n", encoding="utf-8")


def append_code(workspace, relative, code):
    path = workspace / relative
    path.write_text(path.read_text(encoding="utf-8") + "\n" + code + "\n", encoding="utf-8")


T1, T2, T3, T4, T5 = (
    "t1_acl_delivery",
    "t2_passive_repo_cap",
    "t3_acyclic_reminders",
    "t4_module_contracts_hold",
    "t5_schema_drift_scan",
)
SERVICE_T1 = "services/orders_api/app.py"
MODULE_T4 = "shop/orders/service.py"


@pytest.mark.parametrize("task_id", [T1, T2, T3, T4, T5])
def test_unmodified_project_passes(task_id, tmp_path):
    workspace, task, base = project(task_id, tmp_path)
    assert archcheck.check(workspace, task, base)["status"] == "pass"


# --- other ways to break the rule than the shipped patch ------------------


def test_repo_calling_external_system_is_an_acl_violation(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    add_env(workspace, "orders-repo", "CHECK_URL: https://api.other.example/v1")
    result = archcheck.check(workspace, task, base)
    assert {v["target"] for v in result["violations"]["acl"]} == {"orders_repo"}


def test_api_reading_database_directly_is_a_crud_violation(tmp_path):
    workspace, task, base = project(T2, tmp_path)
    add_env(workspace, "loyalty-api", "LOYALTY_DB_DSN: sqlite://loyalty-db/loyalty")
    result = archcheck.check(workspace, task, base)
    assert "loyalty_api" in {v["target"] for v in result["violations"]["crud"]}


def test_three_service_cycle_is_found(tmp_path):
    workspace, task, base = project(T3, tmp_path)
    add_env(workspace, "mail-acl", "BOOKINGS_URL: http://bookings-api:8080")
    result = archcheck.check(workspace, task, base)
    assert result["violations"]["acyclic"]


@pytest.mark.parametrize(
    "code",
    [
        "from shop.inventory.internal.stock import LEDGER",
        "import shop.inventory.internal.stock as stock",
        "from shop.inventory import internal",
        "def late():\n    from shop.catalog.internal import prices\n    return prices",
        "from ..inventory.internal import reservations",
    ],
)
def test_every_import_form_is_seen(code, tmp_path):
    workspace, task, base = project(T4, tmp_path)
    append_code(workspace, MODULE_T4, code)
    result = archcheck.check(workspace, task, base)
    assert "bcIsolation" in result["violations"]


def test_importing_a_foreign_contract_stays_allowed(tmp_path):
    workspace, task, base = project(T4, tmp_path)
    append_code(workspace, MODULE_T4, "from ..inventory import contracts")
    assert archcheck.check(workspace, task, base)["status"] == "pass"


def test_relation_missing_from_diagram_is_drift(tmp_path):
    workspace, task, base = project(T5, tmp_path)
    add_env(workspace, "ocr-acl", "DOCS_URL: http://docs-repo:8080")
    assert "drift" in archcheck.check(workspace, task, base)["violations"]


def test_element_only_on_diagram_is_drift(tmp_path):
    workspace, task, base = project(T5, tmp_path)
    path = workspace / "architecture" / "architecture.puml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("@enduml", 'Container(ghost, "Ghost")\n@enduml'), encoding="utf-8")
    assert "drift" in archcheck.check(workspace, task, base)["violations"]


# --- unknown must never look like "no violations" -------------------------


@pytest.mark.parametrize(
    "code",
    [
        'FASTSHIP = "https://api.fastship.example/v2"',
        'DSN = f"sqlite://orders-db/{1}"',
        "from services.orders_repo import app as repo_app",
        "import sqlite3",
        "import importlib",
    ],
)
def test_wiring_hidden_in_code_is_reported(code, tmp_path):
    workspace, task, base = project(T1, tmp_path)
    append_code(workspace, SERVICE_T1, code)
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_docstring_mentioning_url_is_not_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    path = workspace / SERVICE_T1
    path.write_text(
        '"""See https://docs.example/orders for details."""\n' + path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert archcheck.check(workspace, task, base)["status"] == "pass"


def test_unparsable_endpoint_value_is_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    add_env(workspace, "orders-api", "CARRIER_HOST: carrier.internal:9000")
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_unknown_manifest_kind_is_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    (workspace / "deploy" / "x.yaml").write_text("name: x\nkind: cronjob\n", encoding="utf-8")
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_broken_manifest_is_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    (workspace / "deploy" / "x.yaml").write_text("name: [", encoding="utf-8")
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_empty_deploy_is_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    shutil.rmtree(workspace / "deploy")
    (workspace / "deploy").mkdir()
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_retagging_a_service_to_silence_a_rule_is_reported(tmp_path):
    workspace, task, base = project(T1, tmp_path)
    add_env(workspace, "orders-api", "FASTSHIP_URL: https://api.fastship.example/v2")
    path = workspace / "deploy" / "orders-api.yaml"
    path.write_text(
        path.read_text(encoding="utf-8") + "labels:\n  architecture.tags: [acl]\n",
        encoding="utf-8",
    )
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_unreadable_diagram_is_reported(tmp_path):
    workspace, task, base = project(T5, tmp_path)
    path = workspace / "architecture" / "architecture.puml"
    path.write_text(path.read_text(encoding="utf-8") + "Foo(bar)\n", encoding="utf-8")
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_missing_diagram_is_reported(tmp_path):
    workspace, task, base = project(T5, tmp_path)
    (workspace / "architecture" / "architecture.puml").unlink()
    assert archcheck.check(workspace, task, base)["status"] == "error"


def test_dynamic_import_in_monolith_is_reported(tmp_path):
    workspace, task, base = project(T4, tmp_path)
    append_code(workspace, MODULE_T4, '__import__("shop.inventory.internal.stock")')
    assert archcheck.check(workspace, task, base)["status"] == "error"
