# -*- cpding: UTF-8 -*-
from PIL import ImageFont, Image, ImageDraw
import os
import re
from django.conf import settings
from StringIO import StringIO

IMAGE_FONT_FILE = '/'.join(os.path.realpath(__file__).split('/')[:-1]) + "/FreeSans.ttf"
IMAGE_FONT_FILE = getattr(settings, 'IMAGE_FONT_FILE', IMAGE_FONT_FILE)
IMAGE_FONT_LINE_HEIGHT = getattr(settings, 'IMAGE_FONT_LINE_HEIGHT', .7)
IMAGE_FONT_BACKGROUND = getattr(settings, 'IMAGE_FONT_BACKGROUND', (255, 255, 255, 255))
IMAGE_FONT_FOREGROUND = getattr(settings, 'IMAGE_FONT_FOREGROUND', (0, 0, 0, 255))


def fit_to_width(msg, font, width):
    lines = re.split('\n', msg)
    y_offset = 0
    output_lines = []
    current_line = ""
    max_w = 0
    start_y = 0
    h = 0
    for j in range(len(lines)):
        line = lines[j]
        words = re.split('\s+', line)
        first_word = True
        y_offset += int(h * IMAGE_FONT_LINE_HEIGHT)
        for i in range(len(words)):
            word = words[i]
            if i == 0:
                previous_line = current_line
                current_line = word
            else:
                previous_line = current_line
                current_line += " " + word

            first_word = False
            w, h = font.getsize(current_line)
            if start_y == 0:
                start_y = -int((1 - IMAGE_FONT_LINE_HEIGHT) * h / 2)
            if w > width:
                y_offset += int(h * IMAGE_FONT_LINE_HEIGHT)
                output_lines.append(previous_line)
                w, h = font.getsize(previous_line)
                current_line = word
            # We get the max_w after all arrangements have been performed
            max_w = max(w, max_w)

        if current_line:
            output_lines.append(current_line)
            w, h = font.getsize(current_line)
            # make sure hte last line isn't longer than all the previous lines
            max_w = max(w, max_w)

    return output_lines, max_w, int(h * IMAGE_FONT_LINE_HEIGHT) + y_offset, start_y


def image_text(msg, width, height):
    size = 10
    font = ImageFont.truetype(IMAGE_FONT_FILE, size)

    lines, w, h, start_y = fit_to_width(msg, font, width)

    while w <= width and h <= height:
        size += 1
        font = ImageFont.truetype(IMAGE_FONT_FILE, size)
        lines, w, h, start_y = fit_to_width(msg, font, width)

    # We for sure oversized
    size -= 1
    font = ImageFont.truetype(IMAGE_FONT_FILE, size)
    lines, w, h, start_y = fit_to_width(msg, font, width)
    while size > 1 and (w > width or h > height):
        size -= 1
        font = ImageFont.truetype(IMAGE_FONT_FILE, size)
        lines, w, h, start_y = fit_to_width(msg, font, width)

    # Render the message
    im = Image.new('RGBA', (width, height), IMAGE_FONT_BACKGROUND)  # Create a blank image with the given size
    draw = ImageDraw.Draw(im)
    x_offset = int((width - w) / 2)
    y_offset = start_y + int((height - h) / 2)
    for line in lines:
        draw.text((x_offset, y_offset), line, font=font, fill=IMAGE_FONT_FOREGROUND)  # Draw text
        y_offset += int(font.getsize(line)[1] * IMAGE_FONT_LINE_HEIGHT)

    tmp = StringIO()
    im.save(tmp, "PNG")
    tmp.seek(0)
    output_data = tmp.getvalue()
    tmp.close()

    return output_data


#error_image("FATAL ERROR: The requested file cannot be found.\nTry to get a loop. FATAL ERROR: The requested file cannot be found.\nTry to get a loop. FATAL ERROR: The requested file cannot be found.\nTry to get a loop.", 150, 130).save('/'.join( os.path.realpath(__file__).split('/')[:-1] )+"/text.png")
