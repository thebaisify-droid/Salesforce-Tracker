import unittest
from unittest.mock import patch
from scripts.inspect_candidate_actor_schemas import summarise,inspect

class ActorSchemaTests(unittest.TestCase):
    def test_redacts_schema_fields(self):
        response={"data":{"actId":"T0edvAvD8lVcvc58G","id":"build1",
                  "actorDefinition":{"input":{"properties":{
                    "query":{"type":"string"},"apiToken":{"type":"string"},
                    "maxResults":{"type":"integer"}},"required":["query"]}}}}
        result=summarise("CV-Library","T0edvAvD8lVcvc58G",response)
        self.assertEqual([x["name"] for x in result["fields"]],["maxResults","query"])
        self.assertFalse(result["example_values_included"])
    def test_incorrect_actor_identity_is_rejected(self):
        with self.assertRaises(ValueError):
            summarise("CV-Library","T0edvAvD8lVcvc58G",{"data":{"actId":"wrong","actorDefinition":{"input":{"properties":{}}}}})
    def test_missing_schema_fails(self):
        with self.assertRaises(ValueError):
            summarise("CV-Library","T0edvAvD8lVcvc58G",{"data":{}})
if __name__=="__main__":unittest.main()
