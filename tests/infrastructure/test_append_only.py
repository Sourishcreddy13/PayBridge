from pathlib import Path
import sqlite3
from uuid import uuid4
import pytest
from paybridge.infrastructure.db import Database


def test_NFR_02_payment_update_is_blocked(tmp_path: Path):
    db = Database(tmp_path/'db.sqlite')
    c = db.connection()
    try:
        pid=str(uuid4())
        c.execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?,?)", (pid,'****1234','ABCD*****56','D***','RETAIL','10.00','INR','n','idem-test-1','2026-10-04T00:00:00+00:00','actor'))
        with pytest.raises(sqlite3.DatabaseError): c.execute("UPDATE payments SET amount='11.00' WHERE payment_id=?", (pid,))
    finally: c.close()


def test_NFR_08_delete_is_blocked(tmp_path: Path):
    db = Database(tmp_path/'db.sqlite'); c=db.connection()
    try:
        pid=str(uuid4()); c.execute("INSERT INTO payments VALUES(?,?,?,?,?,?,?,?,?,?,?)", (pid,'****1234','ABCD*****56','D***','RETAIL','10.00','INR','n','idem-test-2','2026-10-04T00:00:00+00:00','actor'))
        with pytest.raises(sqlite3.DatabaseError): c.execute("DELETE FROM payments WHERE payment_id=?", (pid,))
    finally: c.close()
