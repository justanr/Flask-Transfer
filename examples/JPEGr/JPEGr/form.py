from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField, IntegerField


class UploadForm(Form):
    pdf = FileField(
        label='Select a PDF to Convert:',
        validators=[FileAllowed(upload_set=['pdf']), FileRequired()]
    )

    width = IntegerField(label='New Width')
    submit = SubmitField('Convert!')
