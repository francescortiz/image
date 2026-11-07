from django.db import models

from image.fields import ImageCenterField, VideoField


class SampleMedia(models.Model):
    image = models.ImageField(upload_to="samples", blank=True)
    image_center = ImageCenterField(image_field=image)
    video = VideoField(upload_to="samples", blank=True)
    video_center = ImageCenterField(image_field=video)
