import unittest
from scripts.ba_atomic_snapshot_sender import envelope, send_once

class BAReceiverTransportTests(unittest.TestCase):
    def test_valid_checksum(self):
        doc={"schema":"ba-live-snapshot/v1","quality":{"passed":True}}
        self.assertEqual(len(envelope(doc)["sha256"]),64)
    def test_reject_unapproved(self):
        doc={"schema":"ba-live-snapshot/v1","quality":{"passed":True}}
        with self.assertRaises(ValueError):
            send_once(doc,"","",approved=False)
    def test_reject_failed_qa(self):
        doc={"schema":"ba-live-snapshot/v1","quality":{"passed":False}}
        with self.assertRaises(ValueError):
            envelope(doc)
