# -*- coding: UTF-8 -*-
from django.conf.urls import patterns

urlpatterns = patterns('image.views',
    (r'^crosshair$', 'crosshair'),
    (r'^(?P<path>.*)/((?P<token>.*))$', 'image'),
)
