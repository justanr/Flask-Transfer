from flask import flash
from flask_transfer import Transfer
from io import BytesIO
from itertools import count
import os
from wand.image import Image
from wand.color import Color
from werkzeug import secure_filename
from .utils import get_save_path

PDFTransfer = Transfer()


@PDFTransfer.preprocessor
def pdftojpg(filehandle, meta):
    """Converts a PDF to a JPG and places it back onto the FileStorage instance
    passed to it as a BytesIO object.

    Optional meta arguments are:
        * resolution: int or (int, int) used for wand to determine resolution,
        defaults to 300.
        * width: new width of the image for resizing, defaults to 1080
        * bgcolor: new background color, defaults to 'white'
    """
    resolution = meta.get('resolution', 300)
    width = meta.get('width', 1080)
    bgcolor = Color(meta.get('bgcolor', 'white'))
    stream = BytesIO()

    with Image(blob=filehandle.stream, resolution=resolution) as img:
        img.background_color = bgcolor
        img.alpha_channel = False
        img.format = 'jpeg'
        ratio = width / img.width
        img.resize(width, int(ratio * img.height))
        img.compression_quality = 90
        img.save(file=stream)

    stream.seek(0)
    filehandle.stream = stream
    return filehandle


@PDFTransfer.preprocessor
def change_filename(filehandle, meta):
    """Changes the filename to reflect the conversion from PDF to JPG.
    This method will preserve the original filename in the meta dictionary.
    """
    filename = secure_filename(meta.get('filename', filehandle.filename))
    basename, _ = os.path.splitext(filename)
    meta['original_filename'] = filehandle.filename
    filehandle.filename = filename + '.jpg'
    return filehandle


@PDFTransfer.preprocessor
def avoid_name_collisions(filehandle, meta):
    """Manipulates a filename until it's unique. This can be disabled by
    setting meta['avoid_name_collision'] to any falsey value.
    """
    if meta.get('avoid_name_collision', True):
        filename = filehandle.filename
        original, ext = os.path.splitext(filehandle.filename)
        counter = count()
        while os.path.exists(get_save_path(filename)):
            fixer = str(next(counter))
            filename = '{}_{}{}'.format(original, fixer, ext)
        filehandle.filename = filename
    return filehandle


@PDFTransfer.postprocessor
def flash_success(filehandle, meta):
    flash('Converted {} to {}'.format(
        meta['original_filename'], filehandle.filename),
        'success')
    return filehandle


def pdf_saver(filehandle, *args, **kwargs):
    "Uses werkzeug.FileStorage instance to save the converted image."
    fullpath = get_save_path(filehandle.filename)
    filehandle.save(fullpath, buffer_size=kwargs.get('buffer_size', 16384))
