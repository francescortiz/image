from django.db.models.signals import post_save, post_delete, pre_save
from django.db.models.fields.files import FileField
from django.conf import settings
import os
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


def removeDir(dirName):
    #Remove any read-only permissions on file.

    if os.path.exists(dirName):
        removePermissions(dirName)
        for name in os.listdir(dirName):
            file = os.path.join(dirName, name)
            if not os.path.islink(file) and os.path.isdir(file):
                removeDir(file)
            else:
                removePermissions(file)
                os.remove(file)
        os.rmdir(dirName)


def removePermissions(filePath):
    #if (os.access(filePath, os.F_OK)) : #If path exists
    if (not os.access(filePath, os.W_OK)):
        os.chmod(filePath, 0666)
    return


def removeCache(image_path):
    if image_path:
        removeDir(settings.IMAGE_CACHE_ROOT + "/" + image_path)


def prepareImageCacheCleanup(sender, instance=None, **kwargs):
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


def clearPreparedImageCacheCleanup(sender, instance=None, created=False, **kwargs):
    if created:
        return
    if instance is None:
        return
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            if instance.old_image_fields[field.attname] != field.value_to_string(instance):
                removeCache(instance.old_image_fields[field.attname])


def clearImageCache(sender, instance, **kwargs):
    for field in instance._meta.fields:
        if isinstance(field, FileField):
            removeCache(field.value_to_string(instance))


pre_save.connect(prepareImageCacheCleanup)
post_save.connect(clearPreparedImageCacheCleanup)
post_delete.connect(clearImageCache)

#reversion compatibility
if 'reversion' in settings.INSTALLED_APPS:
    try:
        from reversion.models import pre_revision_commit, post_revision_commit

        pre_revision_commit.connect(prepareImageCacheCleanup)
        post_revision_commit.connect(clearPreparedImageCacheCleanup)
    except ImportError:
        pass

