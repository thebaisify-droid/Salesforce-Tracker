import unittest
from unittest.mock import patch
from scripts.read_existing_apify_dataset import dataset_url, read_existing_dataset

class ExistingApifyDatasetTests(unittest.TestCase):
    def test_url_is_read_only_dataset_endpoint(self):
        url=dataset_url("abcDEFGH12345",limit=50)
        self.assertIn("/v2/datasets/abcDEFGH12345/items?",url)
        self.assertNotIn("/run",url)
    def test_invalid_id_is_rejected(self):
        for identifier in ("develop_ify/uk-jobs-reed-task","../danger",""):
            with self.subTest(identifier=identifier):
                with self.assertRaises(ValueError):
                    dataset_url(identifier,limit=10)
    def test_invalid_limits_are_rejected(self):
        with self.assertRaises(ValueError):
            dataset_url("abcDEFGH12345",limit=1001)
    def test_requires_token_before_network(self):
        with self.assertRaises(ValueError):
            read_existing_dataset("abcDEFGH12345","",20)
    def test_never_launches_post(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
        class Dummy(Response): pass
        with patch("scripts.read_existing_apify_dataset.urlopen") as opener:
            response=Dummy()
            opener.return_value=response
            with patch("scripts.read_existing_apify_dataset.json.load",return_value=[{"title":"Data Analyst"}]):
                result=read_existing_dataset("abcDEFGH12345","dummy",20)
        self.assertEqual(len(result),1)
        request=opener.call_args.args[0]
        self.assertEqual(request.get_method(),"GET")
        self.assertIn("/datasets/",request.full_url)

if __name__=="__main__": unittest.main()
