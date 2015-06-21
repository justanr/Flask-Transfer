"""
"""
from functools import update_wrapper
from os.path import splitext
from .exc import UploadError


class BaseValidator(object):
    """BaseValidator class for flask_transfer. Provides utility methods for
    combining validators together. Subclasses should implement `_validates`.

    When called, the validator will catch TypeError and ValueError wrap them
    in UploadError. Other validators should explictly catch expected error and
    reraise UploadError.
    """

    def _validate(self, filehandle, metadata):
        raise NotImplementedError("_validate not implemented")

    def __call__(self, filehandle, metadata):
        return self._validate(filehandle, metadata)

    def __and__(self, other):
        return AndValidator(self, other)

    def __or__(self, other):
        return OrValidator(self, other)

    def __invert__(self):
        return NegatedValidator(self)

    def __repr__(self):
        return self.__class__.__name__


class AndValidator(BaseValidator):
    """Validator representing a condition where both validators must be true.
    flask_transfer validators can be combined in this fashion with the bitwise
    `&` operator.

    .. code-block:: python

        # trivial example: An existing set of allowed extensions
        # combined with a new set of denied extensions
        Images = AllowedExts("jpg", "gif", "png", "psd") # etc
        NoPSDs = DeniedExts("psd")
        ImagesButNoPSDs = Images & NoPSDs
    """

    def __init__(self, first, second):
        self._first, self._second = first, second

    def _validate(self, filehandle, metadata):
        return self._first(filehandle, metadata) and \
            self._second(filehandle, metadata)

    def __repr__(self):
        return "AndValidator({0!r}, {1!r})".format(self._first, self._second)


class OrValidator(BaseValidator):
    """Validator representing a condition where either validator must be true.
    flask_transfer validators can be combined in this fashion with the bitwise
    `|` operator.

    .. code-block:: python

        Images = AllowedExts("jpg", "gif", "png")
        Text = AllowedExts("txt", "json", "md", "rst")
        ImagesOrText = Images | Text
    """

    def __init__(self, first, second):
        self._first, self._second = first, second

    def _validate(self, filehandle, metadata):
        return self._first(filehandle, metadata) or \
            self._second(filehandle, metadata)

    def __repr__(self):
        return "OrValidator({0!r}, {1!r})".format(self._first, self._second)


class NegatedValidator(BaseValidator):
    """Validators that represents the opposite of its internal validator.
    flask_transfer validators can be negated in this fashion with the bitwise
    `~` unary operator.

    .. code-block:: python

        Images = AllowedExts("jpg", "png", "gif")
        # same as creating DeniedExts("jpg", "png", "gif")
        NoImages = ~Images

    :NOTE: `~` was chosen because it is *always* unary, unlike `-` which might
        be an unary or a binary operator.
    """
    def __init__(self, validator):
        self._validator = validator

    def _validate(self, filehandle, metadata):
        return not self._validator(filehandle, metadata)

    def __repr__(self):
        return "NegatedValidator({!r})".format(self._validator)


class FunctionValidator(BaseValidator):
    """Used to lift a function into the validator environment, allowing it to
    access the &, | and ~ shortcuts for combination and negation.

    FunctionValidator presents as the wrapped function.

    .. code-block:: python

        def check_filename_length(filehandle):
            return len(filehandle.filename) >= 5

        CheckFilenameLength = FunctionValidator(check_filename_length)
        assert CheckFilenameLength.__name__ == check_filename__length.__name__

    FunctionValidator can also be used a decorator as well

    .. code-block:: python

        @FunctionValidator
        def check_filename_length(filehandle):
            return len(filehandle.filename) >= 5

    `FunctionValidator` can optionally accept exceptions to catch and convert
    into `UploadErrors` as well. By default, FunctionValidator catches
    TypeError and ValueError, so adding these are redundant.

    .. code-block:: python

        FunctionValidator(check_filename_length, IndexError, TypeError)


    Additionally, individual errors can be added after the fact if needed. This
    can be useful if `FunctionValidator` is used as a decorator, since the
    errors are passed positionally.

        .. code-block:: python

        @FunctionValidator
        def my_validator(filehandle, metadata):
            raise ZeroDivisionError('an example')

        my_validator.add_checked_exception(ZeroDivisionError)

    """
    def __init__(self, func, *errors):
        update_wrapper(self, func)
        self._func = func
        self._errors = (TypeError, ValueError) + errors

    def _validate(self, filehandle, metadata):
        try:
            return self._func(filehandle, metadata)
        except self._errors as e:
            raise UploadError(e)

    def __repr__(self):
        catching = [e.__name__ for e in self._errors]
        return "FunctionValidator({0!r}, catching={1})".format(self._func,
                                                               catching)

    def add_checked_exception(self, exception):
        "Adds an exception type to catch and convert into an UploadError"
        self._errors += (exception,)


class ExtValidator(BaseValidator):
    """Base filename extension class. Extensions are lowercased and placed into
    a frozenset. Also defines a helper staticmethod `_getext` that extracts the
    lowercase extension from a filename.

    Checked extensions should not have the dot included in them.
    """
    def __init__(self, *exts):
        self.exts = frozenset(map(str.lower, exts))

    def __repr__(self):
        exts = ', '.join(self.exts)
        return "{0.__class__.__name__}({1})".format(self, exts)

    @staticmethod
    def _getext(filename):
        "Returns the lowercased file extension."
        return splitext(filename)[-1][1:].lower()


class AllowedExts(ExtValidator):
    """Filename extension validator that whitelights certain extensions

    .. code-block:: python

        ImagesAllowed = AllowedExts('jpg', 'png', 'gif')
        ImagesAllowed(DummyFile(name='awesome.jpg'), {})
        # True
        ImagesAllowed(DummyFile('awesome.psd'), {})
        # UploadError(awesome.psd has an invalid extension...)

    """
    def _validate(self, filehandle, metadata):
        if not self._getext(filehandle.filename) in self.exts:
            exts = ', '.join(self.exts)
            raise UploadError("{0} has an invalid extension. "
                              "Extensions allowed {1}"
                              "".format(filehandle.filename, exts))
        return True


class DeniedExts(ExtValidator):
    """Filename extension validator that blacklists certain extensions

    .. code-block:: python

        DocumentsDenied = DeniedExts('doc', 'xls', 'ppt')
        DocumentsDenied(DummyFile('awesome.pdf'), {})
        # True
        DocumentsDenied(DummyFile('awesome.ppt'), {})
        # UploadError(awesome.ppt has an invalid extension...)

    """
    def _validate(self, filehandle, metadata):
        if self._getext(filehandle.filename) in self.exts:
            exts = ', '.join(self.exts)
            raise UploadError("{0} has an invalid extension. "
                              "Extensions denied {1}"
                              "".format(filehandle.filename, exts))
        return True


# just a little dynamic instance creation, nothing to see here.
AllowAll = type('All', (BaseValidator,), {'_validate': lambda *a, **k: True,
                                          '__repr__': lambda _: 'All',
                                          '__doc__': 'Allows everything.'})()
DenyAll = type('Deny', (BaseValidator,), {'_validate': lambda *a, **k: False,
                                          '__repr__': lambda _: 'Deny',
                                          '__doc__': 'Denies everything.'})()
