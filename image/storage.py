# coding=UTF-8
import hashlib
import os

import sys
from os.path import basename, dirname

from django.conf import settings as django_settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage, staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.utils.module_loading import import_string

try:
    from django.core.files.storage import storages
except ImportError:
    storages = None

try:
    try:
        from storages.backends.s3 import S3Storage as S3BotoStorage
    except ImportError:
        try:
            from storages.backends.s3boto3 import S3Boto3Storage as S3BotoStorage
        except ImportError:
            from storages.backends.s3boto import S3BotoStorage

    BOTO_IS_AVAILABLE = True
except (ImportError, ImproperlyConfigured):
    BOTO_IS_AVAILABLE = False

from image import settings
from image.settings import IMAGE_CACHE_STORAGE as settings_IMAGE_CACHE_STORAGE, STATICFILES_STORAGE

__author__ = 'franki'

STORAGE = None


def get_storage_class(import_path=None):
    if import_path is None:
        storages_setting = getattr(django_settings, 'STORAGES', None)
        if storages_setting and 'default' in storages_setting:
            import_path = storages_setting['default']['BACKEND']
        else:
            import_path = getattr(
                django_settings,
                'DEFAULT_FILE_STORAGE',
                'django.core.files.storage.FileSystemStorage',
            )
    return import_string(import_path)

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


def get_storage():
    global STORAGE
    if STORAGE:
        return STORAGE
    storages_setting = getattr(django_settings, 'STORAGES', None)
    if storages is not None and storages_setting and 'image_cache' in storages_setting:
        STORAGE = storages['image_cache']
        return STORAGE
    if settings_IMAGE_CACHE_STORAGE:
        storage_class = get_storage_class(settings_IMAGE_CACHE_STORAGE)
    else:
        storage_class = get_storage_class()
    STORAGE = storage_class()
    return STORAGE


def get_media_storage():
    if hasattr(django_settings, 'DEFAULT_FILE_STORAGE'):
        return get_storage_class(django_settings.DEFAULT_FILE_STORAGE)()
    return default_storage


def get_static_storage():
    if hasattr(django_settings, 'STATICFILES_STORAGE'):
        return get_storage_class(django_settings.STATICFILES_STORAGE)()
    return staticfiles_storage


IMAGE_CACHE_STORAGE = get_storage()
MEDIA_STORAGE = get_media_storage()
STATIC_STORAGE = get_static_storage()
