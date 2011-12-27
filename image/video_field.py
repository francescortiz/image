from django.db import models
from django.db.models.fields.files import FieldFile


# A video field is exactly a file field with a different signature
class VideoFieldFile(FieldFile):
    pass


class VideoField(models.FileField):
    attr_class = VideoFieldFile
