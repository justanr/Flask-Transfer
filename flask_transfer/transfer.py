"""
    flask_transfer.transfer
    ~~~~~~~~~~~~~~~~~~~~~~~
    Home location of the Transfer class and its helpers.
"""
__all__ = ['Transfer']

from werkzeug._compat import string_types


def _use_filehandle_to_save(dest):
    def saver(filehandle, *args, **kwargs):
        "Uses the save method on the filehandle to save to the destination"
        filehandle.save(dest, *args, **kwargs)
    return saver


def _make_destination_callable(dest):
    if callable(dest):
        return dest
    elif hasattr(dest, 'write') or isinstance(dest, string_types):
        return _use_filehandle_to_save(dest)
    else:
        raise TypeError("Destination must be a string, writable or callable object.")  #noqa


class Transfer(object):
    def __init__(self, destination=None, validators=None, preprocessors=None,
                 postprocessors=None):
        """Instantiates a Transfer object with the provided default destination,
        validators, preprocessors and postprocessors.

        The destination can be a string path, a writable object or a callable
        that will do something with the filehandle. Transfer will handle
        transforming these as needed. The precedence is callables then
        writables then string paths. All three of these are valid inputs to
        Transfer's `destination` param::

            # use callable to handle persisting
            def _save_to_current_user_dir(filehandle, *args, **kwargs):
                "Saves a file to the current user's directory"
                name = g.current_user.name
                path = current_app.config.get('USER_UPLOAD_DIR')
                fullpath = os.path.join(path, filehandle.name)
                filehandle.save(fullpath)

            Transfer(destination=_save_to_current_user_dir)

            # writeable object
            Transfer(destination=BytesIO())

            # string path name
            Transfer(destination="path/to/uploads")

        `destination` may also be None, but a destination *must* be provided
        when saving.

        :param destination: Default destination to pass filehandles to.
        Callables, writables and string paths are all acceptable inputs.
        None may be provided to specify no default path.
        :param validators: List-like of validations to run against the
        filehandle. May be None to run no validations.
        :param preprocessors: List-like of processors to run on the filehandle
        before passing it to the destination. May be None to run no pre
        processing.
        :param postprocessors: List-like of processors to run on the filehandle
        after passing it to the destination. Maybe be None to run no post
        processing.
        """
        if destination is not None:
            self._destination = _make_destination_callable(destination)
        else:
            self._destination = None
        self._validators = validators or []
        self._preprocessors = preprocessors or []
        self._postprocessors = postprocessors or []

    def validator(self, fn):
        """Adds a validator to the Transfer instance::
            from wand.image import Image
            Images = Transfer()

            @Images.validator
            def has_appropirate_dimensions(filehandle, metadata):
                with Image(file=filehandle.stream) as img:
                    height, width = img.height, img.width

                return height <= metadata['height'] and \
                    width <= metadata['width']
        """
        self._validators.append(fn)
        return fn

    def preprocessor(self, fn):
        """Adds a preprocessor to the Transfer instance.::
            Text = Transfer(validators=[AllowedExts('txt'))

            @Text.preprocessor
            def make_uppercase(filehandle, meta):
                "Makes a text document all uppercase"
                filehandle.stream = filehandle.stream.upper()
                return filehandle
        """
        self._preprocessors.append(fn)
        return fn

    def postprocessor(self, fn):
        """Adds a postprocessor to the Transfer instance.::
            from wand.image import Image

            Images = Transfer(validators=[AllowedExts('png', 'jpg')])

            @Images.postprocessor
            def thumbnailify(filehandle, meta):
                with Image(file=filehandle.stream) as img:
                    img.resolution = meta['resolution']
                    ratio = meta['width'] / img.width
                    img.resize(width, int(ratio * img.height)
                    if 'thumbnail_file' in meta:
                        img.save(file=meta['thumbnail_file'])
                    else:
                        img.save(file=meta['thumbnail_path'])
        """
        self._postprocessors.append(fn)
        return fn

    def _validate(self, filehandle, metadata):
        "Runs all attached validators on the provided filehandle."
        return all(validator(filehandle, metadata)
                   for validator in self._validators)

    def _preprocess(self, filehandle, metadata):
        "Runs all attached preprocessors on the provided filehandle."
        for process in self._preprocessors:
            filehandle = process(filehandle, metadata)
        return filehandle

    def _postprocess(self, filehandle, metadata):
        "Runs all attached postprocessors on the provided filehandle."
        for process in self._postprocessors:
            filehandle = process(filehandle, metadata)
        return filehandle

    def save(self, filehandle, destination=None, metadata=None,
             validate=True, *args, **kwargs):
        """Saves the filehandle to the provided destination or the attached
        default destination. Allows passing arbitrary positional and keyword
        arguments to the saving mechanism

        :param filehandle: werkzeug.FileStorage instance
        :param dest: String path, callable or writable destination to pass
        the filehandle off to. Transfer handles transforming a string or
        writable object into a callable automatically.
        :param metadata: Optional mapping of metadata to pass to pre and post
        processors.
        :param validate boolean: Toggle validation, defaults to True
        :param args: Positional arguments to pass to destination callable
        :param kwargs: Keyword arguments to pass to destination callable
        """
        destination = destination or self._destination
        if destination is None:
            raise RuntimeError("Destination for filehandle must be provided.")
        elif destination is not self._destination:
            destination = _make_destination_callable(destination)

        if metadata is None:
            metadata = {}

        if validate:
            self._validate(filehandle, metadata)

        filehandle = self._preprocess(filehandle, metadata)
        destination(filehandle, *args, **kwargs)
        self._postprocess(filehandle, metadata)
