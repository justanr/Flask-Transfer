__all__ = ['Transfer']

from werkzeug._compat import string_types
from .exc import UploadError


def _use_filehandle_to_save(dest):
    def saver(filehandle, metadata):
        "Uses the save method on the filehandle to save to the destination"
        buffer_size = metadata.get('buffer_size', 16384)
        filehandle.save(dest, buffer_size)
    return saver


class Transfer(object):
    """A Transfer object is a self-contained validators, processor and saver.
    These items can be provided at instantiation time, or provided later
    through decorators (for validators and processors) or at save time
    (for saving mechanisms).

    For saving, he destination can be a string path, a writable object
    or a callable that will do something with the filehandle. Transfer will
    handle transforming these as needed. The precedence is callables then
    writables then string paths. All three of these are valid inputs to
    Transfer's `destination` param

    .. code-block:: python

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

    def __init__(self, destination=None, validators=None, preprocessors=None,
                 postprocessors=None):
        if destination is not None:
            self._destination = self.postprocessor_make_destination_callable(destination) # noqa
        else:
            self._destination = None
        self._validators = validators or []
        self._preprocessors = preprocessors or []
        self._postprocessors = postprocessors or []

    def validator(self, fn):
        """Adds a validator to the Transfer instance

        .. code-block:: python

            from wand.image import Image
            ImageTransfer = Transfer()

            @ImageTransfer.validator
            def has_appropirate_dimensions(filehandle, metadata):
                with Image(file=filehandle.stream) as img:
                    height, width = img.height, img.width

                return (height <= metadata['height'] and
                        width <= metadata['width'])
        """
        self._validators.append(fn)
        return fn

    def preprocessor(self, fn):
        """Adds a preprocessor to the Transfer instance.

        .. code-block:: python

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
        """Adds a postprocessor ito the Transfer instance.

        .. code-block:: python

            from wand.image import Image

            ImageTransfer = Transfer(validators=[AllowedExts('png', 'jpg')])

            @ImageTransfer.postprocessor
            def thumbnailify(filehandle, meta):
                with Image(file=filehandle.stream) as img:
                    img.resolution = meta['resolution']
                    ratio = meta['width'] / img.width
                    img.resize(width, int(ratio * img.height)
                    img.save(filename=meta['thumbnail_path'])
        """
        self._postprocessors.append(fn)
        return fn

    def _validate(self, filehandle, metadata, catch_all_errors=False):
        """Runs all attached validators on the provided filehandle.
        The result of `_validate` isn't checked in `Transfer.save`, rather
        validators are expected to raise UploadError to report failure.

        `_validate` can optionally catch all UploadErrors that occur or bail out
        and the first one by toggling the `catch_all_errors` flag. If
        catch_all_errors is Truthy then a single UploadError is raised
        consisting of all UploadErrors raised.
        """
        errors = []

        for validator in self._validators:
            try:
                validator(filehandle, metadata)
            except UploadError as err:
                if not catch_all_errors:
                    raise
                else:
                    errors.append(err)

        if errors:
            raise UploadError(*[str(e) for e in errors])
        else:
            return True

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
             validate=True, catch_all_errors=False, *args, **kwargs):
        """Saves the filehandle to the provided destination or the attached
        default destination. Allows passing arbitrary positional and keyword
        arguments to the saving mechanism

        :param filehandle: werkzeug.FileStorage instance
        :param dest: String path, callable or writable destination to pass the
            filehandle off to. Transfer handles transforming a string or
            writable object into a callable automatically.
        :param metadata: Optional mapping of metadata to pass to validators,
            preprocessors, and postprocessors.
        :param validate boolean: Toggle validation, defaults to True
        :param catch_all_errors boolean: Toggles if validation should collect
            all UploadErrors and raise a collected error message or bail out on
            the first one.
        """
        destination = destination or self._destination
        if destination is None:
            raise RuntimeError("Destination for filehandle must be provided.")

        elif destination is not self._destination:
            destination = self._make_destination_callable(destination)

        if metadata is None:
            metadata = {}

        if validate:
            self._validate(filehandle, metadata)

        filehandle = self._preprocess(filehandle, metadata)
        destination(filehandle, metadata)
        self._postprocess(filehandle, metadata)

    @staticmethod
    def _make_destination_callable(dest):
        if callable(dest):
            return dest
        elif hasattr(dest, 'write') or isinstance(dest, string_types):
            return _use_filehandle_to_save(dest)
        else:
            raise TypeError("Destination must be a string, writable or callable object.")  #noqa
