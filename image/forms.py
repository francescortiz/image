# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import six
from django import forms
from django.forms.utils import flatatt
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

try:
    from django.core.urlresolvers import reverse
except ImportError:
    from django.urls import reverse
import threading


from image.video_field import VideoField


COUNTER = 0


class ImageCenterFormWidget(forms.Widget):

    #def __init__(self, attrs=None):
    #    super(ImageCenterFormWidget, self).__init__(attrs)

    def _format_value(self, value):
        return six.text_type(value)

    def render(self, name, value, attrs=None, **kwargs):

        global COUNTER

        if value is None:
            value = ''
        attrs = attrs or {}
        try:
            final_attrs = self.build_attrs(attrs, name=name)
        except TypeError:
            final_attrs = self.build_attrs(attrs, {"name": name})
        if value != '':
            # Only add the 'value' attribute if a value is non-empty.
            final_attrs['value'] = force_str(self._format_value(value))

        resp = ''
        if getattr(value, 'image_path', None):
            try:
                extra_parms = ""
                if isinstance(value.image_field, VideoField):
                    extra_parms += "&video=true"

                extra_parms += "&is_admin=true&autogen=true"
                from image.misc import get_image_url

                preview_url = get_image_url(
                    value.image_path,
                    'format=png&width=150&height=150&mode=scale' + extra_parms,
                )

                resp = '<div style="display:inline-block; position:relative; border:1px solid black;">'
                resp += '<img id="image_center-' + str(COUNTER) + '" src="' + preview_url + '" onclick=""/>'
                resp += '<img id="image_center_crosshair-' + str(COUNTER) + '" src="' + reverse('image.views.crosshair') + '" style="position:absolute; left:0; top:0;" />'
                resp += '</div>'
                resp += '<script>'
                resp += '(function() {'
                resp += '    window.addEventListener("load", function(){'
                resp += '        var crosshair = document.getElementById("image_center_crosshair-' + str(COUNTER) + '");'
                resp += '        var image = document.getElementById("image_center-' + str(COUNTER) + '");'
                resp += '        if (!crosshair || !image) return;'
                resp += '        var container = image.parentNode;'
                resp += '        var wrapper = container.parentNode;'
                resp += '        var input = wrapper ? wrapper.querySelector("input") : null;'
                resp += '        var iw = image.clientWidth || image.width;'
                resp += '        var ih = image.clientHeight || image.height;'
                resp += '        crosshair.style.left = (iw*' + str(value.x) + ' - 7)+"px";'
                resp += '        crosshair.style.top = (ih*' + str(value.y) + ' - 7)+"px";'
                resp += '        if (input) input.style.display = "none";'
                resp += '        container.addEventListener("click", function(e){'
                resp += '            var rect = image.getBoundingClientRect();'
                resp += '            var nx = e.clientX - rect.left;'
                resp += '            var ny = e.clientY - rect.top;'
                resp += '            var curW = image.clientWidth || image.width;'
                resp += '            var curH = image.clientHeight || image.height;'
                resp += '            crosshair.style.left=(nx - 7)+"px";'
                resp += '            crosshair.style.top=(ny - 7)+"px";'
                resp += '            if (input && curW && curH) input.value = (nx/curW)+","+(ny/curH);'
                resp += '        });'
                resp += '    });'
                resp += '})();'
                resp += '</script>'
                resp += u'<input%s />' % flatatt(final_attrs)

                lock = threading.Lock()
                with lock:
                    COUNTER += 1
                    if COUNTER > 4000000000:
                        COUNTER = 0
            except AttributeError:
                resp = 'Only available once the image has been saved'

        return mark_safe(resp)


class ImageCenterFormField(forms.Field):

    widget = ImageCenterFormWidget

    def __init__(self, *args, **kwargs):
        kwargs['required'] = False
        super(ImageCenterFormField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = self.to_python(value)
        return value
