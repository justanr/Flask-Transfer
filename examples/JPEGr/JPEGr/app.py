from .config import Config
from .form import UploadForm
from .transfer import PDFTransfer, pdf_saver
from . import utils
from flask import (Flask, render_template, redirect, abort,
                   url_for, send_from_directory)
from flask_bootstrap import Bootstrap
import os


app = Flask(__name__)
app.config.from_object(Config)
Bootstrap(app)
Config.init_app(app)


@app.route('/')
def index():
    return render_template('index.html', links=utils.build_image_links())


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    form = UploadForm()
    if form.validate_on_submit():
        meta = {'width': form.width.data or 1080}
        PDFTransfer.save(form.pdf.data, destination=pdf_saver, metadata=meta)
        return redirect(url_for('index'))
    else:
        return render_template('upload.html', form=form)


@app.route('/pdf/<pdf>')
def display_pdf(pdf):
    path = utils.get_save_path(pdf)
    if not os.path.exists(path):
        abort(404)
    else:
        return send_from_directory(*os.path.split(path))
