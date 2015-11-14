
Flask-Transfer
==============

Validate, process and persist file uploads easily through a single
object instead of cramming all that stuff into your routes.

Tired of this?
--------------

.. code:: python

    @app.route('/upload', methods=['GET', 'POST'])
    def handle_upload():
        form = FileUploadForm()
        
        if form.validate_on_submit():
            filehandle = form.uploaded.data
            allowed_exts = ('md', 'txt', 'rst')
            if not os.path.splitext(filehandle.filename)[1] in allowed_exts:
                raise SomeError('Unallowed extension!')
            if filehandle.read() != b'Hello World!':
                raise SomeError('File contents not allowed!')
            filehandle.seek(0)
            
            username = g.current_user.name
            upload_dir = current_app.config['UPLOAD_DIR']
            full_path = os.path.join(upload_dir, username, secure_filename(filehandle.filename))
            filehandle.save(full_path)
            flash("Uploaded {}!".format(filehandle.filename), 'success')
            return redirect(url_for('handle_upload'))
        else:
            return render_template('upload.html', form=form)

That's a mess. Your test runner is literally running away from you.
There's like four or five different things going on in this single
route! Argh.

There's a better way
--------------------

.. code:: python

    from flask_transfer import Transfer, UploadError
    from flask_transfer.validators import AllowedExts
    
    TextFileTransfer = Transfer(validators=[AllowedExts('md', 'rst', 'txt')])
    
    @TextFileTransfer.destination
    def save_to_user_dir(filehandle, metadata):
        username = g.current_user.name
        upload_path = current_app.config['UPLOAD_DIR']
        full_path = os.path.join(upload_dir, username, secure_filename(filehandle.filename))
        filehandle.save(full_path)
    
    
    @TextFileTransfer.validator
    def check_file_contents(filehandle, metadata):
        if filehandle.read() != metadata['allowed_contents']:
            raise UploadError('File contents not allowed!')
        filehandle.seek(0)
        return True
    
    
    @app.route('/upload', methods=['GET', 'POST'])
    def handle_upload():
        form = FileUploadForm()
        
        if form.validate_on_submit():
            filehandle = form.uploaded.data
            TextFileTransfer.save(filehandle, metadata={'allowed_contents': b'Hello World!'})
            flash('Uploaded {}!'.format(filehandle.filename), 'success')
            return redirect(url_for('handle_upload'))
        else:
            return render_template('upload.html', form=form)

Aaaah. Sure, it's a little bit more code. But it's separated out into
bits and pieces. It's easy to test each bit and the intent in the route
is very clear.

More Power
----------

Flask-Transfer supplies hooks for validation, preprocessing and
postprocessing file uploads via decorators. If you need to always create
thumbnails of uploaded images, you can supply a callable to
``MyTransfer.preprocessor`` or ``MyTransfer.postprocessor`` that'll do
that for you.

And validation beyond just simple extension checking is at your
fingertips as well. Perhaps, you've limited your user to a certain
amount of disk space and they should be told to delete data before
uploading more. Write a simple function to check current disk usage and
if the upload would exceed the cap. Then hook it to your Transfer object
with ``MyTransfer.validator``.

Finally, persisting files is easy! Maybe you're running on Heroku and
can't rely on the local filesystem. Just write a callable that'll pass
the file to your S3 bucket! Hook it in with ``MyTransfer.destination``.
Flask-Transfer handles using string paths and writable objects as
destinations as well.

Check out the `quickstart <quickstart.rst>`__ for some more information,
as well!

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
