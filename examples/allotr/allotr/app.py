from flask import flash, url_for, redirect, render_template, Flask
from flask_bootstrap import Bootstrap
from flask_transfer import UploadError
from .transfer import UserUpload, really_bad_du, list_files
from .form import UploadForm
import os

app = Flask(__name__)
Bootstrap(app)
app.config['UPLOAD_PATH'] = os.path.join(app.static_folder, 'uploads')
app.config['SECRET_KEY'] = "it's a secret to everybody"
app.config['MAX_UPLOAD_SIZE'] = 20 * 1024


@app.before_first_request
def create_upload_dir():
    if not os.path.exists(app.config['UPLOAD_PATH']):
        os.makedirs(app.config['UPLOAD_PATH'])


@app.errorhandler(UploadError)
def flash_upload_error(error):
    flash(error.args[0], 'error')
    flash('Redirecting to home', 'error')
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
def index():
    form = UploadForm()
    if form.validate_on_submit():
        destination = os.path.join(app.config['UPLOAD_PATH'],
                                   form.upload.data.filename)
        UserUpload.save(form.upload.data, destination=destination)

    max = app.config['MAX_UPLOAD_SIZE'] // 1024
    current = really_bad_du(app.config['UPLOAD_PATH']) // 1024
    files = [os.path.basename(fp) for fp in list_files(app.config['UPLOAD_PATH'])]

    return render_template('index.html', form=form, max=max,
                           current=current, files=files)
