from io import BytesIO
import os
import shutil

from PIL import Image as PilImage
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import RequestFactory, TestCase
from django.urls import reverse

from image.fields import ImageCenter
from image.misc import get_image_url
from image.storage import IMAGE_CACHE_STORAGE
from image.utils import render as render_image
from test_image.models import SampleMedia


def make_png_bytes(width=100, height=80, color=(255, 0, 0, 255)):
    buf = BytesIO()
    img = PilImage.new("RGBA", (width, height), color)
    img.save(buf, "PNG")
    return buf.getvalue()


class SampleMediaForm(forms.ModelForm):
    class Meta:
        model = SampleMedia
        fields = ["image", "image_center"]


class ImageCompatibilityTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        os.makedirs(settings.STATIC_ROOT, exist_ok=True)
        os.makedirs(settings.IMAGE_CACHE_ROOT, exist_ok=True)
        app_static_dir = os.path.join(settings.BASE_DIR, "test_image", "static", "test_image")
        dst_static_dir = os.path.join(settings.STATIC_ROOT, "test_image")
        os.makedirs(dst_static_dir, exist_ok=True)
        for fname in ("red.png", "alpha_gradient.png"):
            shutil.copyfile(
                os.path.join(app_static_dir, fname),
                os.path.join(dst_static_dir, fname),
            )

    def test_root_view_and_generated_static_images(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("/image/image_token_", html)

        # Fetch one of the generated URLs from the session-tokenized template render
        start = html.index('/image/image_token_')
        end = html.index('"', start)
        img_url = html[start:end].replace("&amp;", "&")
        img_response = self.client.get(img_url)
        self.assertEqual(img_response.status_code, 200)
        rendered = PilImage.open(BytesIO(img_response.content))
        self.assertEqual(rendered.size, (640, 200))

        # Second request should serve from IMAGE_CACHE_STORAGE
        cached_response = self.client.get(img_url)
        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.content, img_response.content)

    def test_crosshair_view(self):
        response = self.client.get(reverse("image.views.crosshair"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-type"], "image/png")
        img = PilImage.open(BytesIO(response.content))
        self.assertEqual(img.size, (15, 15))

    def test_render_operations(self):
        raw = make_png_bytes(120, 80, (200, 100, 50, 255))
        out = render_image(
            raw,
            width=60,
            height=60,
            force=True,
            padding=0.1,
            overlays=("test_image/alpha_gradient.png",),
            overlay_sources=("static",),
            overlay_tints=("ff000088",),
            overlay_sizes=("0.5,0.5",),
            overlay_positions=("0.1!,0.1!",),
            mask="test_image/alpha_gradient.png",
            mask_source="static",
            center="0.25,0.75",
            format="PNG",
            quality=90,
            fill="00ff00ff",
            background="ffffff88",
            tint="0000ff88aa",
            pre_rotation="90",
            post_rotation="45",
            crop=True,
            grayscale=True,
        )
        img = PilImage.open(BytesIO(out))
        self.assertEqual(img.format, "PNG")
        self.assertTrue(img.size[0] > 0 and img.size[1] > 0)

    def test_model_field_form_widget_and_cache_cleanup(self):
        upload = SimpleUploadedFile("sample.png", make_png_bytes(100, 100), content_type="image/png")
        obj = SampleMedia.objects.create(image=upload, image_center="0.3,0.7")
        obj.refresh_from_db()

        self.assertIsInstance(obj.image_center, ImageCenter)
        self.assertAlmostEqual(obj.image_center.x, 0.3)
        self.assertAlmostEqual(obj.image_center.y, 0.7)
        self.assertEqual(obj.image.__image_center_instance__.x, 0.3)

        # Render template tag with ImageFieldFile + center of attention + autogen
        tpl = Template("{% load img %}{% image sample.image 'width=40&height=40&autogen=true' %}")
        req = self.factory.get("/")
        req.session = self.client.session
        rendered_url = tpl.render(Context({"sample": obj, "request": req})).strip()
        self.assertIn(obj.image.name, rendered_url)

        # Render ModelForm widget
        form = SampleMediaForm(instance=obj)
        form_html = form.as_p()
        self.assertIn("image_center_crosshair-", form_html)

        # get_image_url helper
        misc_url = get_image_url(obj.image.name, "width=30&height=30&autogen=true")
        self.assertIn("image_token_", misc_url)

        # Delete object and ensure signal handler runs cleanly
        image_name = obj.image.name
        obj.delete()
        self.assertFalse(IMAGE_CACHE_STORAGE.exists(image_name))
