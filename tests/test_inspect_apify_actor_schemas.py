import unittest
from scripts.inspect_apify_actor_schemas import inspect
class ActorSchemaTests(unittest.TestCase):
    def test_get_only_and_redaction(self):
        def fake(url,token):
            if url.endswith("/builds/default"):
                return {"id":"build","inputSchema":{"properties":{"query":{"type":"string","default":"secret"}},"required":["query"]}}
            return {"id":url.split("/")[-1],"name":"actor","username":"owner"}
        r=inspect("dummy",get=fake)
        self.assertEqual(len(r["actors"]),2)
        self.assertEqual(r["actor_runs_started"],0)
        self.assertFalse(r["pilot_authorised"])
        self.assertNotIn("secret",str(r))
        self.assertEqual(r["actors"][0]["input_field_names"],["query"])
    def test_missing_token(self):
        with self.assertRaises(ValueError):inspect("")
if __name__=="__main__": unittest.main()
