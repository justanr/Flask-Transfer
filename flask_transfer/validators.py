"""
"""
from functools import update_wrapper
from .exc import UploadError
import os


class BaseValidator(object):
    """BaseValidator class for flask_transfer. Provides utility methods for
    combining validators together. Subclasses should implement `_validates`.

    Validators can signal failure in one of two ways:
        * Raise UploadError with a message
        * Return non-Truthy value.

    Raising UploadError is the preferred method, as it allows a more descriptive
    message to reach the caller, however by supporting returning Falsey values,
    lambdas can be used as validators as well.
    """
    def _validate(self, filehandle, metadata):
        raise NotImplementedError("_validate not implemented")

    def __call__(self, filehandle, metadata):
        return self._validate(filehandle, metadata)

    def __repr__(self):
        return self.__class__.__name__

    def __and__(self, other):
        return AndValidator(self, other)

    def __or__(self, other):
        return OrValidator(self, other)

    def __invert__(self):
        return NegatedValidator(self)


class AndValidator(BaseValidator):
    """Combination validator analogous to the builtin `all` function. Every
    nested validator must return Truthy or the entire validator is considered
    False.

    On its own, AndValidator is redundant with how validators are run, however,
    it's useful when combined with `OrValidator` or `NegatedValidator`.

    .. code-block:: python

        ImagesButNotPSD = AndValidator(AllowedExts('gif', 'png', 'jpg'), # etc
                                       DeniedExts('psd'))
        ImagesButNotPSD(DummyFile(filename='awesome.png')) # True
        ImagesButNotPSD(DummyFile(filename='awesome.psd')) # UploadError(...)

    It's also possible to shortcut to creating an AndValidator by using the
    logical/bitwise and (`&`) operator.

    .. code-block:: python

        ImagesButNotPSD = AllowedExts('png', 'gif', 'jpg') & DeniedExts('psd')

    This shortcut is available to any validator inheriting from BaseValidator.
    However, when combining many nested validators together, it's better to
    use the explicit constructor.

    .. code-block:: python

        # Ends up nesting an AndValidator inside another
        AllowedExts('png') & DeniedExts('psd') & MyValidator()

        # Creates a flat AndValidator
        AndValidator(AllowedExts('png'), DeniedExts('psd'), MyValidator())
    """
    def __init__(self, *validators):
        self._validators = validators

    def _validate(self, filehandle, metadata):
        msg = '{0!r}({1!r}, {2!r}) returned false in {3!r}'
        for validator in self._validators:
            if not validator(filehandle, metadata):
                raise UploadError(msg.format(validator, filehandle,
                                             metadata, self))
        return True

    def __repr__(self):
        validators = ', '.join([repr(v) for v in self._validators])
        return 'AndValidator({0})'.format(validators)


class OrValidator(BaseValidator):
    """Combination validator analogous to the builtin `any` function. As long as
    a single nested validator returns True, so does this validator.

    .. code-block:: python

        ImagesOrText = OrValidator(AllowedExts('jpg', 'png' 'gif'), # etc
                                   AllowedExts('txt'))
        ImagesOrText(DummyFile(filename='awesome.txt')) # True
        ImagesOrText(DummyFile(filename='awesome.png')) # True
        ImagesOrText(DummyFile(filename='notawesome.doc')) # UploadError(...)

    It's also possible to shortcut to creating an OrValidator by using the
    logical/bitwise or (`|`) operator.

    .. code-block:: python

        ImagesOrText = AllowedExts('png', 'jpg', 'gif') | AllowedExts('txt')

    This shortcut exists on every validator inheriting from BaseValidator.
    However, when chaining many validator together, it's better to use the
    explicit constructor rather than the shortcut.

    .. code-block:: python

        # nests an OrValidator inside of another
        AllowedExts('png') | AllowedExts('txt') | MyValidator()

        # creates a flat validator
        OrValidator(AllowedExts('png'), AllowedExts('txt'), MyValidator())
    """
    def __init__(self, *validators):
        self._validators = validators

    def _validate(self, filehandle, metadata):
        errors = []
        msg = '{0!r}({1!r}, {2!r}) returned false in {3!r}.'
        for validator in self._validators:
            try:
                if not validator(filehandle, metadata):
                    raise UploadError(msg.format(validator, filehandle,
                                                 metadata, self))
            except UploadError as e:
                errors.append(e.args[0])
            else:
                return True
        raise UploadError(errors)

    def __repr__(self):
        validators = ', '.join([repr(v) for v in self._validators])
        return 'OrValidator({0})'.format(validators)


