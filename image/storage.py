# coding=UTF-8
import hashlib
import os

import sys
from os.path import basename, dirname

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class, FileSystemStorage

try:
    from storages.backends.s3boto import S3BotoStorage

    BOTO_IS_AVAILABLE = True
except (ImportError, ImproperlyConfigured):
    BOTO_IS_AVAILABLE = False

from image import settings
from image.settings import IMAGE_CACHE_STORAGE as settings_IMAGE_CACHE_STORAGE, STATICFILES_STORAGE

__author__ = 'franki'

STORAGE = None

if BOTO_IS_AVAILABLE:
    class LocallyMirroredS3BotoStorage(S3BotoStorage):
        def __init__(self, *args, **kwargs):
            super(LocallyMirroredS3BotoStorage, self).__init__(*args, **kwargs)
            self.mirror = FileSystemStorage(location=settings.S3_MIRROR_ROOT)

        def delete(self, name):
            super(LocallyMirroredS3BotoStorage, self).delete(name)
            try:
                self.mirror.delete(name)
            except OSError:
                full_path = self.mirror.path(name)
                if os.path.exists(full_path):
                    os.rmdir(full_path)

        def exists(self, name):
            exists_local = self.mirror.exists(name)
            if exists_local:
                return True
            else:
                exists_remote = super(LocallyMirroredS3BotoStorage, self).exists(name)
                if exists_remote:
                    self.mirror._save(name, ContentFile(""))
                    return True
            return False

        def _save(self, name, content):
            cleaned_name = super(LocallyMirroredS3BotoStorage, self)._save(name, content)
            self.mirror._save(name, ContentFile(""))
            return cleaned_name
else:
    class LocallyMirroredS3BotoStorage(object):
        def __init__(self, *args, **kwargs):
            raise ImportError("In order to use LocallyMirroredS3BotoStorage you need to install django-storages")


class ImageCacheStorage(FileSystemStorage):
    autogen_required = False

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

    def save(self, name, content, max_length=None):
        super(ImageCacheStorage, self).save(name, ContentFile(content), max_length=max_length)


class ManifestImageCacheStorage(ManifestStaticFilesStorage):
    autogen_required = True

    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.IMAGE_CACHE_ROOT
        if base_url is None:
            base_url = settings.IMAGE_CACHE_URL
        if not location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        super(ManifestImageCacheStorage, self).__init__(location, base_url, *args, **kwargs)

    def path(self, name):
        if not self.location:
            raise ImproperlyConfigured("IMAGE_CACHE_ROOT not defined.")
        return super(ManifestImageCacheStorage, self).path(name)

    def hashed_name(self, name, content=None, filename=None):
        md5sum = hashlib.md5(content).hexdigest()
        return name + "-:-" + md5sum

    def get_available_name(self, name, **kwargs):
        if self.exists(name):
            self.delete(name)
        return name

    def save(self, name, content, max_length=None):
        cached_image_file = IMAGE_CACHE_STORAGE.hashed_name(name, content)
        if self.exists(cached_image_file):
            self.delete(cached_image_file)
        super(ManifestImageCacheStorage, self).save(cached_image_file, ContentFile(content), max_length=max_length)
        self.hashed_files[name] = cached_image_file
        self.hashed_files[os.path.join(basename(name), dirname(name))] = os.path.join(basename(cached_image_file),
                                                                                      dirname(cached_image_file))
        self.save_manifest()

    def url(self, name, force=False):
        actual_name = self.hashed_files[name]
        return super(ManifestImageCacheStorage, self).url(actual_name)


def get_storage():
    global STORAGE
    if STORAGE:
        return STORAGE
    if settings_IMAGE_CACHE_STORAGE:
        storage_class = get_storage_class(settings_IMAGE_CACHE_STORAGE)
    else:
        storage_class = get_storage_class()
    STORAGE = storage_class()
    return STORAGE


IMAGE_CACHE_STORAGE = get_storage()
MEDIA_STORAGE = get_storage_class()()
STATIC_STORAGE = get_storage_class(STATICFILES_STORAGE)()
