
Saving
------

Saving with Flask-Transfer is *super* easy. Once you have FileStorage
object (probably from Flask-WTF), just call
``Transfer.save(filehandle)``. That's mostly it. This'll validate the
file, run the preprocessors, persist the file and then call the
postprocessors.

Destinations
~~~~~~~~~~~~

As mentioned before, destinations can be callables, writables or string
file paths (and the preference is in that order, too). The conversion to
a common interface is done behind the scenes for you. There's also three
ways destinations can be provided, in order of preference:

-  When calling ``Transfer.save``, provide the destination keyword
   argument

.. code:: python

    MyTransfer = Transfer()
    MyTransfer.save(filehandle, metadata, destination='somewhere')

-  Use the ``@Transfer.destination`` callable -- either as a decorator
   or a method call. This callable will accept functions, strings and
   writable objects and handle all the behind the scenes conversion for
   you.

.. code:: python

    MyTransfer = Transfer()

    @MyTransfer.destination
    def storeit(filehandle, metadata):
        # do stuff...
        return filehandle

    #OR

    MyTransfer.destination('~/')

    #OR

    MyTransfer.destination(BytesIO())

-  At instance creation, to provide a "default" destination.

.. code:: python

    MyTransfer = Transfer(destination='~/')

Other stuff
~~~~~~~~~~~

When calling ``Transfer.save`` it's possible to supply metadata to the
validators, preprocessors and postprocessors with the ``metadata``
argument. This can be any object, but defaults to an empty dictionary if
not supplied and probably possible to mutate the object, do what you
will with that information.

Validation can optionally be turned off. Maybe you rely on Flask-WTF to
validate incoming stuff, so doing double validation isn't cool. Just
pass ``validate=False`` to the method.

Finally, if you need to pass positional or keyword arguments down to the
saving mechanism, it's possible to do that as well. ``Transfer.save``
will pass ``*args`` and ``**kwargs`` down to it (and unpack them there
as well).

Validators
----------

Flask-Transfer comes with a handful of predefined validators. Validators
can be loaded into a Transfer object when it's created through the
``validators`` keyword (in this case it should be a list or list-like
object). Or added after the fact with the ``Transfer.validator``
decorator.

.. code:: python

    # load at instance creation
    MyTransfer = Transfer(validators=[ImagesAllowed])

    # load after the fact
    @MyTransfer.validator
    def my_first_validator(filehandle, metadata):
        # do stuff

Extension Validators
~~~~~~~~~~~~~~~~~~~~

There are two extension validators: AllowedExts and DeniedExts. They
both do what you think and creating them is easy peasy:

.. code:: python

    ImagesAllowed = AllowedExts('jpg', 'png', 'gif')
    ImagesDenied = DeniedExts('psd', 'tiff')

Function Validators
~~~~~~~~~~~~~~~~~~~

If you already have a perfectly good function or callable that fits
Flask-Transfer's validator protocol, but you want to take advantage of
the ability to combine validators together with ``&`` and ``|``, you can
use ``FunctionValidator`` to lift your callable into this context:

.. code:: python

    EvenBetterPerfectlyGood = FunctionValidator(perfectly_good_validator)

``FunctionValidator`` can also be used as a decorator:

.. code:: python

    @FunctionValidator
    def perfectly_good(filehandle, metadata):
        return True

Manipulating Validators
~~~~~~~~~~~~~~~~~~~~~~~

Flask-Transfer also allows combining and negating validators easily. If
you have a condition where *two* things need to be true, there's the
``AndValidator`` and its shortcut ``&``:

.. code:: python

    ImagesAndPerfectlyGood = ImagesAllowed & EvenBetterPerfectlyGood

For conditions that are better expressed as an or, there's
``OrValidator`` and its shortcut ``|``:

.. code:: python

    ImagesOrText = ImagesAllowed | AllowExts('txt', 'md', 'rst')

And for conditions that are the opposite of what they currently are,
there's ``NegatedValidator`` and its shortcut ``~`` (yes, that's a tilde
instead of a subtraction sign):

.. code:: python

    NotImages = ~ImagesAllowed

BYOV: Bring Your Own Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Aside from just wrapping a function with FunctionValidator, you can
inherit from ``BaseValidator`` and implement ``_validate``. The only
thing you need to know is that a validator needs to accept a
``werkzeug.FileStorage`` (or whatever you're using internally) instance
and a metadata object (I use dictionaries, but I also make no
presumptions).

Pre and Post processing
-----------------------

Preprocessing happens before saving the filehandle and postprocessing
happens afterwards. Both of these receive the FileStorage instance and a
metadata object (again, dict, object, whatever) and need to return a
FileStorage instance (the same one, a different one, a manipulated one,
doesn't matter). Processors just need to be callable: Functions, classes
with ``__call__``, a method on a class or instance, doesn't matter as
long as it adheres to the calling convention.

Preprocessing
~~~~~~~~~~~~~

These calls are made before calling the save mechanism. Potentially,
they can manipulate the filehandle before it's persisted. Or perhaps use
them to ensure name collision doesn't happen. Or whatever.

Postprocessing
~~~~~~~~~~~~~~

These calls are made after calling the save mechanism. Perhaps after
persisting the filehandle, you need to create thumbnails or shove
something in the database.

Not good enough?
----------------

Subclass ``Transfer`` and do your own thing. Maybe you'd like validators
and processors to map to a dictionary instead of a list.
