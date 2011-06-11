# -*- coding: UTF-8 -*-

from django import template
from django.template.defaulttags import register
from django.core.urlresolvers import reverse
from image.video_field import VideoField, VideoFieldFile

class ImageNode(template.Node):
    def __init__(self, image_field, parameters):
        self.image_field = template.Variable(image_field)
        self.parameters = template.Variable(parameters)
    def render(self, context):
        image_field = self.image_field.resolve(context)
        try:
            parameters = self.parameters.resolve(context)
        except template.VariableDoesNotExist:
            parameters = self.parameters
        
        if isinstance(image_field, VideoFieldFile):
            parameters+="&video=true"
        
        return reverse(
            'image.views.image',
            args=(
                str(image_field),
                parameters+"&center="+image_field.__image_center_instance__.__unicode__()
            )
        )

@register.tag(name="image")
def image(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, image_field, parameters = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires 2 arguments " % token.contents.split()[0]
    
    return ImageNode(image_field, parameters)