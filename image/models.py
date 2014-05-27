from django.db.models.signals import post_save, post_delete, pre_save
from django.db.models.fields.files import FileField
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from django.conf import settings as django_settings
from image.settings import IMAGE_CACHE_STORAGE


def remove_directory(dir_path):
    if IMAGE_CACHE_STORAGE.exists(dir_path):
        for directories, files in IMAGE_CACHE_STORAGE.listdir(dir_path):
            for directory in directories:
                IMAGE_CACHE_STORAGE.delete(directory)
            for file in files:
                IMAGE_CACHE_STORAGE.delete(file)
        IMAGE_CACHE_STORAGE.delete(dir_path)


def remove_cache(image_path):
    if image_path:
        remove_directory(image_path)


def prepare_image_cache_cleanup(sender, instance=None, **kwargs):
    if instance is None:
        return
    instance.old_image_fields = {}

    old_instance = None

    for field in instance._meta.fields:
        if isinstance(field, FileField):
            if not old_instance:
                try:
                    old_instance = sender.objects.get(pk=instance.pk)
                except (ObjectDoesNotExist, MultipleObjectsReturned):
                    return

            instance.old_image_fields[field.attname] = field.value_to_string(old_instance)


def clear_prepared_image_cache_cleanup(sender, instance=None, created=False, **kwargs):
    if created:
        return
    if instance is None:
        return
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            if instance.old_image_fields[field.attname] != field.value_to_string(instance):
                remove_cache(instance.old_image_fields[field.attname])


def clear_image_cache(sender, instance, **kwargs):
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            remove_cache(field.value_to_string(instance))


pre_save.connect(prepare_image_cache_cleanup)
post_save.connect(clear_prepared_image_cache_cleanup)
post_delete.connect(clear_image_cache)

#reversion compatibility
if 'reversion' in django_settings.INSTALLED_APPS:
    try:
        from reversion.models import pre_revision_commit, post_revision_commit

        pre_revision_commit.connect(prepare_image_cache_cleanup)
        post_revision_commit.connect(clear_prepared_image_cache_cleanup)
    except ImportError:
        pass

