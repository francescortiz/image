# -*- coding: UTF-8 -*-
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.utils.http import urlquote
from image.utils import scale, scaleAndCrop, IMAGE_DEFAULT_FORMAT, IMAGE_DEFAULT_QUALITY
from urllib import unquote
import os
from image.videothumbs import generate_thumb
from encodings.base64_codec import base64_decode
import urllib
from django.utils.encoding import smart_unicode
from image.image_error import image_text

IMAGE_ERROR_NOT_FOUND = getattr(settings, 'IMAGE_ERROR_NOT_FOUND', "Image not found")
IMAGE_ERROR_NOT_VALID = getattr(settings, 'IMAGE_ERROR_NOT_VALID', "Image not valid")

#@cache_page(60 * 15)
def image(request, path, token):
	
	if "is_admin=true" in token and request.user.has_perm('admin'):
		parameters = token
	else:
		parameters = request.session.get(token,'')
		
	parms = unquote(parameters).split('&')
	qs = {}
	
	for parm in parms:
		parts = parm.split('=')
		qs[parts[0]] = unquote(parts[1])

	path = os.path.normcase(path)
	
	cached_image_path = settings.IMAGE_CACHE_ROOT+"/"+path+"/"
	cached_image_file = cached_image_path+token
	
	response = HttpResponse()
	response['Content-type'] = 'image/jpeg'
	response['Expires'] = 'Fri, 09 Dec 2327 08:34:31 GMT'
	response['Last-Modified'] = 'Fri, 24 Sep 2010 11:36:29 GMT'

	# If we already have the cache we send it instead of recreating it
	if os.path.exists(smart_unicode(cached_image_file)):
		f = open(cached_image_file, "r")
		response.write( f.read() )
		f.close()
		
		return response
		
	ROOT_DIR = settings.MEDIA_ROOT
	try:
		if qs['static'] == "true":
			ROOT_DIR = settings.STATIC_ROOT
	except KeyError:
		pass
	
	
	try:
		format = qs['format']
	except KeyError:
		format = IMAGE_DEFAULT_FORMAT

	try:
		quality = int(qs['quality'])
	except KeyError:
		quality = IMAGE_DEFAULT_QUALITY

	try:
		overlay = qs['overlay']
	except KeyError:
		overlay = None

	try:
		mask = qs['mask']
	except KeyError:
		mask = None

	if mask is not None:
		format = "PNG"

	try:
		center = qs['center']
	except KeyError:
		center = ".5,.5"
	
	try:
		mode = qs['mode']
	except KeyError:
		mode = "crop"
	
	width = int( qs['width'] )
	height = int( qs['height'] )
	
	if qs.has_key("video"):
		data = generate_thumb(ROOT_DIR+"/"+smart_unicode(path))
	else:
		try:
			try:
				f = urllib.urlopen(qs['url'])
				data = f.read()
				f.close()
			except KeyError:
				f = open(ROOT_DIR+"/"+smart_unicode(path), 'r')
				data = f.read()
				f.close()
		except IOError:
			data = image_text(IMAGE_ERROR_NOT_FOUND, width, height)
			
	
	try:
		if mode == "scale":
			output_data = scale(data, width, height, overlay=overlay, mask=mask, format=format, quality=quality )
		else:
			output_data = scaleAndCrop(data, width, height, True, overlay=overlay, mask=mask, center=center, format=format, quality=quality )
	except IOError:
		output_data = image_text(IMAGE_ERROR_NOT_VALID, width, height)
		
	if not os.path.exists(cached_image_path):
		os.makedirs(cached_image_path)
	
	f = open(cached_image_file, "w")
	f.write(output_data)
	f.close()
	
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

	