"""
    flask_transfer.wtf
    ~~~~~~~~~~~~~~~~~~
    Compatibility layer for using Flask-Transfer validators as Flask-WTF
    validators. Import validators from here instead of the main package for
    this use case.

    The new BaseValidator here extracts the filehandle from the field and yanks
    the metadata needed for the validators off of the form's meta attribute
    or creates an empty dictionary if not provided.
"""


try:
    from flask_wtf.file import FileField
    from wtforms import ValidationError
except ImportError:
    # duh but let's spell it out just in case.
    msg = "flask_wtf is required for flask_transfer compatibility layer"
    raise ImportError(msg)

from inspect import isclass
from . import validators, UploadError


class BaseValidator(validators.BaseValidator):
    """flask_wtf compatible BaseValidator. This class should be used as the base
    for any validators living on a flask-wtf FileField. When invoked, it will
    pull the filehandle off of the field attribute and attempt to get the
    metadata from form.meta.transfer_meta and create an empty dictionary if that
    fails
    """
    def __call__(self, form, field):
        if not isinstance(field, FileField):
            msg = 'Flask-Transfer validators may only live on a FileField'
            raise TypeError(msg)

        if not field.has_file():
            return False

        meta = getattr(form.meta, 'transfer_meta', {})
        try:
            return super().__call__(field.data, meta)
        except UploadError as e:
            raise ValidationError(*e.args)

    # override and, or and invert to avoid falling back to the original
    # validator manipulators which aren't wtforms validator compatible

    def __and__(self, other):
        return AndValidator(self, other)

    def __or__(self, other):
        return OrValidator(self, other)

    def __invert__(self):
        return NegatedValidator(self)


# since the BaseValidator here will automatically pull the filehandle
# and metadata off of the submitted form, And, Or and Negated need to
# simply pass that information along, otherwise errors happen
# These names need to be rebound in the module *anyways* so the new
# BaseValidator can use them instead of falling back to the original
# And/Or/Negated.

class AndValidator(validators.AndValidator, BaseValidator):
    def __call__(self, form, field):
        return self._first(form, field) and self._second(form, field)


class OrValidator(validators.OrValidator, BaseValidator):
    def __call__(self, form, field):
        return self._first(form, field) and self._second(form, field)


class NegatedValidator(validators.NegatedValidator, BaseValidator):
    def __call__(self, form, field):
        return not self._validator(form, field)


# everything about this bad and I feel bad.
# (\/) (;,,;) (\/)
__all__ = ['BaseValidator', 'AndValidator', 'OrValidator', 'NegatedValidator']
for name, validator in validators.__dict__.items():
    if isclass(validator) and issubclass(validator, validators.BaseValidator):
        # since some validators are redefined here already, they're already
        # present in __all__ and should be skipped
        if name in __all__:
            continue

        # dependency inject new base validator into MRO of victim and then put
        # the new validator into the global namespace and __all__ for * exports
        # for a less janky example of using inheritance for dependency injection
        # see Raymond Hettinger' Super Considered Super talk at PyCon 2015
        globals()[name] = type(name, (validator, BaseValidator), {})
        __all__.append(name)
