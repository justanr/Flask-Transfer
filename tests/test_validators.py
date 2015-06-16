from flask_transfer import validators, UploadError
import pytest


class DummyFile(object):
    def __init__(self, filename):
        self.filename = filename


def filename_all_lower(filehandle, metadata):
    "Validates that the filename is all lowercase."
    if not filehandle.filename.islower():
        raise UploadError('require lowercase filename')
    return True


def test_AllowedExts_raises():
    allowed = validators.AllowedExts('jpg')
    with pytest.raises(UploadError) as excinfo:
        allowed._validate(DummyFile('sad.png'), {})

    assert "has an invalid extension" in str(excinfo.value)


def test_AllowedExts_okays():
    allowed = validators.AllowedExts('jpg')
    assert allowed._validate(DummyFile('awesome.jpg'), {})


def test_DeniedExts_raises():
    denied = validators.DeniedExts('png')
    with pytest.raises(UploadError) as excinfo:
        denied._validate(DummyFile('sad.png'), {})

    assert "has an invalid extension" in str(excinfo.value)


def test_DeniedExts_okays():
    denied = validators.DeniedExts('png')
    assert denied._validate(DummyFile('awesome.jpg'), {})


def test_FunctionValidator_wraps():
    checked = ('__name__', '__doc__', '__module__',
               '__qualname__', '__annotations__')
    wrapped = validators.FunctionValidator(filename_all_lower)
    # __qualname__ and __annotations__ in Python 2.6/2.7
    missing = object()
    assert all([getattr(wrapped, c, missing) ==
                getattr(filename_all_lower, c, missing)
                for c in checked])


def test_FunctionValidator_okays():
    wrapped = validators.FunctionValidator(filename_all_lower)
    assert wrapped._validate(DummyFile('awesome.jpg'), {})
