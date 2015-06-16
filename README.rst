
Flask-Transfer
==============

Validate, process and persist uploaded files through a single object
instead of cramming all that stuff into your routes or writing your own
pipeline for it.

Tired of this?
--------------

.. code:: python

    @app.route('/upload', methods=['GET', 'POST'])
    def upload():
        form = UploadForm()
        
        if form.validate_on_submit():
            filehandle = form.uploaded.data
            allowed_exts = ('txt', 'md', 'rst')
            if not os.path.splitext(filehandle.filename)[1] in allowed_exts:
                raise UploadError('File type not allowed!')
            if filehandle.read() != b'hello world':
                raise UploadError('File contents not allowed!')
            # back to beginning
            filehandle.seek()
            username = g.current_user.name
            upload_path = current_app.config['UPLOAD_DIR']
            fullpath = os.path.join(upload_path, username, filehandle.filename)
            filehandle.save(fullpath)
            flash("Uploaded {}!".format(filehandle.filename))
            return redirect(url_for("upload"))
        else:
            return render_template('upload.html', form=form)

Heaven forbid if you need to other validation -- will this file upload
exceed the user's allotment? -- or processing -- gotta make thumbnails,
shove info into the database, etc. Of course, you're a good programmer
and broke all that logic into separate functions...right?

Wouldn't it be nice to place all the validating, processing and saving
logic in one object and just let that handle it for you?

Do this instead
---------------

.. code:: python

    from flask_transfer import Transfer, AllowedExts, UploadError

    def _save_to_user_dir(filehandle):
        current_user = g.current_user
        upload_path = current_app.config['UPLOAD_DIR']
        fullpath = os.path.join(upload_path, current_user, filehandle.filename)
        filehandle.save(fullpath)


    TextDocuments = AllowedExts('txt', 'md', 'rst')
    TextTransfer = Transfer(validators=[TextDocuments], destination=_save_to_user_dir)

    @TextTransfer.validator
    def check_stream_contents(filehandle, metadata):
        if filehandle.read() != metadata['approved_contents']:
            raise UploadError('File contents not allowed')
        filehandle.seek()
        return True

    @app.route('/upload', methods=['GET', 'POST'])
    def upload():
        form = UploadForm()
        
        if form.validate_on_submit():
            filehandle = form.uploaded.data
            TextTransfer.save(filehandle, {})
            flash('Uploaded {}!'.format(filehandle.filename))
            return redirect(url_for('uploaded'))
        else:
            return render_template('upload.html', form=form)

Check out the `quickstart <quickstart.rst>`__ for some more information,
as well!

More Power
----------

Flask-Transfer supplies hooks for validation, preprocessing and
postprocessing via decorators. Need to create thumbnails of images? Just
supply a resizer to the ``Transfer.preprocessor`` or
``Transfer.postprocessor`` hooks.

Validation beyond just checking file extensions is at your fingertips as
well. Look at the current user's disk usage and see if the upload would
exceed the maximum. Just supply a callable to the ``Transfer.validator``
hook.

Maybe you're running on Heroku and you can't persist to the local
filesystem. Create a callable or writable object that'll pipe that data
off to your S3 or Dropbox or the database (oh good god don't do this)
and use that as the destination. Flask-Transfer handles using callables,
writables and string file paths all behind the scenes for you.

Todo
----

There's still quite a bit to do. For example, better error handle.
Perhaps a tighter integration with Flask, or running the opposite way
and cleaving the already few dependencies on werkzeug to become
framework independent.

Contributions
-------------

Given the infancy of this project, pull requests and issue are more than
welcome. Just add yourself to the authors file, write some tests for the
added or change functionality and submit it!
