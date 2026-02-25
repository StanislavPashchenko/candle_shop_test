from django.test import TestCase
from django.core.files.base import ContentFile
from pathlib import Path
from shop.models import HomeBanner

class HomeBannerDeleteTests(TestCase):
    def test_media_file_removed_on_delete(self):
        b = HomeBanner.objects.create(is_active=True)
        b.media.save('home_banner_test.txt', ContentFile(b'hello'), save=True)
        p = Path(b.media.path)
        self.assertTrue(p.exists())
        b.delete()
        self.assertFalse(p.exists())
