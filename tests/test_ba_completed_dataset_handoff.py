import unittest
from scripts.ba_completed_dataset_handoff import build_batch, EXPECTED

class CompletedReceiptHandoffTests(unittest.TestCase):
    def setUp(self):
        self.receipts=[{"source":s,"run_id":"RUN000"+str(i)} for i,s in enumerate(EXPECTED)]
    def getter(self,uri,token):
        if "/actor-runs/" in uri:
            idx=int(uri[-1])
            return {"status":"SUCCEEDED","actId":list(EXPECTED.values())[idx],
                    "defaultDatasetId":"DATASET"+str(idx),"finishedAt":"2026-10-15T15:00:00Z"}
        if "/items?" in uri:
            return [{"title":"Business Analyst","url":"https://www.jobserve.com/gb/en/abc"}]
        return {"itemCount":1}
    def test_all_sources_retrieved_using_completed_run_identifiers(self):
        b=build_batch(self.receipts,"placeholder",get=self.getter)
        self.assertEqual(len(b["sources"]),5)
        self.assertEqual(sum(len(s["records"]) for s in b["sources"]),5)
    def test_wrong_actor_identity_blocks(self):
        def bad(uri,token):
            x=self.getter(uri,token)
            if "/actor-runs/" in uri: x["actId"]="not-approved"
            return x
        with self.assertRaisesRegex(ValueError,"Actor ID mismatch"):
            build_batch(self.receipts,"placeholder",get=bad)
    def test_partial_dataset_blocks(self):
        def bad(uri,token):
            if "/items?" in uri:return []
            return self.getter(uri,token)
        with self.assertRaisesRegex(ValueError,"Partial"):
            build_batch(self.receipts,"placeholder",get=bad)
    def test_no_empty_or_repeated_sources(self):
        x=self.receipts[:4]+[self.receipts[0]]
        with self.assertRaises(ValueError):build_batch(x,"placeholder",get=self.getter)
    def test_no_token_fails_before_get(self):
        with self.assertRaises(ValueError):build_batch(self.receipts,"",get=self.getter)
if __name__=="__main__":unittest.main()
