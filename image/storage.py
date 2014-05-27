# coding=UTF-8
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import get_storage_class, FileSystemStorage

from image import settings
from image.settings import IMAGE_CACHE_STORAGE, STATICFILES_STORAGE


__author__ = 'franki'

STORAGE = None


class ImageCacheStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.IMAGE_CACHE_ROOT
        if base_url is None:
            base_url = settings.IMAGE_CACHE_URL
        if not location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        super(ImageCacheStorage, self).__init__(location, base_url, *args, **kwargs)

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        return super(ImageCacheStorage, self).path(name)


def get_storage():
    global STORAGE
    if STORAGE:
        return STORAGE
    if IMAGE_CACHE_STORAGE:
        storage_class = get_storage_class(IMAGE_CACHE_STORAGE)
    else:
        storage_class = get_storage_class()
    STORAGE = storage_class()
    return STORAGE


IMAGE_CACHE_STORAGE = get_storage()
MEDIA_STORAGE = get_storage_class()()
STATIC_STORAGE = get_storage_class(STATICFILES_STORAGE)()


