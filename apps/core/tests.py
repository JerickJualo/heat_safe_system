from django.test import TestCase


class FrontendPageTests(TestCase):
    def test_frontend_pages_render(self):
        pages = {
            "/": "Dashboard",
            "/analytics/": "Data Analytics",
            "/prediction/": "Heat Index Prediction",
            "/comparison/": "Location Comparison",
            "/performance/": "Model Performance",
            "/reports/": "Reports &amp; Sources",
        }
        for path, title in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, "/static/js/app.js")

