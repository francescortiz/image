from django.conf import settings
import Image as pil
from cStringIO import StringIO

def do_overlay(img, overlayPath):
	if overlayPath is None:
		return img
	
	overlayPath = os.path.normpath(overlayPath)
	
	overlay = pil.open(settings.STATIC_DOC_ROOT+"/"+overlayPath)
	
	# We want the overlay to fit in the image
	iw, ih = img.size
	ow, oh = overlay.size
	if ow>iw:
		overlay = overlay.resize((iw,iw), pil.ANTIALIAS)
		ow, oh = overlay.size
	if oh>ih:
		overlay = overlay.resize((ih,ih), pil.ANTIALIAS)
		ow, oh = overlay.size
	
	img.paste(overlay, (int((iw-ow)/2),int((ih-oh)/2)), overlay)
	
	return img

def do_mask(img, maskPath):
	if maskPath is None:
		return img
	
	maskPath = os.path.normpath(maskPath)
	
	mask = pil.open(settings.STATIC_DOC_ROOT+"/"+maskPath).convert("RGBA")
	
	r,g,b,a = mask.split()
	img.putalpha(a)

def scaleAndCrop(data, width, height, force=True, overlay=None, mask=None, center=".5,.5"):
	"""Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""
	
	max_width = width
	max_height = height

	input_file = StringIO(data)
	img = pil.open(input_file)
	if img.mode != "RGBA":
		img = img.convert("RGBA")
		
	if not force:
		img.thumbnail((max_width, max_height), pil.ANTIALIAS)
	else:
		src_width, src_height = img.size
		src_ratio = float(src_width) / float(src_height)
		dst_width, dst_height = max_width, max_height
		dst_ratio = float(dst_width) / float(dst_height)
		
		if dst_ratio < src_ratio:
			crop_height = src_height
			crop_width = crop_height * dst_ratio
			x_offset = float(src_width - crop_width) / 2
			y_offset = 0
		else:
			crop_width = src_width
			crop_height = crop_width / dst_ratio
			x_offset = 0
			y_offset = float(src_height - crop_height) / 2
		
		center_x, center_y = center.split(',')
		center_x = float(center_x)
		center_y = float(center_y)
		
		x_offset = min(
			max( 0 , center_x*src_width - crop_width/2 ),
			src_width - crop_width
		)
		y_offset = min(
			max( 0 , center_y*src_height - crop_height/2 ),
			src_height - crop_height
		)
		
		img = img.crop((int(x_offset), int(y_offset), int(x_offset)+int(crop_width), int(y_offset)+int(crop_height)))
		img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)
	
	tmp = StringIO()
	do_overlay(img, overlay)
	do_mask(img, mask)
	
	img.save(tmp, 'PNG')
	tmp.seek(0)
	output_data = tmp.getvalue()
	input_file.close()
	tmp.close()
	
	return output_data

def scale(data, width, height, overlay=None, mask=None):
	"""Rescale the given image, optionally cropping it to make sure the result image has the specified width and height."""
		
	max_width = width
	max_height = height

	input_file = StringIO(data)
	img = pil.open(input_file)
	
	if img.mode != "RGBA":
		img = img.convert("RGBA")
	
	src_width, src_height = img.size
	src_ratio = float(src_width) / float(src_height)
	dst_width = max_width
	dst_height = dst_width / src_ratio
	
	if dst_height > max_height:
		dst_height = max_height
		dst_width = dst_height * src_ratio
	
	img = img.resize((int(dst_width), int(dst_height)), pil.ANTIALIAS)
		
	tmp = StringIO()
	do_overlay(img, overlay)
	do_mask(img, mask)
	
	img.save(tmp, 'PNG')
	tmp.seek(0)
	output_data = tmp.getvalue()
	input_file.close()
	tmp.close()
	
	return output_data


