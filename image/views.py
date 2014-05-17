# -*- coding: UTF-8 -*-
from django.conf import settings
from django.http import HttpResponse, QueryDict
from django.http.response import Http404
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.utils.http import urlquote, http_date
from image.utils import scale, scaleAndCrop, IMAGE_DEFAULT_FORMAT, IMAGE_DEFAULT_QUALITY,\
    image_create_token
from urllib import unquote
import os
from image.videothumbs import generate_thumb
from encodings.base64_codec import base64_decode
import urllib
from django.utils.encoding import smart_unicode
from image.image_error import image_text
import traceback

IMAGE_ERROR_NOT_FOUND = getattr(settings, 'IMAGE_ERROR_NOT_FOUND', "Image not found")
IMAGE_ERROR_NOT_VALID = getattr(settings, 'IMAGE_ERROR_NOT_VALID', "Image not valid")
IMAGE_WRONG_REQUEST = getattr(settings, 'IMAGE_WRONG_REQUEST', "Wrong request")
IMAGE_HTTP_CACHE_EXPIRATION = getattr(settings, 'IMAGE_HTTP_CACHE_EXPIRATION', 3600 * 24 * 30)

#@cache_page(60 * 15)
def image(request, path, token, autogen=False):

    is_admin = False
    if ("is_admin=true" in token and request and request.user.has_perm('admin')) or autogen:
        parameters = token
        is_admin = True
        if autogen:
            token = image_create_token(parameters)
    else:
        parameters = request.session.get(token, token)

    path = os.path.normcase(path)
    
    cached_image_path = settings.IMAGE_CACHE_ROOT + "/" + path + "/"
    cached_image_file = cached_image_path + token

    now = timezone.now()
    expire_offset = timezone.timedelta(seconds=IMAGE_HTTP_CACHE_EXPIRATION)

    response = HttpResponse()
    response['Content-type'] = 'image/jpeg'
    response['Expires'] = (now + expire_offset).strftime("%a, %d %b %Y %T GMT")
    response['Last-Modified'] = now.strftime("%a, %d %b %Y %T GMT")
    response['Cache-Control'] = 'max-age=3600, must-revalidate'
    response.status_code = 200

    # If we already have the cache we send it instead of recreating it
    if os.path.exists(smart_unicode(cached_image_file)):
        
        if autogen:
            return 'Already generated'
        
        try:
            f = open(cached_image_file, "r")
        except IOError:
            raise Http404()
        response.write(f.read())
        f.close()

        response['Last-Modified'] = http_date(os.path.getmtime(cached_image_file))
        return response
    
    if parameters == token and not is_admin:
        return HttpResponse("Forbidden", status=403)

    qs = QueryDict(parameters)

    ROOT_DIR = settings.MEDIA_ROOT
    try:
        if qs['static'] == "true":
            ROOT_DIR = settings.STATIC_ROOT
    except KeyError:
        pass

    format = qs.get('format', IMAGE_DEFAULT_FORMAT)
    quality = int(qs.get('quality', IMAGE_DEFAULT_QUALITY))
    mask = qs.get('mask', None)
    mask_source = qs.get('mask_source', None)

    if mask is not None:
        format = "PNG"

    fill = qs.get('fill', None)
    background = qs.get('background', None)
    tint = qs.get('tint', None)

    center = qs.get('center', ".5,.5")
    mode = qs.get('mode', "crop")
        
    overlays = qs.getlist('overlay')
    overlay_sources = qs.getlist('overlay_source')
    overlay_tints = qs.getlist('overlay_tint')
    overlay_sizes = qs.getlist('overlay_size')
    overlay_positions = qs.getlist('overlay_position')

    width = int(qs.get('width', None))
    height = int(qs.get('height', None))
    try:
        padding = float(qs.get('padding',None))
    except TypeError:
        padding = 0.0

    if "video" in qs:
        data, http_response = generate_thumb(ROOT_DIR + "/" + smart_unicode(path), width=width, height=height)
        response.status_code = http_response
    else:
        try:
            try:
                f = urllib.urlopen(qs['url'])
                data = f.read()
                f.close()
            except KeyError:
                f = open(ROOT_DIR + "/" + smart_unicode(path), 'r')
                data = f.read()
                f.close()
        except IOError:
            response.status_code = 404
            #data = image_text(IMAGE_ERROR_NOT_FOUND, width, height)
            data = ""

    if data:
        try:
            if mode == "scale":
                output_data = scale(data, width, height, path, padding=padding, overlays=overlays, overlay_sources=overlay_sources, overlay_tints=overlay_tints, overlay_positions=overlay_positions, overlay_sizes=overlay_sizes, mask=mask, mask_source=mask_source, format=format, quality=quality, fill=fill, background=background, tint=tint)
            else:
                output_data = scaleAndCrop(data, width, height, path, True, padding=padding, overlays=overlays, overlay_sources=overlay_sources, overlay_tints=overlay_tints, overlay_positions=overlay_positions, overlay_sizes=overlay_sizes, mask=mask, mask_source=mask_source, center=center, format=format, quality=quality, fill=fill, background=background, tint=tint)
        except IOError:
            traceback.print_exc()
            response.status_code = 500
            #output_data = image_text(IMAGE_ERROR_NOT_VALID, width, height)
            output_data = ""
    else:
        output_data = data

    if response.status_code == 200:
        if not os.path.exists(cached_image_path):
            os.makedirs(cached_image_path)
    
        f = open(cached_image_file, "w")
        f.write(output_data)
        f.close()
        if autogen:
            return 'Generated ' + str(response.status_code)
    else:
        if autogen:
            return 'Failed ' + cached_image_file
    
    response.write(output_data)

    return response


def crosshair(request):

    response = HttpResponse()
    response['Content-type'] = 'image/png'
    response['Expires'] = 'Fri, 09 Dec 2327 08:34:31 GMT'
    response['Last-Modified'] = 'Fri, 24 Sep 2010 11:36:29 GMT'
    output, length = base64_decode('iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAAwElEQVQoz6WTwY0CMQxFX7DEVjCShUQnc6YCdzCH1EYDboICphb28veA2UULSBHzLpEif9vfcRr/kHQF9jzz3Vr74hWSLpKUmYoIubvMTO6uiFBmqri8FPbeBazAAhwBq3MB1t77c4IH4flNy9T9+Z7g12Nm3iu+Ez4mWMvCFUmKCFVrIywRcasuSe6u8jbC0d3/xGamGs4IZmaSpB3ANE0Ah0HxoeLZAczzDHAaFJ8qfuO0N73z5g37dLfbll/1A+4O0Wm4+ZiPAAAAAElFTkSuQmCC')
    response.write(output)
    return response
