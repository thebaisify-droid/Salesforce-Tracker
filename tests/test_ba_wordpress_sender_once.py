import unittest
from scripts.ba_wordpress_sender_once import make_update,publish,APPROVAL
class BAWPDeliveryTests(unittest.TestCase):
    def test_fragment_replacement_only(self):
        source='<section><tbody id="ba-v2-body">OLD</tbody><script type="application/json" id="ba-v2-json">[]</script></section>'
        pkg={"schema":"ba-wordpress-delivery-package/v1","page_id":49,"delivery_approved":False,
             "rows":1,"table_fragment":'<tbody id="ba-v2-body">NEW</tbody>',
             "embedded_json_fragment":'<script type="application/json" id="ba-v2-json">[{"x":1}]</script>'}
        res=make_update(source,pkg)
        self.assertIn("NEW",res)
        self.assertIn('[{"x":1}]',res)
        self.assertNotIn("OLD",res)
    def test_no_publish_without_approval(self):
        with self.assertRaises(ValueError):
            publish({}, "u","p",approval="no")
    def test_reject_malformed_raw_page(self):
        pkg={"schema":"ba-wordpress-delivery-package/v1","page_id":49,"delivery_approved":False,
             "rows":1,"table_fragment":"x","embedded_json_fragment":"y"}
        with self.assertRaises(ValueError):
            make_update("Page missing BA anchors",pkg)
if __name__=="__main__":unittest.main()
