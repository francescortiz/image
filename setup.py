# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(
    name='image',
    version='1.3.2',
    author=u'Francesc Ortiz',
    author_email='francescortiz@gmail.com',
    packages=find_packages(),
    url='https://github.com/francescortiz/image',
    license='BSD',
    description='Django application that provides cropping, resizing, ' + \
                'thumbnailing, overlays and masking for images and videos with ' + \
                'the ability to set the center of attention,',
    long_description='Django application that provides cropping, resizing, ' + \
                     'thumbnailing, overlays and masking for images and videos with ' + \
                     'the ability to set the center of attention,',
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'pillow', 'django',
    ],
)
