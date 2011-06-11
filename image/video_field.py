from django.db import models
from django.db.models.fields.files import FieldFile

class VideoFieldFile(FieldFile):
    pass

class VideoField(models.FileField):
    
    attr_class = VideoFieldFile
    

