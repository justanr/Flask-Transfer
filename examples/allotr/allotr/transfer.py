from flask import current_app, flash
from flask_transfer import Transfer, UploadError
import os


UserUpload = Transfer()


def list_files(path):
    files = []
    for name in os.listdir(path):
        path = os.path.join(path, name)
        if os.path.isfile(path):
            files.append(path)
    return files


def really_bad_du(path):
    "Don't actually use this, it's just an example."
    return sum([os.path.getsize(fp) for fp in list_files(path)])


@UserUpload.validator
def check_disk_usage(filehandle, meta):
    """Checks the upload directory to see if the uploaded file would exceed
    the total disk allotment. Meant as a quick and dirty example.
    """
    # limit it at twenty kilobytes if no default is provided
    MAX_DISK_USAGE = current_app.config.get('MAX_DISK_USAGE', 20 * 1024)
    CURRENT_USAGE = really_bad_du(current_app.config['UPLOAD_PATH'])
    filehandle.seek(0, os.SEEK_END)

    if CURRENT_USAGE + filehandle.tell() > MAX_DISK_USAGE:
        filehandle.close()
        raise UploadError("Upload exceeds allotment.")
    filehandle.seek(0)
    return filehandle


@UserUpload.postprocessor
def flash_success(filehandle, meta):
    message = meta.get('message', 'Uploaded {}'.format(filehandle.filename))
    flash(message, 'success')
