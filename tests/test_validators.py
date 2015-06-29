from flask_transfer import validators, UploadError
import pytest

try:
    from unittest import mock
except ImportError:
    import mock


class DummyFile(object):
    def __init__(self, filename):
        self.filename = filename

    def __repr__(self):
        return 'DummyFile(filename={0})'.format(self.filename)


def filename_all_lower(filehandle, metadata):
    "Validates that the filename is all lowercase."
    if not filehandle.filename.islower():
        raise UploadError('require lowercase filename')
    return True


def test_raise_with_unimplemented_validate():
    with pytest.raises(NotImplementedError) as excinfo:
        validators.BaseValidator()('', {})

    assert '_validate not implemented' == str(excinfo.value)


def test_make_AndValidator():
    v1, v2 = validators.AllowedExts('jpg'), validators.DeniedExts('png')
    and_validator = v1 & v2

    assert isinstance(and_validator, validators.AndValidator)
    assert and_validator._validators == (v1, v2)


def test_AndValidator_success():
    DummyValidator = mock.MagicMock(return_value=True)
    dummy_file = DummyFile('awesome.jpg')
    and_validator = validators.AndValidator(DummyValidator,
                                            DummyValidator)
    assert and_validator(dummy_file, {})
    assert DummyValidator.call_count == 2
    assert DummyValidator.call_args == mock.call(dummy_file, {})


def test_AndValidator_failure_with_callable():
    dummy_file = DummyFile(filename='doesntmatter.exe')
    truthy = mock.MagicMock(return_value=True)
    falsey = mock.MagicMock(return_value=False)
    and_validator = validators.AndValidator(falsey, truthy)

    with pytest.raises(UploadError) as excinfo:
        and_validator(dummy_file, {})

    assert 'returned false in' in str(excinfo.value)
    assert falsey.call_count == 1
    assert falsey.call_args == mock.call(dummy_file, {})
    assert truthy.call_count == 0


def test_AndValidator_failure_with_exception():
    toss_error = mock.MagicMock(side_effect=UploadError('something bad happened'))

    dummy_file = DummyFile(filename='kindamatters.exe')
    and_validator = validators.AndValidator(toss_error, toss_error)

    with pytest.raises(UploadError) as excinfo:
        and_validator(dummy_file, {})

    assert 'something bad happened' == str(excinfo.value)


def test_make_OrValidator():
    v1, v2 = validators.AllowedExts('png'), validators.AllowedExts('jpg')
    or_validator = v1 | v2

    assert isinstance(or_validator, validators.OrValidator)
    assert or_validator._validators == (v1, v2)


def test_OrValidator_success():
    def only_jpgs(fh, m):
        return fh.filename.endswith('jpg')

    def only_pngs(fh, m):
        return fh.filename.endswith('png')

    or_validator = validators.OrValidator(only_jpgs, only_pngs)

    assert or_validator(DummyFile(filename='awesome.png'), {})
    assert or_validator(DummyFile(filename='awesome.jpg'), {})


def test_OrValidator_failure_with_callable():
    falsey = mock.MagicMock(return_value=False)
    or_validator = validators.OrValidator(falsey, falsey)

    with pytest.raises(UploadError) as excinfo:
        or_validator(DummyFile(filename='wolololo.wav'), {})

    assert falsey.call_count == 2
    assert len(excinfo.value.args[0]) == 2
    assert 'returned false in' in excinfo.value.args[0][0]


def test_OrValidator_failure_with_exception():
    toss_error = mock.MagicMock(side_effect=UploadError('something bad happened'))

    or_validator = validators.OrValidator(toss_error, toss_error, toss_error)
    with pytest.raises(UploadError) as excinfo:
        or_validator(DummyFile(filename='wolololo.wav'), {})

    assert toss_error.call_count == 3
    assert len(excinfo.value.args[0]) == 3
    assert all('something bad happened' == e for e in excinfo.value.args[0])


def test_make_NegatedValidator():
    class MyValidator(validators.BaseValidator):
        def _validate(fh, m):
            return False

    mv = MyValidator()
    negated_mv = ~mv

    assert isinstance(negated_mv, validators.NegatedValidator)
    assert negated_mv._nested is mv


def test_NegatedValidator_turns_false_to_true():
    my_negated = validators.NegatedValidator(lambda fh, m: False)
    assert my_negated(DummyFile(filename='cat.lol'), {})


def test_NegatedValidator_turns_UploadError_to_true():
    def toss_error(fh, m):
        raise UploadError('never actually seen')

    my_negated = validators.NegatedValidator(toss_error)
    assert my_negated(DummyFile(filename='awesome.sh'), {})


def test_NegatedValidator_raises_on_failure():
    def truthy(fh, m):
        return True

    my_negated = validators.NegatedValidator(truthy)

    with pytest.raises(UploadError) as excinfo:
        my_negated(DummyFile(filename='perfectlyokay.php'), {})

    assert 'returned false' in str(excinfo.value)


def test_FunctionValidator_wraps():
    my_func_validator = validators.FunctionValidator(filename_all_lower)
    # don't bother with qualname/annotations because 2.6/2.7 compat
    assert my_func_validator.__name__ == filename_all_lower.__name__
    assert my_func_validator.__doc__ == filename_all_lower.__doc__
    assert my_func_validator.__module__ == filename_all_lower.__module__


def test_FunctionValidator_as_decorator():
    @validators.FunctionValidator
    def do_nothing(fh, m):
        return True

    assert isinstance(do_nothing, validators.FunctionValidator)
    assert do_nothing.__name__ == 'do_nothing'


def test_FuncionValidator_validates():
    fake = mock.Mock(return_value=True)
    fake.__name__ = fake.__doc__ = fake.__module__ = ''
    fake_file = DummyFile(filename='inconceivable.py')

    my_func_validator = validators.FunctionValidator(fake)
    my_func_validator(fake_file, {})

    assert fake.call_args == mock.call(fake_file, {})


def test_AllowedExts_raises():
    allowed = validators.AllowedExts('jpg')
    with pytest.raises(UploadError) as excinfo:
        allowed._validate(DummyFile('sad.png'), {})

    assert "has an invalid extension" in str(excinfo.value)


def test_AllowedExts_okays():
    allowed = validators.AllowedExts('jpg')
    assert allowed._validate(DummyFile('awesome.jpg'), {})


def test_invert_AllowedExts():
    exts = frozenset(['jpg', 'png', 'gif'])
    flipped = ~validators.AllowedExts(*exts)
    assert isinstance(flipped, validators.DeniedExts) and flipped.exts == exts


def test_DeniedExts_raises():
    denied = validators.DeniedExts('png')
    with pytest.raises(UploadError) as excinfo:
        denied._validate(DummyFile('sad.png'), {})

    assert "has an invalid extension" in str(excinfo.value)


def test_DeniedExts_okays():
    denied = validators.DeniedExts('png')
    assert denied._validate(DummyFile('awesome.jpg'), {})


def test_invert_DeniedExts():
    exts = frozenset(['jpg', 'gif', 'png'])
    flipped = ~validators.DeniedExts(*exts)
    assert isinstance(flipped, validators.AllowedExts) and flipped.exts == exts
