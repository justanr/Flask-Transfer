from flask import current_app, url_for
from glob import glob
import os


def get_save_path(filename):
    static_path = current_app.static_folder
    upload_path = current_app.config['UPLOAD_PATH']
    return os.path.join(static_path, upload_path, filename)


def find_jpgs():
    path = os.path.join(current_app.static_folder,
                        current_app.config['UPLOAD_PATH'],
                        '*.jpg')
    return glob(path)


def build_image_links():
    images = []
    for jpg in find_jpgs():
        jpg = os.path.basename(jpg)
        images.append(url_for('display_pdf', pdf=jpg))
    return images
