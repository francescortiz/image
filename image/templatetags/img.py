# -*- coding: UTF-8 -*-

from django import template
from django.template.defaulttags import register
from django.core.urlresolvers import reverse
from django.db.models.fields.files import ImageFieldFile
import os
from image.storage import IMAGE_CACHE_STORAGE
from image.video_field import VideoFieldFile
from image import views as image_views
from image.utils import image_create_token


def image_tokenize(session, parameters):
    if session:
        token = None
        for k, v in session.items():
            if v == parameters:
                token = k
                break
        if token is None:
            token = image_create_token(parameters)
            session[token] = parameters
    else:
        token = image_create_token(parameters)
    return token


class ImageNode(template.Node):
    def __init__(self, image_field, parameters):
        self.image_field = template.Variable(image_field)
        self.parameters = template.Variable(parameters)

    def render(self, context):
        try:
            request = context['request']
            session = request.session
        except KeyError:
            session = None

        image_field = self.image_field.resolve(context)
        try:
            parameters = self.parameters.resolve(context)
        except template.VariableDoesNotExist:
            parameters = self.parameters

        if isinstance(image_field, VideoFieldFile):
            parameters += "&video=true"

        if isinstance(image_field, ImageFieldFile) or isinstance(image_field, VideoFieldFile):
            try:
                parameters = parameters + "&center=" + image_field.__image_center_instance__.__unicode__()
            except AttributeError:
                pass

        if "autogen=true" in parameters:
            # We want the image to be generated immediately
            image_views.image(None, str(image_field), parameters, True)

        return IMAGE_CACHE_STORAGE.url(os.path.join(unicode(image_field), image_tokenize(session, parameters)))

        # return reverse(
        #     'image.views.image',
        #     args=(
        #         str(image_field),
        #         image_tokenize(session, parameters)
        #     )
        # )


@register.tag(name="image")
def image(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, image_field, parameters = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires 2 arguments " % token.contents.split()[0]

    return ImageNode(image_field, parameters)
