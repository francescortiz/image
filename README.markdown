### What's new

Masking, working with static files, possiblity of telling format and quality.

**significant update: now you have to {% load img %} instead of {% load image %}**

## Introduction
I've seen some plugins that allow you to set the crop images by dragging and resizing a selection area over the original image. The problem with this method is that you need to know cropped sizes when you upload the images. Also, many thumbnailers forget about videos.
This is why I created my own image resizing library for django.

## settings variables

### Context Processors

'django.core.context_processors.request' is mandatory because the image tag uses sessions.

### Custom settings

* **IMAGE_CACHE_ROOT**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_DEFAULT_FORMAT**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_DEFAULT_QUALITY**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

### Dependency on django settings

* **STATIC_ROOT**: Only if you use overlay or mask.

* **FILE_UPLOAD_TEMP_DIR**: Used to store temporary images when working with videos.

## Custom fields
It adds two custom fields you can use with your models:

* **ImageCenterField**: you only have to provide the **image_field** argument. It has to be the ImageField or VideoField it references. **It also provides thumbnail preview in the admin section** when in edit mode.
* **VideoField**: It is just a FileField with another signature.

## Template tags
You have to {% load img %} in your templates:
###{% image [source] [parameters] %}
Returns an url that points to the thumbnail.

* **source**: Either a path or an ImageField or VideoField instance. It doesn't necessarely needs to have a related ImageCenterField.
* **parameters**: string of a list of parameters in querystring format. See parameters section

## URLs
It provides two URLs:

* /image/(?P\<**path**\>)/(?P\<**parameters**\>): It is this view that actually does the work. **path** will be searched in the directory settings.MEDIA_ROOT. See below for **parameters**.
* /image-crosshair: Just a base64 encoded png to use in the admin section.

## Parameters
Parameters are supplied in query string format.

### Common Parameters

* **width**: [required] target width. Set it to a big number if you are scaling to fit vertically.
* **height**: [required] target height. Set it to a big number if you are scaling to fit horizontally.
* **mode**: "scale" or "crop". Defaults to "crop". "scale" will fit the image to the given width and height without loosing proportions. "crop" will fill the given area cropping if necessary.
* **overlay**: and overlay image to add on top of the image. It won't be resized. I use it to place a play button on top of video thumbnails. Overlay search path is STATIC_ROOT.
* **mask**: a mask image. the source image has to be cropped to the mask image size. Mask search path is STATIC_ROOT. **If you set a mask, format switches automatically to PNG**
* **static**: tells image to look for our image in STATIC_ROOT instead of MEDIA_ROOT.
* **format**: one of JPG, PNG, etc.
* **quality**: quality to use for "format"

### Other parameters

* **url**: make a thumbnail of the given url. The url has to point to a media resource. If url is given, [source] is ignored.

These next two parameters don't make sense if you are thumbnailing an ImageField or VideoField, because if so image takes care of them automatically.

* **video**: If the key exists we are going to create a thumbnail of a video.
* **center**: center of attention. You have to provide X and Y as base 1 percentages. For example, "center=0.5,0.5" will set the center of attention to the center of the image.


## Admin Section
This is how ImageCenter looks in the admin section when it is editable. **Just click on the the center of attention of the image and save.**

![Screenshot](https://github.com/francescortiz/image/wiki/admin_section.png)

## Background features

* Thumbnails are automatically removed when database entries are removed.
* It does not use any templates or resources. Just setup urls.py and done.
* South integration: custom fields are understood by south.
* URLs get tokenized to the session, so it prevents direct image linkage from external sites.
* If you set IMAGE_CACHE_ROOT to a directory that is in your public http docs, then you can use mod_rewrite or equivalents to have the HTTP server to serve the resized image directly.

## Dependencies

* **PIL**: python imaging library is used for image manipualtion. If you want to handle transparency you need at least PIL 1.1.7
* **ffmpeg**: only if you want video thumbnails.

## Known issues
I develop as I need to. Open an issue if you need to fix something or demand any other feature.

* help_text kwarg does not work for ImageCenterField
* You cannot serve images outside of your website unless you have them already thumbnailed and you serve them with mod_rewrite or equivalent through an appropiate IMAGE_CACHE_ROOT. This is a security feature that you will be able to bypass once named profiles.

### TODO

* Add support for named profiles in order to be able to access images without having a session (allow 3rd party image linking)

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

    {% load img %}
    <img src="{% image test.image 'width=150&height=150&format=JPEG&quality=95' %}"/>
    <img src="{% image test.video 'width=150&height=150&format=PNG' %}"/>
    <img src="{% image path_variable 'width=150&height=150&mode=scale&static=true' %}"/>
    <img src="{% image '' 'url=http://www.example.com/img.jpg&width=150&height=150&mode=scale&video=true&overlay=img/overlay.png' %}"/>

