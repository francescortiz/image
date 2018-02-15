## Introduction

I've seen some plugins that allow you to set the crop images by dragging and resizing a selection area over the original image. The problem with this method is that you need to know cropped sizes when you upload the images and, if there is a change in the design, you have to do all the crops again.

Also, many thumbnailers forget about videos.

This is why I created this image resizing library for django, in which you set the center of attention of an image (or video) and cropping is done **automatically keeping the center of attention** as close to the center of the image as possible. Thanks to this, when people's faces or the significant element of a picture are not centered, you can relay on automatic cropping confident that those items will be respected.

Apart from that, I keep adding the functionalities that I need as I come into new projects. Thanks to this, you can see features like **masking, multiple overlays, tint, fill color** or **background color**.

On a more technical side, another feature of image is that **it does not use presets**. You just set the parameters that you want to use on each place, allowing you to quickly implement it and to easily integrate image with other code. For server security and stability, it relays on tokens and disk cache to keep the server in peace. If you publish this disk cache through **mod_rewrite** or equivalents, you can even skip django from getting image requests.

### What's new

**Version 1.5.18-1.5.19**

- Bugfix for django 2.0 compatibility.

**Version 1.5.17**

- Django 2.0 compatibility.

**Version 1.5.16**

- Add a function named after image.utils.image_url that generates an image url.

**Version 1.5.12**

- Add LocallyMirroredS3BotoStorage to boost S3.

**Version 1.5.11**

- Allow overlays to have their origin in the bottom right corner by adding an exclamation sign to the corresponding coordinate.

**Version 1.5.10**

- Bug fix.

**Version 1.5.9**

- Swap order of arguments in the urls in order to keep original file name.

**Version 1.5.8**

- Bug fix.

**Version 1.5.7**

- Recover backwards compatibility with Django 1.8.

**Version 1.5.6**

- Django 1.11 compatibility.

**Version 1.5.5**

- Work with Django 1.10

**Version 1.4.4**

- Added an option to prevent enlarging images. "enlarge=false" or whatever value different than true. defaults to true for backwards compatibility.

**Version 1.4**

- Added grayscale

**Version 1.4**

- No need to tell width and height. It takes the image dimensions if they are lacking.
- Added pre_rotation and post_rotation. Rotate the image before cropping and applying effects or after.
 
**Version 1.3**

- Added support for django storages
- Code cleanup
- Remove unneeded stuff (font file, some functions).

**Version 1.2.1**

- Better cache response headers

**Version 1.2**

- Lots of improvements

**May 2012**

- parameter "tint=RRGGBBAA" or  "tint=RRGGBBAAII":
    Tints the image. Works equal to overlays.
    See below.

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

### how to install

pip install image
add 'image' to INSTALLED_APPS

## settings variables

### Context Processors

'django.template.context_processors.request' is mandatory because the image tag uses sessions.

### Custom settings

* **IMAGE_DEFAULT_FORMAT**: (default='JPEG') It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_DEFAULT_QUALITY**: (default=85) It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_CACHE_ROOT**: It is the filesystem path where you want cache to be stored. You can use a web public directory. This way, with the appropiate .htaccess rules or server configuration, you can delegate to the http server thumbnail submission once they are already created.

* **IMAGE_CACHE_URL**: (default='/image/') Base url for cached images. If you plan to use Amazon S3 you need this and autogen=true.

* **IMAGE_CACHE_STORAGE**: (default='image.storage.ImageCacheStorage') The storage to use for cached images.

* **IMAGE_CACHE_HTTP_EXPIRATION**: (default=3600 * 24 * 30) What to say to browsers in the HTTP Response headers about cache duration.

* **S3_MIRROR_ROOT**: Directory where local empty files are going to be created. Applies only when using LocallyCachedS3BotoStorage. It serves as a local cache for calls to `.exists()`.


### Dependency on django settings

* **STATIC_ROOT / STATICFILES**: Only if you use overlay or mask.

* **FILE_UPLOAD_TEMP_DIR**: Used to store temporary images when working with videos.


## Storage

### LocallyMirroredS3BotoStorage

Dynamic image generation relies heavily on checking for existance of generated files. S3 is very slow when checking for existance of files. This storage is a simple wrapper that keeps a local cache ef existance of files throgh a local mirror of empty files.


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

### overlay_tint=RRGGBBAAII

II stands for Intensity. Values from 00 to ff. Ammount of tint to apply.

