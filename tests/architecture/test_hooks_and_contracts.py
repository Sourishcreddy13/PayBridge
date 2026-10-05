import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / ".claude" / "hooks"
bash = shutil.which("bash")
pytestmark = pytest.mark.skipif(bash is None, reason="bash required")


def run(hook: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(bash), str(HOOKS / hook)], cwd=cwd, capture_output=True, text=True)


@pytest.mark.parametrize("hook", ["amount-precision-check.sh", "payment-immutability-check.sh", "masked-pii-check.sh"])
def test_hooks_pass_on_the_repository(hook):
    result = run(hook, ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def make_tree(tmp_path: Path, domain_src: str, other: dict[str, str] | None = None) -> Path:
    for sub in ("domain", "application", "infrastructure"):
        (tmp_path / "src/paybridge" / sub).mkdir(parents=True)
    (tmp_path / "src/paybridge/domain/money.py").write_text(domain_src)
    for name, body in (other or {}).items():
        (tmp_path / name).write_text(body)
    return tmp_path


def test_precision_hook_rejects_float_money(tmp_path):
    tree = make_tree(tmp_path, "from decimal import Decimal\nx = float(amount)\n")
    result = run("amount-precision-check.sh", tree)
    assert result.returncode == 1 and "money.py" in result.stdout


def test_precision_hook_allows_marked_non_monetary_float(tmp_path):
    tree = make_tree(
        tmp_path,
        "from decimal import Decimal\n",
        {"src/paybridge/application/retry.py": "sleep(float(d))  # non-monetary: wall-clock seconds\n"},
    )
    assert run("amount-precision-check.sh", tree).returncode == 0


def test_precision_hook_fails_closed_without_sources(tmp_path):
    assert run("amount-precision-check.sh", tmp_path).returncode == 2


def test_immutability_hook_rejects_dml(tmp_path):
    tree = make_tree(tmp_path, "Decimal\n", {"src/paybridge/infrastructure/r.py": 'conn.execute("DELETE FROM payments")\n'})
    assert run("payment-immutability-check.sh", tree).returncode == 1


def test_pii_hook_rejects_logged_account_numbers(tmp_path):
    tree = make_tree(tmp_path, "Decimal\n", {"src/paybridge/application/s.py": 'logger.info("x", account_number)\n'})
    assert run("masked-pii-check.sh", tree).returncode == 1


def test_import_linter_contracts_are_loaded():
    config = (ROOT / ".importlinter").read_text()
    assert "[importlinter:contract:" in config and "include_external_packages = True" in config
