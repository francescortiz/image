from io import BytesIO
import os
import shutil
import tempfile
from unittest import mock

from PIL import Image as PilImage
from django import forms
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.template import Context, Template, TemplateSyntaxError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from image import storage as image_storage
from image import views as image_views
from image.fields import ImageCenter, ImageCenterField
from image.forms import ImageCenterFormField, ImageCenterFormWidget
from image.misc import get_image_url
from image.models import remove_cache, remove_directory, safe_delete
from image.storage import IMAGE_CACHE_STORAGE, ImageCacheStorage
from image.utils import (
    add_rgba_to_pixel,
    do_background,
    do_fill,
    do_grayscale,
    do_mask,
    do_overlay,
    do_overlays,
    do_padding,
    do_rotate,
    do_tint,
    image_create_token,
    image_tokenize,
    image_url,
    power_to_rgb,
    render as render_image,
    resizeCrop,
    resizeScale,
    rgb_to_power,
)
from image.video_field import VideoField, VideoFieldFile
from image.videothumbs import generate_thumb
from test_image.models import SampleMedia


def make_png_bytes(width=100, height=80, color=(255, 0, 0, 255)):
    buf = BytesIO()
    img = PilImage.new("RGBA", (width, height), color)
    img.save(buf, "PNG")
    return buf.getvalue()