AA and II are optional.

If AA smaller than ff, the layer will become transparent.

Accepts value None (overlay_tint=None).

### overlay_source=media/static

Where to look for overlay, either MEDIA_ROOT or STATIC_ROOT

### overlay_position=X.XX/Y.YY

Origin of the overlay. Centered by default. Percentage from 0.0 to 1.0. **By now it crashes if you place the overlay outside out of bounds.**

### overlay_size=W.WW/H.HH

Size of the overlay of the overlay. Percentage from 0.0 to 1.0. It doesn't allow distortion.


### Examples:

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

* **width**: target width. Set it to a big number if you are scaling to fit vertically.
* **height**: target height. Set it to a big number if you are scaling to fit horizontally.
* **mode**: "scale" or "crop". Defaults to "crop". "scale" will fit the image to the given width and height without loosing proportions. "crop" will fill the given area cropping if necessary.
* **overlay** (multiple values accepted): and overlay image to add on top of the image. It won't be resized. I use it to place a play button on top of video thumbnails. Overlay search path is STATIC_ROOT.
* **overlay_source=media/static** (multiple values accepted): tells where to look for the overlay, either MEDIA_ROOT or STATIC_ROOT.
* **overlay_tint=RRGGBB overlay_tint=RRGGBBAA overlay_tint=RRGGBBAAII** (multiple values accepted): tints the overlay. II stands for intensity. AA different to ff makes the overlay transparent.
* **mask**: a mask image. the mask will be resized to the rendered image size. Mask search path is STATIC_ROOT. **If you set a mask, format switches automatically to PNG**
* **static**: tells image to look for our image in STATIC_ROOT instead of MEDIA_ROOT.
* **format**: one of JPG, PNG, etc.
* **quality**: quality to use for "format"
* **autogen**: if set, the image will be pregenerated, allowing external linking (newsletters, etc).
* **background=RRGGBBAA**: if set, background color to apply to the image (only makes sense on transparent images).
* **fill=RRGGBBAA**: forces the size of the generated image to be the request width and height. Unless "mode" is set to "scale", it behaves exactly as "background=RRGGBBAA".
* **tint=RRGGBB tint=RRGGBBAA tint=RRGGBBAAII**: tints the image. Works like overlay_tint.
* **pre_rotation=DEGREES**: rotates the image before doing any work on it.
* **post_rotation=DEGREES**: rotates the image after doing all the work with it.
* **grayscale=true**: converts the image to grayscale.
* **enlarge**: "true" or anything else. Defaults to "true". If it is true it enlarges images to a size bigger than their original size.


### Other parameters

* **url**: make a thumbnail of the given url. If url is given, [source] is ignored.

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
* **requests**
* **ffmpeg**: only if you want video thumbnails.

## Known issues
I develop as I need to. Open an issue if you need to fix something or demand any other feature.

* help_text kwarg does not work for ImageCenterField

## Examples

Sample model:
from image.fields import ImageCenterField

    class Test(models.Model):
    
        image = ImageField(upload_to="test")
        image_center = ImageCenterField(image_field=image)
        video = VideoField(upload_to="test")
        video_center = ImageCenterField(image_field=video)

Sample urls.py:

    # -*- coding: UTF-8 -*-
    from django.conf.urls import *
    from django.contrib import admin
    admin.autodiscover()
    
    urlpatterns = patterns('',
        (r'^admin/', include(admin.site.urls)),
        (r'^image/', include('image.urls')),
    )

Sample template:

    {% load img %}

    Make a cropped high quality JPEG
    <img src="{% image test.image 'width=150&height=150&format=JPEG&quality=95' %}"/>

    Make a cropped PNG
    <img src="{% image test.video 'width=150&height=150&format=PNG' %}"/>

    Scale a static image
    <img src="{% image path_variable 'width=150&height=150&mode=scale&static=true' %}"/>

    Scale and add overlay to a remote image
    <img src="{% image '' 'url=http://www.example.com/img.jpg&width=150&height=150&mode=scale&overlay=img/overlay.png' %}"/>

## Known bugs

* When using RunPython in migrations the image_center does not get associated to the image field. Check issue [#4](https://github.com/francescortiz/image/issues/4) for a workaround.

## TODO

* Remove the need to specify with and height for images beeing manipulated. Let the system work with the original image size.
* Add the posibility to prevent upscaling.
* Make it possible to set the size of the center of attention, in order to be able to make crops that only show that area.
 



