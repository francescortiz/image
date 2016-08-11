# -*- coding: UTF-8 -*-
from django.conf.urls import url

from image import views

urlpatterns = [
    url(r'^crosshair$', views.crosshair),
    url(r'^(?P<path>.+)/(?P<token>[\w_=&]+)$', views.image),
]