class NegatedValidator(BaseValidator):
    """Flips a validation failure into a success and validator success into
    failure. This is analogous to the `not` keyword (or `operator.not_`
    function). If the nested validator returns False or raises UploadError,
    NegatedValidator instead returns True. However, if the nested returns True,
    it raises an UploadError instead.

    .. code-block:: python

        NotImages = NegatedValidator(AllowedExts('png', 'jpg', 'gif'))
        NotImages(DummyFile(filename='awesome.txt')) # True
        NotImages(DummyFile(filename='awesome.png')) # UploadError(...)

    There is also an operator shortcut: the logical/bitwise inversion (`~`)
    operator. The reason `~` was chosen over `-` is that inversion is *always*
    unary, where as `-` may be unary or binary depending on surrounding context,
    using logical inversion also keeps it in theme with AndValidator and
    OrValidator.

    .. code-block:: python

        ~OrValidator(AllowedExts('png'), AllowedExts('txt'))
        # NegatedValidator(OrValidator(AllowedExts('png'), AllowedExts('txt')))

    This shortcut exists on every validator inheriting from BaseValidator.
    However, there is special behavior for `AllowedExts` and `DeniedExts` which
    simply flip between one another when used with the invert operator.

    .. code-block:: python

        ~AllowedExts('png') # becomes DeniedExts('png')
        ~DeniedExts('txt') # becomes AllowedExts('txt')
    """
    def __init__(self, nested):
        self._nested = nested

    def _validate(self, filehandle, metadata):
        try:
            if not self._nested(filehandle, metadata):
                return True
        except UploadError:
            # UploadError would only be raised to signal a failed condition
            # but we want to flip a False into a True anyways.
            return True
        # looks strange that we're tossing an error out if we reach here
        # but we'll need to signal a failure to the caller with some information
        msg = '{0!r}({1!r}, {2!r}) returned false'
        raise UploadError(msg.format(self, filehandle, metadata))

    def __repr__(self):
        return 'NegatedValidator({0!r})'.format(self._nested)


class FunctionValidator(BaseValidator):
    def __init__(self, wrapped):
        update_wrapper(self, wrapped)
        self._nested = wrapped

    def _validate(self, filehandle, metadata):
        return self._nested(filehandle, metadata)

    def __repr__(self):
        return 'FunctionValidator({0!r})'.format(self._nested)


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
        return os.path.splitext(filename)[-1][1:].lower()


class AllowedExts(ExtValidator):
    """Filename extension validator that whitelists certain extensions

    .. code-block:: python

        ImagesAllowed = AllowedExts('jpg', 'png', 'gif')
        ImagesAllowed(DummyFile(name='awesome.jpg'), {})
        # True
        ImagesAllowed(DummyFile('awesome.psd'), {})
        # UploadError(awesome.psd has an invalid extension...)

    """
    def _validate(self, filehandle, metadata):
        if self._getext(filehandle.filename) not in self.exts:
            exts = ', '.join(self.exts)
            msg = '{0} has an invalid extension, allowed extensions: {1}'
            raise UploadError(msg.format(filehandle.filename, exts))

        return True

    def __invert__(self):
        return DeniedExts(*self.exts)


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
            msg = '{0} has an invalid extension, denied extensions {1}'
            raise UploadError(msg.format(filehandle.filename, exts))

        return True

    def __invert__(self):
        return AllowedExts(*self.exts)


# just a little dynamic instance creation, nothing to see here.
AllowAll = type('All', (BaseValidator,), {'_validate': lambda *a, **k: True,
                                          '__repr__': lambda _: 'All',
                                          '__doc__': 'Allows everything.'})()
DenyAll = type('Deny', (BaseValidator,), {'_validate': lambda *a, **k: False,
                                          '__repr__': lambda _: 'Deny',
                                          '__doc__': 'Denies everything.'})()