def make_split_horizontal_image(width=200, height=100, left_color=(255, 0, 0, 255), right_color=(0, 0, 255, 255)):
    img = PilImage.new("RGBA", (width, height), left_color)
    right = PilImage.new("RGBA", (width // 2, height), right_color)
    img.paste(right, (width // 2, 0))
    return img


def make_split_vertical_image(width=100, height=200, top_color=(0, 255, 0, 255), bottom_color=(255, 255, 0, 255)):
    img = PilImage.new("RGBA", (width, height), top_color)
    bottom = PilImage.new("RGBA", (width, height // 2), bottom_color)
    img.paste(bottom, (0, height // 2))
    return img


class SampleMediaForm(forms.ModelForm):
    class Meta:
        model = SampleMedia
        fields = ["image", "image_center", "video", "video_center"]


class BaseImageTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        shutil.rmtree(settings.IMAGE_CACHE_ROOT, ignore_errors=True)
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        os.makedirs(settings.STATIC_ROOT, exist_ok=True)
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        os.makedirs(settings.IMAGE_CACHE_ROOT, exist_ok=True)
        app_static_dir = os.path.join(settings.BASE_DIR, "test_image", "static", "test_image")
        dst_static_dir = os.path.join(settings.STATIC_ROOT, "test_image")
        os.makedirs(dst_static_dir, exist_ok=True)
        for fname in ("red.png", "alpha_gradient.png"):
            shutil.copyfile(
                os.path.join(app_static_dir, fname),
                os.path.join(dst_static_dir, fname),
            )

    def tearDown(self):
        shutil.rmtree(settings.IMAGE_CACHE_ROOT, ignore_errors=True)
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)


class ImageCenterAndFieldTests(BaseImageTestCase):
    def test_image_center_defaults_and_explicit_coordinates(self):
        center_default = ImageCenter(None)
        self.assertEqual((center_default.x, center_default.y), (0.5, 0.5))
        self.assertEqual(str(center_default), "0.5,0.5")

        center_xy = ImageCenter(None, xy="0.25,0.75")
        self.assertEqual((center_xy.x, center_xy.y), (0.25, 0.75))

        center_malformed = ImageCenter(None, xy="not-a-coord")
        self.assertEqual((center_malformed.x, center_malformed.y), (0.5, 0.5))

        center_explicit = ImageCenter(None, x=0, y=1)
        self.assertEqual((center_explicit.x, center_explicit.y), (0.0, 1.0))

    def test_image_center_validation_errors(self):
        with self.assertRaises(ValueError):
            ImageCenter(None, x=0.5, y=None)
        with self.assertRaises(ValueError):
            ImageCenter(None, x=None, y=0.5)
        with self.assertRaises(ValueError):
            ImageCenter(None, x=-0.1, y=0.5)
        with self.assertRaises(ValueError):
            ImageCenter(None, x=1.1, y=0.5)
        with self.assertRaises(ValueError):
            ImageCenter(None, x=0.5, y=-0.01)
        with self.assertRaises(ValueError):
            ImageCenter(None, x=0.5, y=1.01)

    def test_image_center_field_validation_and_conversions(self):
        with self.assertRaises(ValueError):
            ImageCenterField(image_field=12345)

        field = ImageCenterField(image_field="image")
        self.assertEqual(field.db_type(None), "char(100)")
        _, _, _, deconstruct_kwargs = field.deconstruct()
        self.assertEqual(deconstruct_kwargs.get("image_field"), "image")

        center = field.to_python("0.2,0.8")
        self.assertIsInstance(center, ImageCenter)
        self.assertEqual((center.x, center.y), (0.2, 0.8))
        self.assertIs(field.to_python(center), center)

        self.assertEqual(field.get_db_prep_value(center), "0.2,0.8")
        self.assertEqual(field.get_db_prep_value("0.4,0.6"), "0.4,0.6")

        from_db = field.from_db_value("0.1,0.9", None, None)
        self.assertIsInstance(from_db, ImageCenter)
        self.assertEqual((from_db.x, from_db.y), (0.1, 0.9))

        # set_instance, value_to_string, and query_string
        dummy = SampleMedia(image_center="0.33,0.66")
        field.attname = "image_center"
        field.set_instance(dummy)
        self.assertIs(field.instance, dummy)
        self.assertEqual(field.value_to_string(dummy), "0.33,0.66")
        field.x, field.y = 0.2, 0.8
        self.assertEqual(field.query_string(), "center=0.2,0.8")


class ModelFormWidgetAndSignalsTests(BaseImageTestCase):
    def test_model_lifecycle_and_cache_cleanup_signals(self):
        upload1 = SimpleUploadedFile("first.png", make_png_bytes(100, 100), content_type="image/png")
        obj = SampleMedia.objects.create(image=upload1, image_center="0.3,0.7")
        obj.refresh_from_db()

        self.assertIsInstance(obj.image_center, ImageCenter)
        self.assertAlmostEqual(obj.image_center.x, 0.3)
        self.assertAlmostEqual(obj.image_center.y, 0.7)
        self.assertEqual(obj.image.__image_center_instance__.x, 0.3)

        first_image_name = obj.image.name
        # Generate a cached thumbnail for first_image_name
        result = image_views.image(None, first_image_name, "width=40&height=40", autogen=True)
        self.assertEqual(result, "Generated 200")
        token = image_create_token("width=40&height=40")
        cached_rel_path = os.path.join(first_image_name, token)
        self.assertTrue(IMAGE_CACHE_STORAGE.exists(cached_rel_path))

        # Saving without changing the image should NOT remove the cached thumbnail
        obj.image_center = "0.4,0.6"
        obj.save()
        self.assertTrue(IMAGE_CACHE_STORAGE.exists(cached_rel_path))

        # Replacing the image SHOULD remove the old image's cached thumbnails
        upload2 = SimpleUploadedFile("second.png", make_png_bytes(100, 100, (0, 255, 0, 255)), content_type="image/png")
        obj.image = upload2
        obj.save()
        self.assertFalse(IMAGE_CACHE_STORAGE.exists(cached_rel_path))

        # Generate cache for the second image and verify delete() cleans it up
        second_image_name = obj.image.name
        image_views.image(None, second_image_name, "width=40&height=40", autogen=True)
        second_cached_rel_path = os.path.join(second_image_name, token)
        self.assertTrue(IMAGE_CACHE_STORAGE.exists(second_cached_rel_path))

        obj.delete()
        self.assertFalse(IMAGE_CACHE_STORAGE.exists(second_cached_rel_path))

        # Saving an instance with an explicit non-existent PK should not fail in pre_save/post_save
        explicit_pk_obj = SampleMedia(pk=99999, image_center="0.5,0.5")
        explicit_pk_obj.save()

        # remove_directory with nested directory and non-existent directory
        nested_dir = os.path.join(settings.IMAGE_CACHE_ROOT, "custom_dir", "subdir")
        os.makedirs(nested_dir, exist_ok=True)
        remove_directory("custom_dir")
        remove_directory("non_existent_dir")

    def test_form_and_widget_rendering_for_image_and_video(self):
        # Empty instance (no saved image/video yet) renders empty widget output
        empty_obj = SampleMedia()
        empty_form = SampleMediaForm(instance=empty_obj)
        self.assertEqual(ImageCenterFormWidget().render("image_center", None), "")
        self.assertEqual(ImageCenterFormWidget().render("image_center", empty_obj.image_center), "")

        # Populated image and video fields render admin preview + crosshair + script + input
        img_upload = SimpleUploadedFile("widget_img.png", make_png_bytes(80, 80), content_type="image/png")
        vid_upload = SimpleUploadedFile("widget_vid.mp4", b"fake-video-bytes", content_type="video/mp4")
        obj = SampleMedia.objects.create(
            image=img_upload,
            image_center="0.2,0.8",
            video=vid_upload,
            video_center="0.6,0.4",
        )
        obj.refresh_from_db()

        form = SampleMediaForm(instance=obj)
        rendered = form.as_p()
        self.assertIn("image_center_crosshair-", rendered)
        self.assertIn("image_token_", rendered)
        self.assertNotIn("django.jQuery", rendered)

        # Form clean preserves submitted coordinate value
        form_field = ImageCenterFormField()
        self.assertFalse(form_field.required)
        self.assertEqual(form_field.clean("0.15,0.85"), "0.15,0.85")


class ImageUtilsTests(BaseImageTestCase):
    def test_color_math_helpers(self):
        # Low and high branches of power_to_rgb and rgb_to_power
        self.assertEqual(power_to_rgb(0.0), 0)
        self.assertTrue(0 < power_to_rgb(0.002) < 10)
        self.assertEqual(power_to_rgb(1.0), 255)

        self.assertEqual(rgb_to_power(0), 0.0)
        self.assertTrue(0.0 < rgb_to_power(5) < 0.01)
        self.assertAlmostEqual(rgb_to_power(255), 1.0, places=5)

        # Opaque and translucent branches of add_rgba_to_pixel
        blended_opaque = add_rgba_to_pixel((100, 100, 100, 1.0), (200, 200, 200, 1.0), 1.0, 1.0)
        self.assertEqual(blended_opaque, (150.0, 150.0, 150.0, 1.0))

        blended_alpha = add_rgba_to_pixel((100, 100, 100, 0.5), (200, 200, 200, 0.5), 1.0, 1.0)
        self.assertEqual(blended_alpha, (150.0, 150.0, 150.0, 0.5))

    def test_resize_scale_with_and_without_enlarge(self):
        img = PilImage.new("RGBA", (100, 50), (255, 0, 0, 255))

        # Downscale width-constrained
        scaled_down = resizeScale(img, 50, 50, force=True)
        self.assertEqual(scaled_down.size, (50, 25))

        # Downscale height-constrained
        scaled_height = resizeScale(img, 200, 20, force=True)
        self.assertEqual(scaled_height.size, (40, 20))

        # Upscale when force=True (enlarge=true)
        scaled_up = resizeScale(img, 200, 200, force=True)
        self.assertEqual(scaled_up.size, (200, 100))

        # Do not upscale when force=False (enlarge=false)
        not_enlarged = resizeScale(img, 200, 200, force=False)
        self.assertEqual(not_enlarged.size, (100, 50))

    def test_resize_crop_respects_center_of_attention(self):
        # Horizontal split: left half red, right half blue
        horiz = make_split_horizontal_image(200, 100)
        crop_left = resizeCrop(horiz.copy(), 50, 50, center="0.1,0.5", force=True)
        self.assertEqual(crop_left.size, (50, 50))
        self.assertEqual(crop_left.getpixel((25, 25)), (255, 0, 0, 255))

        crop_right = resizeCrop(horiz.copy(), 50, 50, center="0.9,0.5", force=True)
        self.assertEqual(crop_right.size, (50, 50))
        self.assertEqual(crop_right.getpixel((25, 25)), (0, 0, 255, 255))

        # Vertical split: top half green, bottom half yellow
        vert = make_split_vertical_image(100, 200)
        crop_top = resizeCrop(vert.copy(), 50, 50, center="0.5,0.1", force=True)
        self.assertEqual(crop_top.size, (50, 50))
        self.assertEqual(crop_top.getpixel((25, 25)), (0, 255, 0, 255))

        crop_bottom = resizeCrop(vert.copy(), 50, 50, center="0.5,0.9", force=True)
        self.assertEqual(crop_bottom.size, (50, 50))
        self.assertEqual(crop_bottom.getpixel((25, 25)), (255, 255, 0, 255))

        # force=False uses thumbnail without enlarging
        small = PilImage.new("RGBA", (40, 20), (255, 0, 0, 255))
        not_enlarged = resizeCrop(small.copy(), 100, 100, center="0.5,0.5", force=False)
        self.assertEqual(not_enlarged.size, (40, 20))

    def test_tint_grayscale_fill_background_padding_and_rotate(self):
        # Tint variations
        white_rgb = PilImage.new("RGB", (10, 10), (255, 255, 255))
        do_tint(white_rgb, None)
        do_tint(white_rgb, "None")
        do_tint(white_rgb, "ffffffff")

        img_full_tint = PilImage.new("RGBA", (10, 10), (255, 255, 255, 255))
        do_tint(img_full_tint, "ff000080")
        self.assertEqual(img_full_tint.getpixel((0, 0)), (255, 0, 0, 128))

        img_partial_tint = PilImage.new("RGBA", (10, 10), (200, 200, 200, 255))
        do_tint(img_partial_tint, "000000ff80")
        px = img_partial_tint.getpixel((0, 0))
        self.assertTrue(80 < px[0] < 120)
        self.assertEqual(px[3], 255)

        img_invalid_tint = PilImage.new("RGBA", (4, 4), (100, 150, 200, 255))
        do_tint(img_invalid_tint, "zzzzzzzzzz")
        self.assertEqual(img_invalid_tint.getpixel((0, 0)), (100, 150, 200, 255))

        # Grayscale
        colored = PilImage.new("RGBA", (10, 10), (255, 0, 0, 255))
        gray = do_grayscale(colored)
        r, g, b, a = gray.getpixel((5, 5))
        self.assertEqual(r, g)
        self.assertEqual(g, b)
        self.assertEqual(a, 255)

        # Fill
        inner = PilImage.new("RGBA", (20, 10), (255, 0, 0, 255))
        self.assertIs(do_fill(inner, None, 40, 40), inner)
        filled = do_fill(inner, "00ff00ff", 40, 40)
        self.assertEqual(filled.size, (40, 40))
        self.assertEqual(filled.getpixel((0, 0)), (0, 255, 0, 255))
        self.assertEqual(filled.getpixel((20, 20)), (255, 0, 0, 255))

        # Background
        transparent = PilImage.new("RGBA", (20, 20), (0, 0, 0, 0))
        self.assertIs(do_background(transparent, None), transparent)
        with_bg = do_background(transparent, "0000ffff")
        self.assertEqual(with_bg.getpixel((10, 10)), (0, 0, 255, 255))

        # Padding
        base_pad = PilImage.new("RGBA", (100, 100), (255, 0, 0, 255))
        self.assertIs(do_padding(base_pad, None), base_pad)
        self.assertIs(do_padding(base_pad, -0.1), base_pad)
        self.assertIs(do_padding(base_pad, "invalid"), base_pad)
        padded = do_padding(base_pad.copy(), 0.2)
        self.assertEqual(padded.size, (100, 100))
        self.assertEqual(padded.getpixel((0, 0))[3], 0)
        self.assertEqual(padded.getpixel((50, 50)), (255, 0, 0, 255))
        clamped_pad = do_padding(base_pad.copy(), 0.9)
        self.assertEqual(clamped_pad.size, (100, 100))

        # Rotation
        rect = PilImage.new("RGBA", (40, 20), (255, 0, 0, 255))
        self.assertIs(do_rotate(rect, None), rect)
        rot90 = do_rotate(rect, "90")
        self.assertEqual(rot90.size, (20, 40))
        rot45 = do_rotate(rect, "45")
        self.assertTrue(rot45.size[0] > 40 and rot45.size[1] > 20)
        rot_invalid = do_rotate(rect, "not-a-number")
        self.assertEqual(rot_invalid.size, (40, 20))

    def test_overlays_and_masks_from_static_and_media(self):
        # Save an overlay/mask image in MEDIA_STORAGE as well
        media_overlay_path = "media_overlay.png"
        mask_img = PilImage.new("RGBA", (20, 20), (0, 255, 0, 128))
        buf = BytesIO()
        mask_img.save(buf, "PNG")
        image_storage.MEDIA_STORAGE.save(media_overlay_path, ContentFile(buf.getvalue()))

        base = PilImage.new("RGBA", (100, 100), (255, 0, 0, 255))
        self.assertIs(do_overlay(base, None), base)

        # Negative width or height in overlay_size computes from aspect ratio
        ov_neg_w = do_overlay(base.copy(), "test_image/alpha_gradient.png", "static", overlay_size="-1,0.2")
        self.assertEqual(ov_neg_w.size, (100, 100))
        ov_neg_h = do_overlay(base.copy(), "test_image/alpha_gradient.png", "static", overlay_size="0.2,-1")
        self.assertEqual(ov_neg_h.size, (100, 100))

        # Oversized overlay without overlay_size scales down to fit base image (both width and height constrained)
        small_base = PilImage.new("RGBA", (10, 10), (255, 0, 0, 255))
        ov_auto = do_overlay(small_base, media_overlay_path, "media")
        self.assertEqual(ov_auto.size, (10, 10))

        tall_rgb_overlay_path = "tall_rgb_overlay.png"
        tall_buf = BytesIO()
        PilImage.new("RGB", (10, 40), (0, 0, 255)).save(tall_buf, "PNG")
        image_storage.MEDIA_STORAGE.save(tall_rgb_overlay_path, ContentFile(tall_buf.getvalue()))
        wide_base = PilImage.new("RGBA", (30, 15), (255, 0, 0, 255))
        ov_tall = do_overlay(wide_base.copy(), tall_rgb_overlay_path, "media")
        self.assertEqual(ov_tall.size, (30, 15))
        do_mask(wide_base.copy(), tall_rgb_overlay_path, "media", mask_mode=None)

        # Overlay positions: empty X, empty Y, and ! right/bottom origins
        ov_pos_empty_x = do_overlay(base.copy(), media_overlay_path, "media", overlay_position=",0.2")
        self.assertEqual(ov_pos_empty_x.size, (100, 100))
        ov_pos_empty_y = do_overlay(base.copy(), media_overlay_path, "media", overlay_position="0.2,")
        self.assertEqual(ov_pos_empty_y.size, (100, 100))

        # Multiple overlays via do_overlays with None strings
        multi = do_overlays(
            base.copy(),
            overlays=["test_image/alpha_gradient.png", media_overlay_path],
            overlay_tints=["None", "ff000080"],
            overlay_sources=["static", "media"],
            overlay_sizes=["None", "0.3,0.3"],
            overlay_positions=["None", "0.1!,0.1!"],
        )
        self.assertEqual(multi.size, (100, 100))

        # Masks: None, media source, distort mode, and proportional scaling
        self.assertIs(do_mask(base, None, "static"), base)
        masked_media = base.copy()
        do_mask(masked_media, media_overlay_path, "media", mask_mode="distort")
        self.assertEqual(masked_media.getpixel((50, 50))[3], 128)

        masked_prop = PilImage.new("RGBA", (10, 10), (255, 0, 0, 255))
        do_mask(masked_prop, media_overlay_path, "media", mask_mode=None)
        self.assertEqual(masked_prop.getpixel((5, 5))[3], 128)

    def test_render_defaults_and_token_helpers(self):
        raw = make_png_bytes(64, 48, (10, 20, 30, 255))
        # width=None, height=None uses original image dimensions; default format is JPEG (RGB)
        jpeg_bytes = render_image(raw, width=None, height=None, crop=False)
        jpeg_img = PilImage.open(BytesIO(jpeg_bytes))
        self.assertEqual(jpeg_img.format, "JPEG")
        self.assertEqual(jpeg_img.size, (64, 48))
        self.assertEqual(jpeg_img.mode, "RGB")

        # Tokenize reuses existing token in session and works with session=None
        session = {}
        tok1 = image_tokenize(session, "width=10&height=10")
        tok2 = image_tokenize(session, "width=10&height=10")
        self.assertEqual(tok1, tok2)
        self.assertEqual(session[tok1], "width=10&height=10")
        self.assertEqual(image_tokenize(None, "width=10&height=10"), tok1)

        # image_url with generate=True
        req = self.factory.get("/")
        req.session = {}
        url = image_url(req, "static=true&width=20&height=20", "test_image/red.png", generate=True)
        self.assertIn("test_image/red.png", url)


class ViewsAndTemplateTagsTests(BaseImageTestCase):
    def test_root_view_and_generated_static_images(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn("/image/image_token_", html)

        start = html.index("/image/image_token_")
        end = html.index('"', start)
        img_url = html[start:end].replace("&amp;", "&")
        img_response = self.client.get(img_url)
        self.assertEqual(img_response.status_code, 200)
        rendered = PilImage.open(BytesIO(img_response.content))
        self.assertEqual(rendered.size, (640, 200))

        # Second request serves from IMAGE_CACHE_STORAGE
        cached_response = self.client.get(img_url)
        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.content, img_response.content)
        self.assertEqual(cached_response["Content-type"], "image/jpeg")

    def test_image_view_content_type_by_format_and_cache(self):
        for fmt_param, expected_mime, expected_pil_format in [
            ("WEBP", "image/webp", "WEBP"),
            ("webp", "image/webp", "WEBP"),
            ("PNG", "image/png", "PNG"),
            ("JPEG", "image/jpeg", "JPEG"),
            ("JPG", "image/jpeg", "JPEG"),
        ]:
            params = "static=true&width=32&height=24&format=%s" % fmt_param
            tok = image_create_token(params)
            req = self.factory.get("/image/")
            req.user = AnonymousUser()
            req.session = {tok: params}

            # Initial generation sets Content-type matching format
            resp1 = image_views.image(req, "test_image/alpha_gradient.png", tok)
            self.assertEqual(resp1.status_code, 200)
            self.assertEqual(resp1["Content-type"], expected_mime)
            img1 = PilImage.open(BytesIO(resp1.content))
            self.assertEqual(img1.format, expected_pil_format)
            if expected_pil_format in ("PNG", "WEBP"):
                self.assertEqual(img1.mode, "RGBA")

            # Subsequent request served from cache (even with empty session) preserves Content-type
            req_cached = self.factory.get("/image/")
            req_cached.user = AnonymousUser()
            req_cached.session = {}
            resp2 = image_views.image(req_cached, "test_image/alpha_gradient.png", tok)
            self.assertEqual(resp2.status_code, 200)
            self.assertEqual(resp2["Content-type"], expected_mime)

        # Mask parameter forces PNG format and image/png Content-type
        mask_params = "static=true&width=32&height=24&format=JPEG&mask=test_image/alpha_gradient.png"
        tok_mask = image_create_token(mask_params)
        req_mask = self.factory.get("/image/")
        req_mask.user = AnonymousUser()
        req_mask.session = {tok_mask: mask_params}
        resp_mask = image_views.image(req_mask, "test_image/red.png", tok_mask)
        self.assertEqual(resp_mask.status_code, 200)
        self.assertEqual(resp_mask["Content-type"], "image/png")

    def test_crosshair_view(self):
        response = self.client.get(reverse("image.views.crosshair"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-type"], "image/png")
        img = PilImage.open(BytesIO(response.content))
        self.assertEqual(img.size, (15, 15))

    def test_image_view_permissions_admin_autogen_404_and_remote_url(self):
        # 1. Request with unauthenticated/unknown token -> 403 Forbidden
        req = self.factory.get("/image/unknown_token/test_image/red.png")
        req.session = {}
        req.user = AnonymousUser()
        resp_403 = image_views.image(req, "test_image/red.png", "unknown_token")
        self.assertEqual(resp_403.status_code, 403)

        # 2. Admin user with is_admin=true in token -> 200 OK without session token
        admin_user = User.objects.create_superuser(username="admin", email="a@b.com", password="pw")
        req_admin = self.factory.get("/image/")
        req_admin.session = {}
        req_admin.user = admin_user
        admin_params = "static=true&width=30&height=20&is_admin=true"
        resp_admin = image_views.image(req_admin, "test_image/red.png", admin_params)
        self.assertEqual(resp_admin.status_code, 200)
        self.assertEqual(PilImage.open(BytesIO(resp_admin.content)).size, (30, 20))

        # 3. Backwards-compatible swapped path/token for admin
        resp_swapped = image_views.image(
            req_admin,
            "static=true&width=25&height=25&is_admin=true",
            "test_image/red.png",
        )
        self.assertEqual(resp_swapped.status_code, 200)
        self.assertEqual(PilImage.open(BytesIO(resp_swapped.content)).size, (25, 25))

        # 4. autogen=True returns 'Generated 200' first, then 'Already generated', and 'Failed ...' on 404
        autogen_params = "static=true&width=16&height=16&mask=test_image/alpha_gradient.png"
        first_autogen = image_views.image(None, "test_image/red.png", autogen_params, autogen=True)
        self.assertEqual(first_autogen, "Generated 200")
        second_autogen = image_views.image(None, "test_image/red.png", autogen_params, autogen=True)
        self.assertEqual(second_autogen, "Already generated")

        failed_autogen = image_views.image(None, "nonexistent/missing.png", "width=16&height=16", autogen=True)
        self.assertTrue(failed_autogen.startswith("Failed "))

        # 5. Missing file returns 404 response
        req_missing = self.factory.get("/image/")
        req_missing.user = AnonymousUser()
        tok_missing = image_create_token("width=20&height=20")
        req_missing.session = {tok_missing: "width=20&height=20"}
        resp_404 = image_views.image(req_missing, "does_not_exist.png", tok_missing + "-:-extra")
        self.assertEqual(resp_404.status_code, 404)

        # 6. Remote URL fetching via requests.get
        fake_remote_png = make_png_bytes(50, 50, (0, 128, 255, 255))
        mock_response = mock.MagicMock()
        mock_response.content = fake_remote_png
        with mock.patch("image.views.requests.get", return_value=mock_response) as mocked_get:
            remote_params = "url=http://example.com/remote.png&width=25&height=25"
            tok_remote = image_create_token(remote_params)
            req_remote = self.factory.get("/image/")
            req_remote.user = AnonymousUser()
            req_remote.session = {tok_remote: remote_params}
            resp_remote = image_views.image(req_remote, "ignored_path.png", tok_remote)
            self.assertEqual(resp_remote.status_code, 200)
            mocked_get.assert_called_once_with("http://example.com/remote.png")
            self.assertEqual(PilImage.open(BytesIO(resp_remote.content)).size, (25, 25))

        # 7. IOError when opening cached file raises Http404, and IOError during render returns 500
        with mock.patch.object(IMAGE_CACHE_STORAGE, "open", side_effect=IOError("disk read error")):
            with self.assertRaises(Http404):
                image_views.image(req_remote, "ignored_path.png", tok_remote)

        with mock.patch("image.views.render", side_effect=IOError("corrupt image")), \
             mock.patch("image.views.traceback.print_exc"):
            err_params = "static=true&width=21&height=21"
            tok_err = image_create_token(err_params)
            req_err = self.factory.get("/image/")
            req_err.user = AnonymousUser()
            req_err.session = {tok_err: err_params}
            resp_500 = image_views.image(req_err, "test_image/red.png", tok_err)
            self.assertEqual(resp_500.status_code, 500)

    def test_template_tag_variations_and_misc_helper(self):
        # Invalid syntax (wrong argument count) raises TemplateSyntaxError
        with self.assertRaises(TemplateSyntaxError):
            Template("{% load img %}{% image only_one_arg %}")

        # Context without 'request' key falls back to HttpRequest()
        tpl_no_req = Template("{% load img %}{% image 'test_image/red.png' 'static=true&width=20&height=20' %}")
        rendered_no_req = tpl_no_req.render(Context({})).strip()
        self.assertIn("/image/image_token_", rendered_no_req)

        # VideoFieldFile in template tag appends &video=true and center
        vid_upload = SimpleUploadedFile("clip.mp4", b"video-data", content_type="video/mp4")
        obj = SampleMedia.objects.create(video=vid_upload, video_center="0.4,0.6")
        obj.refresh_from_db()
        with mock.patch("image.views.generate_thumb", return_value=(make_png_bytes(40, 40), 200)) as mocked_thumb:
            tpl_vid = Template("{% load img %}{% image sample.video 'width=30&height=30&autogen=true' %}")
            vid_url = tpl_vid.render(Context({"sample": obj})).strip()
            self.assertIn(obj.video.name, vid_url)
            mocked_thumb.assert_called_once()

        # get_image_url helper
        misc_url = get_image_url("test_image/red.png", "static=true&width=15&height=15&autogen=true")
        self.assertIn("image_token_", misc_url)


class StorageAndVideoThumbsTests(BaseImageTestCase):
    def test_image_cache_storage_validation_and_storage_getters(self):
        with override_settings(IMAGE_CACHE_ROOT=None):
            with mock.patch.object(image_storage.settings, "IMAGE_CACHE_ROOT", None):
                with self.assertRaises(ImproperlyConfigured):
                    ImageCacheStorage(location=None)

        storage = ImageCacheStorage(location=settings.IMAGE_CACHE_ROOT, base_url="/image/")
        storage.location = None
        with self.assertRaises(ImproperlyConfigured):
            storage.path("any.png")

        # Verify STORAGES['image_cache'] resolution in get_storage()
        with override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "image_cache": {"BACKEND": "image.storage.ImageCacheStorage"},
            }
        ):
            prev_storage = image_storage.STORAGE
            try:
                image_storage.STORAGE = None
                resolved = image_storage.get_storage()
                self.assertIsInstance(resolved, ImageCacheStorage)
            finally:
                image_storage.STORAGE = prev_storage

    def test_locally_mirrored_s3_storage(self):
        if not image_storage.BOTO_IS_AVAILABLE:
            self.skipTest("django-storages S3 backend not available")

        mirror_dir = tempfile.mkdtemp(dir=settings.BASE_DIR)
        try:
            with mock.patch.object(image_storage.settings, "S3_MIRROR_ROOT", mirror_dir):
                with mock.patch.object(image_storage.S3BotoStorage, "__init__", return_value=None), \
                     mock.patch.object(image_storage.S3BotoStorage, "exists", return_value=True) as mock_s3_exists, \
                     mock.patch.object(image_storage.S3BotoStorage, "_save", side_effect=lambda name, content: name) as mock_s3_save, \
                     mock.patch.object(image_storage.S3BotoStorage, "delete", return_value=None) as mock_s3_delete:
                    mirrored = image_storage.LocallyMirroredS3BotoStorage()

                    # First exists() queries remote S3 and creates local mirror marker
                    self.assertTrue(mirrored.exists("folder/pic.jpg"))
                    self.assertEqual(mock_s3_exists.call_count, 1)

                    # Second exists() hits local mirror without calling remote S3
                    self.assertTrue(mirrored.exists("folder/pic.jpg"))
                    self.assertEqual(mock_s3_exists.call_count, 1)

                    # _save() writes to remote S3 and local mirror
                    saved_name = mirrored._save("folder/saved.jpg", ContentFile(b"data"))
                    self.assertEqual(saved_name, "folder/saved.jpg")
                    mock_s3_save.assert_called_once()
                    self.assertTrue(mirrored.mirror.exists("folder/saved.jpg"))

                    # delete() removes from both remote S3 and local mirror
                    mirrored.delete("folder/saved.jpg")
                    mock_s3_delete.assert_called_once_with("folder/saved.jpg")
                    self.assertFalse(mirrored.mirror.exists("folder/saved.jpg"))

                # Remote exists() returning False returns False without creating local mirror
                with mock.patch.object(image_storage.S3BotoStorage, "__init__", return_value=None), \
                     mock.patch.object(image_storage.S3BotoStorage, "exists", return_value=False):
                    mirrored_false = image_storage.LocallyMirroredS3BotoStorage()
                    self.assertFalse(mirrored_false.exists("folder/not_there.jpg"))
        finally:
            shutil.rmtree(mirror_dir, ignore_errors=True)

    def test_video_field_dimensions_and_generate_thumb(self):
        vid_upload = SimpleUploadedFile("dim_video.mp4", b"video-bytes", content_type="video/mp4")
        obj = SampleMedia.objects.create(video=vid_upload)
        with mock.patch("image.video_field.get_video_dimensions", return_value=(1920, 1080)) as mock_dims:
            self.assertEqual(obj.video.width, 1920)
            self.assertEqual(obj.video.height, 1080)
            # Cached on second access
            self.assertEqual(obj.video.width, 1920)
            mock_dims.assert_called_once()

        # generate_thumb: missing video returns ('', '404')
        fs_storage = FileSystemStorage(location=settings.MEDIA_ROOT)
        data_404, status_404 = generate_thumb(fs_storage, "missing_video.mp4")
        self.assertEqual((data_404, status_404), ("", "404"))

        # generate_thumb: ffmpeg failure returns ('', '500')
        with mock.patch("image.videothumbs.os.system", return_value=1):
            data_500, status_500 = generate_thumb(fs_storage, obj.video.name)
            self.assertEqual((data_500, status_500), ("", "500"))

        # generate_thumb: simulated ffmpeg frame extraction, histogram RMSE selection, square & rect thumbnails
        def fake_ffmpeg(cmd):
            # Extract framemask path from command: /usr/bin/ffmpeg -y -t 00:00:05 -i '...' '<framemask>'
            framemask = cmd.split("'")[-2]
            fmt = "PNG" if framemask.lower().endswith("png") else "JPEG"
            for idx, color in enumerate([(10, 10, 10), (100, 100, 100), (110, 110, 110)], start=1):
                frame = PilImage.new("RGB", (120, 80), color)
                frame.save(framemask % idx, fmt)
            return 0

        with mock.patch("image.videothumbs.os.system", side_effect=fake_ffmpeg):
            thumb_sq, status_sq = generate_thumb(fs_storage, obj.video.name, thumb_size=(40, 40), format="jpg")
            self.assertEqual(status_sq, 200)
            self.assertEqual(PilImage.open(BytesIO(thumb_sq)).size, (40, 40))

            thumb_rect, status_rect = generate_thumb(fs_storage, obj.video.name, thumb_size=(60, 40), format="png")
            self.assertEqual(status_rect, 200)
            self.assertEqual(PilImage.open(BytesIO(thumb_rect)).size, (60, 40))

            thumb_orig, status_orig = generate_thumb(fs_storage, obj.video.name, thumb_size=None, format="jpg")
            self.assertEqual(status_orig, 200)
            self.assertEqual(PilImage.open(BytesIO(thumb_orig)).size, (120, 80))
