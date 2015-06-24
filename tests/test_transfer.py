from flask_transfer import transfer, UploadError
from werkzeug import FileStorage
import pytest

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

try:
    from unittest import mock
except ImportError:
    import mock


@pytest.fixture
def transf():
    return transfer.Transfer()


class ReportingTransfer(transfer.Transfer):
    def __init__(self, *args, **kwargs):
        super(ReportingTransfer, self).__init__(*args, **kwargs)
        self._validated = False
        self._preprocessed = False
        self._postprocessed = False
        self._saved = None

    def _validate(self, fh, meta):
        self._validated = True
        return True

    def _preprocess(self, fh, meta):
        self._preprocessed = True
        return fh

    def _postprocess(self, fh, meta):
        self._postprocessed = True
        return fh

    def save(self, *args, **kwargs):
        def destination(filehandle, metadata):
            self._saved = True

        kwargs['destination'] = destination
        super(ReportingTransfer, self).save(*args, **kwargs)


@pytest.mark.parametrize('save_to', [
    lambda a: a, BytesIO(), 'dummy/path'
])
def test_make_destination_callable(save_to):
    assert callable(transfer._make_destination_callable(save_to))


def test_make_destination_callable_raises():
    with pytest.raises(TypeError) as excinfo:
        transfer._make_destination_callable(object())

    assert "Destination must be a string, writable or callable object." == \
        str(excinfo.value)


def test_writeable_saving():
    destination = BytesIO()
    filehandle = FileStorage(stream=BytesIO(b'hello world'))
    dummy_save = transfer._use_filehandle_to_save(destination)

    with mock.patch('werkzeug.FileStorage.save') as mocked_save:
        dummy_save(filehandle, {'buffer_size': 1})

    mocked_save.assert_called_with(destination, 1)


def test_string_path_saving():
    source = BytesIO()
    filehandle = FileStorage(stream=source, filename='test.png')
    dummy_save = transfer._use_filehandle_to_save('test.png')

    with mock.patch('werkzeug.FileStorage.save') as mocked_save:
        dummy_save(filehandle, {'buffer_size': None})

    mocked_save.assert_called_with('test.png', None)


def test_Transfer_setup_blank():
    t = transfer.Transfer()
    assert t._destination is None
    assert t._validators == []
    assert t._preprocessors == []
    assert t._postprocessors == []


@pytest.mark.parametrize('destination', [
    lambda a: a, BytesIO(), 'dummy/path'
])
def test_Transfer_setup_with_destination(destination):
    t = transfer.Transfer(destination=destination)
    assert callable(t._destination)


def test_register_validator(transf):
    @transf.validator
    def _(fh, meta):
        return fh

    assert len(transf._validators) == 1


def test_register_preprocessor(transf):
    @transf.preprocessor
    def _(fh, meta):
        return fh

    assert len(transf._preprocessors) == 1


def test_register_postprocessor(transf):
    @transf.postprocessor
    def _(fh, meta):
        return fh

    assert len(transf._postprocessors) == 1



def test_register_destination(transf):
    @transf.destination
    def save_path(filehandle, metadata):
        pass

    assert transf._destination is save_path


def test_Transfer_save_raises_with_no_destination(transf):
    with pytest.raises(RuntimeError) as excinfo:
        transf.save(FileStorage(), destination=None)

    assert "Destination for filehandle must be provided." == str(excinfo.value)


def test_Transfer_validate(transf):
    @transf.validator
    def suitable_contents(filehandle, meta):
        res = filehandle.read() == b'Hello World'
        filehandle.seek(0)
        return res

    source = FileStorage(stream=BytesIO(b'Hello World'))
    assert transf._validate(source, {})


def test_Transfer_validate_catch_all_errors(transf):
    @transf.validator
    @transf.validator
    def derp(filehandle, meta):
        raise UploadError('error')

    with pytest.raises(UploadError) as excinfo:
        transf._validate('', {}, catch_all_errors=True)

    assert str(excinfo.value) == "('error', 'error')"


def test_Transfer_validate_bail_on_first_error(transf):
    counter = iter(range(2))

    @transf.validator
    @transf.validator
    def derp(filehandle, meta):
        raise UploadError(str(next(counter)))

    with pytest.raises(UploadError) as excinfo:
        transf._validate('', {}, catch_all_errors=False)

    assert str(excinfo.value) == '0'
    assert next(counter) == 1


def test_Transfer_preprocess(transf):
    @transf.preprocessor
    def to_upper(filehandle, meta):
        filehandle.stream = BytesIO(filehandle.stream.read().lower())
        return filehandle

    source = FileStorage(stream=BytesIO(b'Hello World'))
    transf._preprocess(source, {})
    source.seek(0)
    assert source.read() == b'hello world'


def test_Transfer_postprocess(transf):
    @transf.postprocessor
    def to_uppercase(filehandle, meta):
        filehandle.stream = BytesIO(filehandle.stream.read().upper())
        return filehandle

    source = FileStorage(stream=BytesIO(b'Hello World'))
    transf._postprocess(source, {})
    source.seek(0)

    assert source.read() == b'HELLO WORLD'


def test_Transfer_save():
    t = ReportingTransfer()
    t.save('')

    assert t._validated
    assert t._preprocessed
    assert t._saved
    assert t._postprocessed


def test_Transfer_save_toggle_validate():
    t = ReportingTransfer()
    t.save('', validate=False)

    assert not t._validated
