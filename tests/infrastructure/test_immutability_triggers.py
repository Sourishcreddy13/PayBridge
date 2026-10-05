from paybridge.infrastructure.db import Database


def test_NFR_02_transition_trigger_exists(tmp_path):
    c=Database(tmp_path/'db.sqlite').connection()
    try:
        row=c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='prevent_transition_update'").fetchone(); assert row
    finally: c.close()
