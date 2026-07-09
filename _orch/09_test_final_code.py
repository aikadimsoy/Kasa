import sys, os, sqlite3, tempfile, shutil, unittest
sys.path.insert(0, 'd:/kasa')
from src.vault.database import Vault
from src.vault.audit import AuditChain
from src.vault.schema import CREATE_AUDIT_TABLE
from src.mcp_server.tools import VaultTools

class TestVault(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault = Vault(vault_path=self.tmpdir)
        self.vault.connect()
        self.conn = self.vault.get_connection()

    def tearDown(self):
        self.vault.close()
        shutil.rmtree(self.tmpdir)

    def test_schema_created(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['events', 'profiles', 'audit', 'settings']
        self.assertListEqual(tables, expected_tables)

    def test_write_and_read_event(self):
        source = "test"
        event_type = "test_type"
        content_dict = {"key": "value"}
        result = VaultTools(self.vault).event_ingest(source, event_type, content_dict)
        self.assertEqual(result["status"], "success")
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE source=? AND event_type=?", (source, event_type))
        event = cursor.fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(event[1], source)
        self.assertEqual(event[2], event_type)
        self.assertDictEqual(eval(event[3]), content_dict)

class TestAuditChain(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(CREATE_AUDIT_TABLE)
        self.conn.commit()
        self.chain = AuditChain(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_record_and_verify(self):
        agent_id = "test_agent"
        action = "test_action"
        details_dict = {"detail": "test"}
        entry_hash1 = self.chain.record(agent_id, action, details_dict)
        entry_hash2 = self.chain.record(agent_id, action, details_dict)
        entry_hash3 = self.chain.record(agent_id, action, details_dict)
        self.assertTrue(self.chain.verify_chain())

    def test_tamper_detected(self):
        agent_id = "test_agent"
        action = "test_action"
        details_dict = {"detail": "test"}
        entry_hash1 = self.chain.record(agent_id, action, details_dict)
        cursor = self.conn.cursor()
        cursor.execute("UPDATE audit SET action='tampered' WHERE id=1")
        self.conn.commit()
        self.assertFalse(self.chain.verify_chain())

class TestVaultTools(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.vault = Vault(vault_path=self.tmpdir)
        self.vault.connect()
        self.tools = VaultTools(self.vault, agent_id="system")

    def tearDown(self):
        self.vault.close()
        shutil.rmtree(self.tmpdir)

    def test_event_ingest(self):
        source = "test"
        event_type = "test_type"
        content_dict = {"key": "value"}
        result = self.tools.event_ingest(source, event_type, content_dict)
        self.assertEqual(result["status"], "success")
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM events WHERE source=? AND event_type=?", (source, event_type))
        event = cursor.fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(event[1], source)
        self.assertEqual(event[2], event_type)
        self.assertDictEqual(eval(event[3]), content_dict)

    def test_profile_write_read(self):
        key = "test_key"
        value = "test_value"
        provenance = "test_provenance"
        result = self.tools.profile_write(key, value, provenance)
        self.assertEqual(result["status"], "success")
        result = self.tools.profile_read("*")
        self.assertEqual(result["status"], "success")
        self.assertIn((key,), [row[0] for row in result["data"]])

    def test_forget(self):
        key = "test_key"
        value = "test_value"
        provenance = "test_provenance"
        self.tools.profile_write(key, value, provenance)
        result = self.tools.forget(key)
        self.assertEqual(result["status"], "success")
        result = self.tools.profile_read("*")
        self.assertNotIn((key,), [row[0] for row in result["data"]])

    def test_audit_read(self):
        agent_id = "test_agent"
        action = "test_action"
        details_dict = {"detail": "test"}
        self.chain.record(agent_id, action, details_dict)
        result = self.tools.audit_read()
        self.assertEqual(result["status"], "success")
        self.assertGreater(result["count"], 0)

if __name__ == '__main__':
    unittest.main()
