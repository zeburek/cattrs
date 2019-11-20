===========
convclasses
===========

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black


----

``cattrs`` is an open source Python library for structuring and unstructuring
data. ``cattrs`` works best with ``attrs`` classes and the usual Python
collections, but other kinds of classes are supported by manually registering
converters.

Python has a rich set of powerful, easy to use, built-in data types like
dictionaries, lists and tuples. These data types are also the lingua franca
of most data serialization libraries, for formats like json, msgpack, yaml or
toml.

Data types like this, and mappings like ``dict`` s in particular, represent
unstructured data. Your data is, in all likelihood, structured: not all
combinations of field names are values are valid inputs to your programs. In
Python, structured data is better represented with classes and enumerations.
``attrs`` is an excellent library for declaratively describing the structure of
your data, and validating it.

When you're handed unstructured data (by your network, file system, database...),
``cattrs`` helps to convert this data into structured data. When you have to
convert your structured data into data types other libraries can handle,
``cattrs`` turns your classes and enumerations into dictionaries, integers and
strings.

Here's a simple taste. The list containing a float, an int and a string
gets converted into a tuple of three ints.

.. code-block:: python

    >>> import cattr
    >>> from typing import Tuple
    >>>
    >>> cattr.structure([1.0, 2, "3"], Tuple[int, int, int])
    (1, 2, 3)

``cattrs`` works well with ``attrs`` classes out of the box.

.. code-block:: python

    >>> import attr, cattr
    >>>
    >>> @attr.s(slots=True, frozen=True)  # It works with normal classes too.
    ... class C:
    ...     a = attr.ib()
    ...     b = attr.ib()
    ...
    >>> instance = C(1, 'a')
    >>> cattr.unstructure(instance)
    {'a': 1, 'b': 'a'}
    >>> cattr.structure({'a': 1, 'b': 'a'}, C)
    C(a=1, b='a')

Here's a much more complex example, involving ``attrs`` classes with type
metadata.

.. code-block:: python

    >>> from enum import unique, Enum
    >>> from typing import List, Optional, Sequence, Union
    >>> from cattr import structure, unstructure
    >>> import attr
    >>>
    >>> @unique
    ... class CatBreed(Enum):
    ...     SIAMESE = "siamese"
    ...     MAINE_COON = "maine_coon"
    ...     SACRED_BIRMAN = "birman"
    ...
    >>> @attr.s
    ... class Cat:
    ...     breed: CatBreed = attr.ib()
    ...     names: Sequence[str] = attr.ib()
    ...
    >>> @attr.s
    ... class DogMicrochip:
    ...     chip_id = attr.ib()
    ...     time_chipped: float = attr.ib()
    ...
    >>> @attr.s
    ... class Dog:
    ...     cuteness: int = attr.ib()
    ...     chip: Optional[DogMicrochip] = attr.ib()
    ...
    >>> p = unstructure([Dog(cuteness=1, chip=DogMicrochip(chip_id=1, time_chipped=10.0)),
    ...                  Cat(breed=CatBreed.MAINE_COON, names=('Fluffly', 'Fluffer'))])
    ...
    >>> print(p)
    [{'cuteness': 1, 'chip': {'chip_id': 1, 'time_chipped': 10.0}}, {'breed': 'maine_coon', 'names': ('Fluffly', 'Fluffer')}]
    >>> print(structure(p, List[Union[Dog, Cat]]))
    [Dog(cuteness=1, chip=DogMicrochip(chip_id=1, time_chipped=10.0)), Cat(breed=<CatBreed.MAINE_COON: 'maine_coon'>, names=['Fluffly', 'Fluffer'])]

Consider unstructured data a low-level representation that needs to be converted
to structured data to be handled, and use ``structure``. When you're done,
``unstructure`` the data to its unstructured form and pass it along to another
library or module. Use `attrs type metadata <http://attrs.readthedocs.io/en/stable/examples.html#types>`_
to add type metadata to attributes, so ``cattrs`` will know how to structure and
destructure them.

* Free software: MIT license
* Documentation: https://cattrs.readthedocs.io.
* Python versions supported: 2.7, 3.5 and up.


Features
--------

* Converts structured data into unstructured data, recursively:

  * ``attrs`` classes are converted into dictionaries in a way similar to ``attr.asdict``, or into tuples in a way similar to ``attr.astuple``.
  * Enumeration instances are converted to their values.
  * Other types are let through without conversion. This includes types such as
    integers, dictionaries, lists and instances of non-``attrs`` classes.
  * Custom converters for any type can be registered using ``register_unstructure_hook``.

* Converts unstructured data into structured data, recursively, according to
  your specification given as a type. The following types are supported:

  * ``typing.Optional[T]``.
  * ``typing.List[T]``, ``typing.MutableSequence[T]``, ``typing.Sequence[T]`` (converts to a list).
  * ``typing.Tuple`` (both variants, ``Tuple[T, ...]`` and ``Tuple[X, Y, Z]``).
  * ``typing.MutableSet[T]``, ``typing.Set[T]`` (converts to a set).
  * ``typing.FrozenSet[T]`` (converts to a frozenset).
  * ``typing.Dict[K, V]``, ``typing.MutableMapping[K, V]``, ``typing.Mapping[K, V]`` (converts to a dict).
  * ``attrs`` classes with simple attributes and the usual ``__init__``.

    * Simple attributes are attributes that can be assigned unstructured data,
      like numbers, strings, and collections of unstructured data.

  * All `attrs` classes with the usual ``__init__``, if their complex attributes
    have type metadata.
  * ``typing.Union`` s of supported ``attrs`` classes, given that all of the classes
    have a unique field.
  * ``typing.Union`` s of anything, given that you provide a disambiguation
    function for it.
  * Custom converters for any type can be registered using ``register_structure_hook``.

Credits
-------

Major credits to Hynek Schlawack for creating attrs_ and its predecessor,
characteristic_.

``cattrs`` is tested with Hypothesis_, by David R. MacIver.

``cattrs`` is benchmarked using perf_, by Victor Stinner.

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _attrs: https://github.com/hynek/attrs
.. _characteristic: https://github.com/hynek/characteristic
.. _Hypothesis: http://hypothesis.readthedocs.io/en/latest/
.. _perf: https://github.com/haypo/perf
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage

