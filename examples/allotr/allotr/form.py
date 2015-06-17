from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import SubmitField


class UploadForm(Form):
    upload = FileField(label="Select a file to upload",
                       validators=[FileRequired()])
    submit = SubmitField(label='Engage!')
