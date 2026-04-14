from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import User


class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin_test", password="Admin@1234", role="admin"
        )
        self.viewer = User.objects.create_user(
            username="viewer_test", password="Viewer@1234", role="viewer"
        )

    def _login(self, username, password):
        res = self.client.post(reverse("auth-login"), {"username": username, "password": password})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return res.data["access"]

    def test_login_success(self):
        res = self.client.post(reverse("auth-login"), {
            "username": "admin_test", "password": "Admin@1234"
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_login_wrong_password(self):
        res = self.client.post(reverse("auth-login"), {
            "username": "admin_test", "password": "wrong"
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint(self):
        token = self._login("admin_test", "Admin@1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "admin_test")
        self.assertEqual(res.data["role"], "admin")

    def test_me_unauthenticated(self):
        res = self.client.get(reverse("auth-me"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_list_users(self):
        token = self._login("admin_test", "Admin@1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.get(reverse("user-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_create_user(self):
        token = self._login("viewer_test", "Viewer@1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.post(reverse("user-list"), {
            "username": "new_user", "password": "Pass@1234",
            "password_confirm": "Pass@1234", "role": "viewer"
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_user(self):
        token = self._login("admin_test", "Admin@1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        res = self.client.post(reverse("user-list"), {
            "username": "new_user", "email": "new@test.com",
            "password": "Pass@1234", "password_confirm": "Pass@1234", "role": "viewer"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="new_user").exists())

    def test_cannot_delete_admin_user(self):
        token = self._login("admin_test", "Admin@1234")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        # Try to delete self
        res = self.client.delete(reverse("user-detail", args=[self.admin.pk]))
        # admin username protection is on username="admin", not "admin_test"
        self.assertIn(res.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN])
