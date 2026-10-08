import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from scripts.run_candidate_pilot import request_json

class PilotErrorDiagnosticsTests(unittest.TestCase):
    def test_safe_structured_apify_error_type(self):
        error=HTTPError("https://api.apify.com/example?token=DO_NOT_LOG",400,
                        "bad request",{},io.BytesIO(json.dumps({
                            "error":{"type":"invalid-input","message":"PRIVATE EMAIL AND TOKEN"}
                        }).encode()))
        with patch("scripts.run_candidate_pilot.urlopen",side_effect=error):
            with self.assertRaises(RuntimeError) as ctx:
                request_json("https://api.apify.com/example?token=DO_NOT_LOG","secret",body={"password":"hidden"})
        message=str(ctx.exception)
        self.assertIn("HTTP 400",message)
        self.assertIn("invalid-input",message)
        for secret in ("DO_NOT_LOG","PRIVATE EMAIL","secret","hidden"):
            self.assertNotIn(secret,message)

    def test_missing_structured_body(self):
        error=HTTPError("https://example.test",400,"bad",{},io.BytesIO(b"not json"))
        with patch("scripts.run_candidate_pilot.urlopen",side_effect=error):
            with self.assertRaisesRegex(RuntimeError,"error_type=unknown"):
                request_json("https://example.test","dummy",body={"a":1})

if __name__ == "__main__":unittest.main()
