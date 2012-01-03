# -*- coding: utf-8 -*-
from distutils.core import setup

setup(
    name='image',
    version='1.0',
    author=u'Francesc Ortiz',
    author_email='francescortiz@gmail.com',
    packages=['image'],
    url='https://github.com/francescortiz/image',
    license='GPLv3',
    description='Django application that provides cropping, resizing, ' + \
		'thumbnailing, overlays and masking for images and videos with ' + \
		'the ability to set the center of attention,',
    long_description='Django application that provides cropping, resizing, ' + \
		'thumbnailing, overlays and masking for images and videos with ' + \
		'the ability to set the center of attention,',
    zip_safe=False,
    include_package_data=True,
)
