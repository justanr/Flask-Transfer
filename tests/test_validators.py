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


def test_raise_with_unimplemented_validate():
    class MyValidator(validators.BaseValidator):
        pass

    with pytest.raises(NotImplementedError) as excinfo:
        MyValidator()('', {})

    assert '_validate not implemented' == str(excinfo.value)


def test_AndValidator_shortcut():
    first = validators.BaseValidator()
    second = validators.BaseValidator()
    and_validator = first & second

    assert isinstance(and_validator, validators.AndValidator)
    assert and_validator._first is first and and_validator._second is second


def test_OrValidator_shortcut():
    first = validators.BaseValidator()
    second = validators.BaseValidator()
    or_validator = first | second

    assert isinstance(or_validator, validators.OrValidator)
    assert or_validator._first is first and or_validator._second is second


def test_NegatedValidator_shortcut():
    validator = validators.BaseValidator()
    negated_validator = ~validator

    assert isinstance(negated_validator, validators.NegatedValidator)
    assert negated_validator._validator is validator


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

    # fill in __qualname__ and __annotations__ in Python 2.6/2.7
    missing = object()
    assert all([getattr(wrapped, c, missing) ==
                getattr(filename_all_lower, c, missing)
                for c in checked])


def test_FunctionValidator_okays():
    wrapped = validators.FunctionValidator(filename_all_lower)
    assert wrapped._validate(DummyFile('awesome.jpg'), {})


def test_FunctionValidator_as_decorator():
    @validators.FunctionValidator
    def my_func(filehandle, metadata):
        pass

    assert isinstance(my_func, validators.FunctionValidator)


def test_FunctionValidator_accepts_errors_to_catch():
    some_validator = validators.FunctionValidator(lambda x: x, ZeroDivisionError)

    assert some_validator._errors == (TypeError, ValueError, ZeroDivisionError)


def test_FunctionValidator_add_error_after_creation():
    some_validator = validators.FunctionValidator(lambda x: x)
    some_validator.add_checked_exceptions(ZeroDivisionError)

    assert ZeroDivisionError in some_validator._errors


def test_FunctionValidator_add_several_errors_after_creation():
    some_validator = validators.FunctionValidator(lambda x: x)
    some_validator.add_checked_exceptions(ZeroDivisionError, RuntimeError)

    assert len(some_validator._errors) == 4


def test_FunctionValidator_converts_to_UploadError():
    class MyException(Exception):
        pass

    @validators.FunctionValidator
    def throw_an_error(filehandle, metadata):
        raise MyException('what a test!')

    throw_an_error.add_checked_exceptions(MyException)

    with pytest.raises(UploadError) as excinfo:
        throw_an_error('', {})

    assert excinfo.errisinstance(UploadError)
    assert 'what a test!' == excinfo.value.args[0]


@pytest.mark.parametrize('first, second, result', [
    (True, True, True), (False, True, True),
    (False, False, False), (True, False, True)
])
def test_OrValidator(first, second, result):
    orer = validators.OrValidator(lambda f, m: first, lambda f, m: second)
    assert orer('', {}) == result


@pytest.mark.parametrize('first, second, result', [
    (True, True, True), (False, False, False),
    (True, False, False), (False, True, False)
])
def test_AndValidator(first, second, result):
    ander = validators.AndValidator(lambda f, m: first, lambda f, m: second)
    assert ander('', {}) == result


def test_NegatedValidator():
    negated = validators.NegatedValidator(lambda f, m: True)
    assert not negated('', {})
    assert validators.NegatedValidator(negated)('', {})
