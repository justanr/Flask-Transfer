"""
    flask_transfer.validators
    ~~~~~~~~~~~~~~~~~~~~~~~~~
    Built in validators for flask_transfer.
"""

from functools import update_wrapper
from os.path import splitext
from .exc import UploadError


class BaseValidator(object):
    """BaseValidator class for flask_transfer. Provides utility methods for
    combining validators together. Subclasses should implement `_validates`
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
    & operator.::
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
    | operator.::
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
    ~ unary operator.::
        Images = AllowedExts("jpg", "png", "gif")
        NoImages = ~Images # same as creating DeniedExts("jpg", "png", "gif")

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
    """flask_transfer validator used to lift a function into the validator
    environment, allowing it to access the &, | and ~ shortcuts for combination
    and negation. FunctionValidator presents as the wrapped function.::

        def check_filename_length(filehandle):
            return len(filehandle.name) >= 5

        CheckFilenameLength = FunctionValidator(check_filename_length)

    FunctionValidator can also be used a decorator as well::
        @FunctionValidator
        def check_filename_length(filehandle):
            return len(filehandle.name) >= 5
    """
    def __init__(self, func):
        update_wrapper(self, func)
        self._func = func

    def _validate(self, filehandle, metadata):
        return self._func(filehandle, metadata)

    def __repr__(self):
        return "FunctionValidator({!r})".format(self._func)


class ExtValidator(BaseValidator):
    """Base filename extension class. Extensions are lowercased and placed into
    a frozenset. Also defines a helper staticmethod `_getext` that extracts the
    lowercase extension from a filename.
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
    """Filename extension validator that whitelights certain extensions::
        >>> Images = AllowedExts("jpg", "png", "gif")
        >>> Images._validate(DummyFile("awesome.png"))
        >>> True
        >>> Images._validate(DummyFile("sadface.psd"))
        >>> False
    """
    def _validate(self, filehandle, metadata):
        if not self._getext(filehandle.filename) in self.exts:
            exts = ', '.join(self.exts)
            raise UploadError("{} has an invalid extension. "
                              "Extensions allowed {}"
                              "".format(filehandle.filename, exts))
        return True


class DeniedExts(ExtValidator):
    """Filename extension validator that blacklists certain extensions::
        >>> DeniedDocuments = DeniedExts("doc", "xls")
        >>> DeniedDocumentss._validate(DummyFile("nope.doc"))
        >>> False
        >>> DeniedDocuments._validate(DummyFile("okay.odt"))
        >>> True
    """
    def _validate(self, filehandle, metadata):
        if self._getext(filehandle.filename) in self.exts:
            exts = ', '.join(self.exts)
            raise UploadError("{} has an invalid extension. "
                              "Extensions denied {}"
                              "".format(filehandle.filename, exts))
        return True


# just a little dynamic instance creation, nothing to see here.
AllowAll = type('All', (BaseValidator,), {'_validate': lambda *a, **k: True,
                                          '__repr__': lambda _: 'All'})()
DenyAll = type('Deny', (BaseValidator,), {'_validate': lambda *a, **k: False,
                                          '__repr__': lambda _: 'Deny'})()
AllowAll.__doc__ = 'Okays everything passed to it.'
DenyAll.__doc__ = 'Denies everything passed to it.'
