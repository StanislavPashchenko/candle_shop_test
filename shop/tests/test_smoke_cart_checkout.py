import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from shop.models import Candle, Order, OrderItem


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SmokeCartCheckoutTests(TestCase):
    def _create_candle(self) -> Candle:
        c = Candle.objects.create(
            name="Свеча тест",
            description="Описание",
            price="100.00",
            is_available=True,
        )
        c.image.save("test.jpg", ContentFile(b"fake-image-bytes"), save=True)
        return c

    def test_add_to_cart_and_open_cart_page(self):
        candle = self._create_candle()

        resp = self.client.post(
            reverse("cart_add"),
            data=json.dumps({"pk": candle.pk, "qty": 2, "options": {}}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertTrue(payload.get("ok"))
        self.assertEqual(payload.get("items"), 2)

        resp2 = self.client.get(reverse("cart_view"))
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, candle.display_name())

    def test_checkout_creates_order(self):
        candle = self._create_candle()

        session = self.client.session
        session["cart"] = {str(candle.pk): 1}
        session.save()

        with patch("shop.views.telegram_send_message", return_value=False):
            resp = self.client.post(
                reverse("checkout"),
                data={
                    "full_name": "Тест Пользователь",
                    "phone": "+380000000000",
                    "email": "test@example.com",
                    "city": "Киев",
                    "payment_method": "card",
                    "agree_to_terms": "on",
                    "warehouse": "Отделение 1",
                    "notes": "",
                },
                follow=True,
            )
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.warehouse, "Отделение 1")

        self.assertEqual(OrderItem.objects.count(), 1)
        item = OrderItem.objects.first()
        self.assertEqual(item.order_id, order.id)
        self.assertEqual(item.candle_id, candle.id)
        self.assertEqual(item.quantity, 1)

        try:
            p = Path(candle.image.path)
            if p.exists():
                p.unlink()
        except Exception:
            pass
