from django.test import TestCase


class EcommerceSmokeTests(TestCase):
    def test_dashboard_url_resolves(self):
        response = self.client.get('/shop/')
        self.assertNotEqual(response.status_code, 404)
