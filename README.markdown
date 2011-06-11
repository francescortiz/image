## Introduction
I've seen some plugins that allow you to set the crop images by dragging and resizing a selection area over the original image. The problem with this method is that you need to know cropped sizes when you upload the images. Also, many tuhmbnailers forget about videos.
This is why I created my own image resizing library for django.

## Custom settings

* **IMAGE_CACHE_ROOT**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

## Custom fields
It adds two custom fields you can use with your models:

* **ImageCenterField**: you only have to provide the **image_field** argument. It has to be the ImageField or VideoField it references. **It also provides thumbnail preview in the admin section** when in edit mode.
* **VideoField**: It just extends FileField.

## Template tags
You have to {% load image %} in your templates:
###{% image [field] [parameters] %}
Returns an url that points to the thumbnail.

* **field**: has to be an ImageField or VideoField instance. It doesn't necessarely needs to have a related ImageCenterField.
* **parameters**: string of a list of parameters in querystring format. See parameters section

## URLs
It provides two URLs:

* /image/(?P\<**path**\>)/(?P\<**parameters**\>): It is this view that actually does the work. **path** will be searched in the directory settings.MEDIA_ROOT. See below for **parameters**.
* /image-crosshair: Just a base64 encoded png to use in the admin section.

## Parameters
Parameters are supplied in query string format.
Since the image tag is just a wrapper for {% url image.views.image [path] [parameters] %}, we are going to talk about Common Parameters and URL Parameters.

### Common Parameters
Parameters to use both in the "{% image [field] [parameters] %}" tag and the {% url image.views.image [path] [parameters] %} tag:

* **width**: target width
* **height**: target height
* **mode**: "scale" or "crop". "scale" will fit the image to the given width and height without loosing proportions. "crop" will fill the given area cropping if necessary.
* **overlay**: and overlay image to add on top of the image. It won't be resized. I use it to place a play button on top of video thumbnails. Overlay search path is STATIC_DOC_ROOT.

### URL Parameters
These parameters don't make sense when you use the "{% image [field] [parameters] %}" tag:

* **url**: make a thumbnail of the given url. The url has to point to a media resource.
* **video**: If the key exists we are going to create a thumbnail of a video.
* **center**: center of attention. You have to provide X and Y as base 1 percentages. For example, "center=0.5,0.5" will set the center of attention to the center of the image.

## Admin Section
This is how ImageCenter looks in the admin section when it is editable. **Just click on the the center of attention of the image.**

[[admin_section.png]]
![Screenshot](https://github.com/francescortiz/image/wiki/admin_section.png)

## Background features

* Thumbnails are automatically removed when database entries are removed.
* It does not use any templates or resources. Just setup urls.py and done.
* South integration: custom fields are understood by south.

## Dependencies

* **PIL**: python imaging library is used for image manipualtion. If you want to handle transparency you need at least PIL 1.1.7
* **ffmpeg**: only if you want video thumbnails.

## Known issues
I developed what I needed. Open an issue if you need any of these fixed or demand any other feature.

* help_text kwarg does not work for ImageCenterField
* I only tested it in python 1.2.5.
* Thumnails are always saved in PNG format.
* It does not have yet a mechanism to prevent an attacker from creating arbitrary thumbnails and fill up your server's disk space.
* I am no python expert, so it has issues with import paths. Just readjust them to your needs in your project.
* South integration can also suffer from import path issues.

## Examples

Sample model:

    class Test(models.Model):
    
        image = ImageField(upload_to="test")
        image_center = ImageCenterField(image_field=image)
        video = VideoField(upload_to="test")
        video_center = ImageCenterField(image_field=video)

Sample urls.py:

    # -*- coding: UTF-8 -*-
    from django.conf.urls.defaults import *
    from django.contrib import admin
    admin.autodiscover()
    
    urlpatterns = patterns('',
        (r'^admin/', include(admin.site.urls)),
        (r'^', include('image.urls')),
    )

Sample template:

    {% load image %}
    {% image test.image 'width=150&height=150' %}
    {% image test.video 'width=150&height=150' %}
    {% url path_variable 'width=150&height=150&mode=scale' %}
    {% url '' 'url=http://www.example.com/img.jpg&width=150&height=150&mode=scale&video=true&overlay=img/overlay.png' %}

