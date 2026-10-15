"""BA WordPress query-route isolation and no-write delivery safeguards."""
import unittest
from scripts import ba_wp_rest_routes as routes
from scripts import ba_atomic_snapshot_sender as sender
from scripts import ba_wordpress_sender_once as page_sender
from scripts import ba_auth_only_probe as auth_probe
from scripts import ba_delivery_credentials_readonly as credentials

class BAPlainPermalinkRoutes(unittest.TestCase):
    def test_query_routes_are_exactly_scoped(self):
        self.assertEqual(routes.AUTH_IDENTITY_URL,
            "https://jobs.zarafytek.com/?rest_route=/wp/v2/users/me&context=edit")
        self.assertEqual(routes.BA_SNAPSHOT_URL,
            "https://jobs.zarafytek.com/?rest_route=/business-analysis-tracker/v1/snapshot")
        self.assertEqual(routes.BA_PAGE_EDIT_URL,
            "https://jobs.zarafytek.com/?rest_route=/wp/v2/pages/49&context=edit")
        self.assertEqual(routes.BA_PAGE_UPDATE_URL,
            "https://jobs.zarafytek.com/?rest_route=/wp/v2/pages/49")
    def test_delivery_is_ba_only(self):
        self.assertEqual(sender.ENDPOINT, routes.BA_SNAPSHOT_URL)
        self.assertEqual(auth_probe.URL, routes.AUTH_IDENTITY_URL)
        self.assertEqual(page_sender.PAGE_URL, routes.BA_PAGE_EDIT_URL)
        self.assertEqual(page_sender.PUT_URL, routes.BA_PAGE_UPDATE_URL)
        self.assertNotIn("salesforce-tracker", sender.ENDPOINT)
        for route,url in [
            ("/wp/v2/users/me",routes.AUTH_IDENTITY_URL),
            ("/business-analysis-tracker/v1/snapshot",routes.BA_SNAPSHOT_URL),
            ("/wp/v2/pages/49",routes.BA_PAGE_UPDATE_URL),
        ]:
            self.assertTrue(routes.verify_ba_rest_endpoint(url,route))
            self.assertFalse(routes.verify_ba_rest_endpoint(url.replace(
                "jobs.zarafytek.com", "example.com"),route))
    def test_sender_stays_no_write_by_default(self):
        with self.assertRaises(ValueError):
            sender.send_once({"schema":"ba-live-snapshot/v1",
                              "quality":{"passed":True}},"u","p")
if __name__=="__main__":
    unittest.main()
