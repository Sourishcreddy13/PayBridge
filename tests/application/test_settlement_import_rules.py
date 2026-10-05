from datetime import date

import pytest

from paybridge.domain.exceptions import SettlementImportAlreadyExists, ValidationError
from tests.helpers import build_stack

DAY = date(2026, 10, 4)
HEAD = "external_reference,payment_id,amount,currency\n"


def importer(tmp_path):
    return build_stack(tmp_path)


def do(s, body, day=DAY):
    return s.importer.import_bytes(body.encode(), day, "ops", "c")


def test_AC_06_amounts_are_quantized_to_two_decimals(tmp_path):
    s = importer(tmp_path)
    entries, _ = do(s, HEAD + "r1,,10.005,INR\n")
    assert str(entries[0].amount) == "10.01"


@pytest.mark.parametrize("row", [",,10.00,INR", "r1,,abc,INR", "r1,,-5,INR", "r1,,10.00,USD", "r1,not-a-uuid,10.00,INR", "x" * 200 + ",,1.00,INR"])
def test_AC_06_malformed_rows_are_rejected(tmp_path, row):
    with pytest.raises(ValidationError):
        do(importer(tmp_path), HEAD + row + "\n")


def test_AC_06_missing_columns_and_empty_files_are_rejected(tmp_path):
    s = importer(tmp_path)
    with pytest.raises(ValidationError):
        do(s, "a,b\n1,2\n")
    with pytest.raises(ValidationError):
        do(s, HEAD)


def test_AC_06_reimporting_the_same_file_is_rejected_without_duplicates(tmp_path):
    s = importer(tmp_path)
    do(s, HEAD + "r1,,10.00,INR\n")
    with pytest.raises(SettlementImportAlreadyExists):
        do(s, HEAD + "r1,,10.00,INR\n")
    assert len(s.settlements_repo.list_entries(DAY)) == 1


def test_AC_06_duplicate_reference_across_files_is_rejected_atomically(tmp_path):
    s = importer(tmp_path)
    do(s, HEAD + "r1,,10.00,INR\n")
    with pytest.raises(ValidationError):
        do(s, HEAD + "r2,,5.00,INR\nr1,,7.00,INR\n")
    assert [e.external_reference for e in s.settlements_repo.list_entries(DAY)] == ["r1"]


def test_AC_06_repeated_reference_inside_a_file_is_rejected(tmp_path):
    with pytest.raises(ValidationError):
        do(importer(tmp_path), HEAD + "r1,,1.00,INR\nr1,,2.00,INR\n")


def test_AC_06_non_utf8_input_is_rejected(tmp_path):
    with pytest.raises(ValidationError):
        importer(tmp_path).importer.import_bytes(b"\xff\xfe\x00", DAY, "ops", "c")


def test_AC_09_import_is_audited(tmp_path):
    s = importer(tmp_path)
    do(s, HEAD + "r1,,10.00,INR\n")
    assert s.rows("SELECT event_type FROM audit_events") == [{"event_type": "SETTLEMENT_IMPORTED"}]
