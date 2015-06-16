
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


Saving
------

Saving with Flask-Transfer is *super* easy. Once you have FileStorage
object (probably from Flask-WTF), just call
``Transfer.save(filehandle)``. That's mostly it. This'll validate the
file, run the preprocessors, persist the file and then call the
postprocessors.

Destinations
~~~~~~~~~~~~

As mentioned before, destinations can be callables, writables or string
file paths (and the preference is in that order, too). The conversion to
a common interface is done behind the scenes for you. There's also two
locations destinations can be provided:

-  At instance creation, to provide a "default" destination.
-  When calling ``Transfer.save`` to provide a more preferential
   destination.

Other stuff
~~~~~~~~~~~

When calling ``Transfer.save`` it's possible to supply metadata to the
validators, preprocessors and postprocessors with the ``metadata``
argument. This can be any object, but defaults to an empty dictionary if
not supplied and probably possible to mutate the object, do what you
will with that information.

Validation can optionally be turned off. Maybe you rely on Flask-WTF to
validate incoming stuff, so doing double validation isn't cool. Just
pass ``validate=False`` to the method.

Finally, if you need to pass positional or keyword arguments down to the
saving mechanism, it's possible to do that as well. ``Transfer.save``
will pass ``*args`` and ``**kwargs`` down to it (and unpack them there
as well).

Validators
----------

Flask-Transfer comes with a handful of predefined validators. Validators
can be loaded into a Transfer object when it's created through the
``validators`` keyword (in this case it should be a list or list-like
object). Or added after the fact with the ``Transfer.validator``
decorator.

.. code:: python

    # load at instance creation
    MyTransfer = Transfer(validators=[ImagesAllowed])

    # load after the fact
    @MyTransfer.validator
    def my_first_validator(filehandle, metadata):
        # do stuff

Extension Validators
~~~~~~~~~~~~~~~~~~~~

There are two extension validators: AllowedExts and DeniedExts. They
both do what you think and creating them is easy peasy:

.. code:: python

    ImagesAllowed = AllowedExts('jpg', 'png', 'gif')
    ImagesDenied = DeniedExts('psd', 'tiff')

Function Validators
~~~~~~~~~~~~~~~~~~~

Already have a perfectly good callable that validates files for you?
Just lift into the Flask-Transfer validator context like this:

.. code:: python

    EvenBetterPerfectlyGood = FunctionValidator(perfectly_good_validator)

``FunctionValidator`` can also be used as a decorator:

.. code:: python

    @FunctionValidator
    def perfectly_good(filehandle, metadata):
        return True

Manipulating Validators
~~~~~~~~~~~~~~~~~~~~~~~

Flask-Transfer also allows combining and negating validators easily. If
you have a condition where *two* things need to be true, there's the
``AndValidator`` and its shortcut ``&``:

.. code:: python

    ImagesAndPerfectlyGood = ImagesAllowed & EvenBetterPerfectlyGood

For conditions that are better expressed as an or, there's
``OrValidator`` and its shortcut ``|``:

.. code:: python

    ImagesOrText = ImagesAllowed | AllowExts('txt', 'md', 'rst')

And for conditions that are the opposite of what they currently are,
there's ``NegatedValidator`` and its shortcut ``~`` (yes, that's a tilde
instead of a subtraction sign):

.. code:: python

    NotImages = ~ImagesAllowed

Just to clarify, that is effectively the same as defining a ``DeniedExts``
with the same extensions.

BYOV: Bring Your Own Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aside from just wrapping a function with FunctionValidator, you can
inherit from ``BaseValidator`` and implement ``_validate``. The only
thing you need to know is that a validator needs to accept a
``werkzeug.FileStorage`` (or whatever you're using internally) instance
and a metadata object (I use dictionaries, but I also make no
presumptions).

Pre and Post processing
-----------------------

Preprocessing happens before saving the filehandle and postprocessing
happens afterwards. Both of these receive the FileStorage instance and a
metadata object (again, dict, object, whatever) and need to return a
FileStorage instance (the same one, a different one, a manipulated one,
doesn't matter). Processors just need to be callable: Functions, classes
with ``__call__``, a method on a class or instance, doesn't matter as
long as it adheres to the calling convention.

Preprocessing
~~~~~~~~~~~~~

These calls are made before calling the save mechanism. Potentially,
they can manipulate the filehandle before it's persisted. Or perhaps use
them to ensure name collision doesn't happen. Or whatever.

Postprocessing
~~~~~~~~~~~~~~

These calls are made after calling the save mechanism. Perhaps after
persisting the filehandle, you need to create thumbnails or shove
something in the database.

Not good enough?
----------------

Subclass ``Transfer`` and do your own thing. Maybe you'd like validators
and processors to map to a dictionary instead of a list.

Contributions
-------------

Given the infancy of this project, pull requests and issue are more than
welcome. Just add yourself to the authors file, write some tests for the
added or change functionality and submit it!
