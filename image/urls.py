# -*- coding: UTF-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'image.views',
    url(r'^crosshair$', 'crosshair'),
    url(r'^(?P<path>.+)/(?P<token>[\w_=&]+)$', 'image'),
)
