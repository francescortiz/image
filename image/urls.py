# -*- coding: UTF-8 -*-
try:
    from django.urls import re_path
except ImportError:
    from django.conf.urls import url as re_path

from image import views

urlpatterns = [
    re_path(r'^crosshair$', views.crosshair, name="image.views.crosshair"),
    re_path(r'^(?P<token>[:\-\w_=&]+)/(?P<path>.+)$', views.image, name="image.views.image"),
]
