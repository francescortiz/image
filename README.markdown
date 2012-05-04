### What's new

**May 2012**

- parameter "overlay_source=media":
    looks for overlay image in MEDIA_ROOT instead of STATIC_ROOT

- parameter "overlay_tint=RRGGBBAA" or  "overlay_tint=RRGGBBAAII":
    Tints the overlay.
    See below.

- support for multiple overlays:
    See below.

**April 2012**

- make it compatible with django 1.4

- make it compatible with django-reversion.

- parameter "autogen=true":
    Add support for precreation of images.
    Allows external linking, good for newsletters and others

- parameter "background=RRGGBBAA":
    Allow to set background color to an RGBA hex value.
    Applied before mask and overlay.

- parameter "fill=RRGGBBAA":
    When using "mode=scale", allow to force size of output image
    to target with and height.
    You have to pass and RGBA hex value that will be set as background color.
    Applied before mask and overlay.

**December 2011**

Masking, working with static files, possiblity of telling format and quality.
Show error images instead of raising exceptions.

Significant update: now you have to {% load img %} instead of {% load image %}


## Introduction
I've seen some plugins that allow you to set the crop images by dragging and resizing a selection area over the original image. The problem with this method is that you need to know cropped sizes when you upload the images. Also, many thumbnailers forget about videos.
This is why I created my own image resizing library for django.

## settings variables

### Context Processors

'django.core.context_processors.request' is mandatory because the image tag uses sessions.

### Custom settings

* **IMAGE_CACHE_ROOT**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_DEFAULT_FORMAT**: (default='JPEG') It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_DEFAULT_QUALITY**: (default=85) It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_FONT_FILE**: (default=[image package path]/FreeFont.ttf) The font file to use for error messages.

* **IMAGE_FONT_LINE_HEIGHT**: (default=.7) A base 1 percentage (1 equals 100%) to set line height for the font.

* **IMAGE_FONT_BACKGROUND**: ( default=(255,255,255,255) ) Background color for errors. RGBA format

* **IMAGE_FONT_LINE_HEIGHT**: ( default=(0,0,0,255) ) Foreground color for errors. RGBA format

* **IMAGE_ERROR_NOT_FOUND**: ( default="Image not found" ) Text to show when an image is not found.

* **IMAGE_ERROR_NOT_VALID**: ( default="Image not valid" ) Text to show when an image is not valid.

* **IMAGE_ERROR_VIDEO_NOT_FOUND**: ( default="Video not found" ) Text to show when a video is not found.

* **IMAGE_ERROR_FFMPEG**: ( default="Video error" ) Text to show when ffmpeg fails.

* **IMAGE_WRONG_REQUEST**: (default="Wrong request" ) Text to show when the request is wrong

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

## Overlays
You can have multiple overlays, each one with its overlay_source and its overlay_tint.

**overlay_tint=RRGGBBAA or overlay_tint=RRGGBBAAII**

II stands for Intensity. Values from 00 to ff. Ammount of tint to apply.

If AA smaller than ff, the layer will become transparent. You cannot make the layer transparent without changing its color. Open an issue if you have this need.

Accepts value None (overlay_tint=None)

## Examples:

overlay=test/img0.png&overlay_tint=**ff0000ff**&overlay=test/img1.png&overlay_tint=**00ff0077**

overlay=test/img0.png&overlay_tint=**None**&overlay=test/img1.png&overlay_tint=**00ff0077aa**

overlay=test/img0.png&overlay_source=**media**&overlay=test/img1.png&overlay_source=**static**

## Caution with overlays
**If you use overlay_tint or overlay_source, the position in which they appear does not matter**.

The order of appearances is used to associate overlays with overlay_tints and overlay_sources. In other words, the first appearance of overlay_tint is associated with the first overlay. The same applies for overlay_source.

### These two are equivalent:

overlay=test/img0.png&**overlay_tint=ff0000ff**&overlay=test/img1.png

overlay=test/img0.png&overlay=test/img1.png**&overlay_tint=ff0000ff**

### To tint only the second overlay, you have to do this:

overlay=test/img0.png**&overlay_tint=None**&overlay=test/img1.png**&overlay_tint=ff0000ff**

## Parameters
Parameters are supplied in query string format.

### Common Parameters

* **width**: [required] target width. Set it to a big number if you are scaling to fit vertically.
* **height**: [required] target height. Set it to a big number if you are scaling to fit horizontally.
* **mode**: "scale" or "crop". Defaults to "crop". "scale" will fit the image to the given width and height without loosing proportions. "crop" will fill the given area cropping if necessary.
* **overlay** (multiple values accepted): and overlay image to add on top of the image. It won't be resized. I use it to place a play button on top of video thumbnails. Overlay search path is STATIC_ROOT.
* **overlay_source=media/static** (multiple values accepted): tells where to look for the overlay, either MEDIA_ROOT or STATIC_ROOT.
* **overlay_tint=RRGGBBAA** overlay_tint=RRGGBBAA**II** (multiple values accepted): tints the overlay. II stands for intensity. AA different to ff makes the overlay transparent.
* **mask**: a mask image. the mask will be resized to the rendered image size. Mask search path is STATIC_ROOT. **If you set a mask, format switches automatically to PNG**
* **static**: tells image to look for our image in STATIC_ROOT instead of MEDIA_ROOT.
* **format**: one of JPG, PNG, etc.
* **quality**: quality to use for "format"
* **autogen**: if set, the image will be pregenerated, allowing external linking (newsletters, etc).
* **background=RRGGBBAA**: if set, background color to apply to the image (only makes sense on transparent images).
* **fill=RRGGBBAA**: forces the size of the generated image to be the request width and height. Unless "mode" is set to "scale", it behaves exactly as "background=RRGGBBAA".


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
* Unless "autogen=true" is set, it prevents external linking.
* If you set IMAGE_CACHE_ROOT to a directory that is in your public http directory, you can use mod_rewrite or equivalents to have the HTTP server serve the resized images directly.

## Dependencies

* **PIL**: python imaging library is used for image manipualtion. If you want to handle transparency you need at least PIL 1.1.7
* **ffmpeg**: only if you want video thumbnails.

## Known issues
I develop as I need to. Open an issue if you need to fix something or demand any other feature.

* help_text kwarg does not work for ImageCenterField

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
    <img src="{% image '' 'url=http://www.example.com/img.jpg&width=150&height=150&mode=scale&overlay=img/overlay.png' %}"/>

