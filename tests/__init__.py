import string
import keyword
import os

from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
    Set,
    Tuple,
)

import typing

from convclasses._compat import is_py2, bytes, unicode

from dataclasses import make_dataclass, MISSING, field
from hypothesis import strategies as st, settings, HealthCheck

settings.register_profile(
    "CI", settings(suppress_health_check=[HealthCheck.too_slow]), deadline=None
)

if "CI" in os.environ:
    settings.load_profile("CI")


if is_py2:
    # we exclude float checks from py2, because their stringification is not
    # consistent
    primitive_strategies = st.sampled_from(
        [(st.text(), unicode), (st.binary(), bytes)]
    )
else:
    primitive_strategies = st.sampled_from(
        [
            (st.integers(), int),
            (st.floats(allow_nan=False), float),
            (st.text(), unicode),
            (st.binary(), bytes),
        ]
    )


def _get_field(_type=None, **kwargs):
    f = field(**kwargs)
    f.type = _type
    return f


def fields_sorting(t):
    return (t[0].default is not MISSING) or (
        t[0].default_factory is not MISSING
    )


@st.composite
def enums_of_primitives(draw):
    """Generate enum classes with primitive values."""
    if is_py2:
        names = draw(
            st.sets(
                st.text(alphabet=string.ascii_letters, min_size=1), min_size=1
            )
        )
    else:
        names = draw(st.sets(st.text(min_size=1), min_size=1))
    n = len(names)
    vals = draw(
        st.one_of(
            st.sets(
                st.one_of(
                    st.integers(),
                    st.floats(allow_nan=False),
                    st.text(min_size=1),
                ),
                min_size=n,
                max_size=n,
            )
        )
    )
    return Enum("HypEnum", list(zip(names, vals)))


list_types = st.sampled_from([List, Sequence, MutableSequence])
set_types = st.sampled_from([Set, MutableSet])


@st.composite
def lists_of_primitives(draw):
    """Generate a strategy that yields tuples of list of primitives and types.

    For example, a sample value might be ([1,2], List[int]).
    """
    prim_strat, t = draw(primitive_strategies)
    list_t = draw(list_types.map(lambda list_t: list_t[t]) | list_types)
    return draw(st.lists(prim_strat)), list_t


@st.composite
def mut_sets_of_primitives(draw):
    """A strategy that generates mutable sets of primitives."""
    prim_strat, t = draw(primitive_strategies)
    set_t = draw(set_types.map(lambda set_t: set_t[t]) | set_types)
    return draw(st.sets(prim_strat)), set_t


@st.composite
def frozen_sets_of_primitives(draw):
    """A strategy that generates frozen sets of primitives."""
    prim_strat, t = draw(primitive_strategies)
    set_t = draw(st.just(Set) | st.just(Set[t]))
    return frozenset(draw(st.sets(prim_strat))), set_t


h_tuple_types = st.sampled_from([Tuple, Sequence])
h_tuples_of_primitives = primitive_strategies.flatmap(
    lambda e: st.tuples(
        st.lists(e[0]),
        st.one_of(
            st.sampled_from([Tuple[e[1], ...], Sequence[e[1]]]), h_tuple_types
        ),
    )
).map(lambda e: (tuple(e[0]), e[1]))

dict_types = st.sampled_from([Dict, MutableMapping, Mapping])

seqs_of_primitives = st.one_of(lists_of_primitives(), h_tuples_of_primitives)

sets_of_primitives = st.one_of(
    mut_sets_of_primitives(), frozen_sets_of_primitives()
)


def create_generic_dict_type(type1, type2):
    """Create a strategy for generating parameterized dict types."""
    return st.one_of(
        dict_types,
        dict_types.map(lambda t: t[type1, type2]),
        dict_types.map(lambda t: t[Any, type2]),
        dict_types.map(lambda t: t[type1, Any]),
    )


def create_dict_and_type(tuple_of_strats):
    """Map two primitive strategies into a strategy for dict and type."""
    (prim_strat_1, type_1), (prim_strat_2, type_2) = tuple_of_strats

    return st.tuples(
        st.dictionaries(prim_strat_1, prim_strat_2),
        create_generic_dict_type(type_1, type_2),
    )


dicts_of_primitives = st.tuples(
    primitive_strategies, primitive_strategies
).flatmap(create_dict_and_type)


def gen_attr_names():
    """
    Generate names for attributes, 'a'...'z', then 'aa'...'zz'.
    ~702 different attribute names should be enough in practice.
    Some short strings (such as 'as') are keywords, so we skip them.

    Every second attribute name is private (starts with an underscore).
    """
    lc = string.ascii_lowercase
    has_underscore = False
    for c in lc:
        yield c if not has_underscore else "_" + c
        has_underscore = not has_underscore
    for outer in lc:
        for inner in lc:
            res = outer + inner
            if keyword.iskeyword(res):
                continue
            yield outer + inner


def _create_hyp_class(attrs_and_strategy):
    """
    A helper function for Hypothesis to generate attrs classes.

    The result is a tuple: an attrs class, and a tuple of values to
    instantiate it.
    """

    attrs_and_strat = sorted(attrs_and_strategy, key=fields_sorting)
    attrs = [a[0] for a in attrs_and_strat]
    vals = tuple((a[1]) for a in attrs_and_strat)
    return st.tuples(
        st.just(
            make_dataclass(
                "HypClass",
                zip(gen_attr_names(), [a.type for a in attrs], attrs),
            )
        ),
        st.tuples(*vals),
    )


def just_class(tup):
    nested_cl = tup[1][0]
    combined_attrs = list(tup[0])
    combined_attrs.append(
        (_get_field(default_factory=nested_cl), st.just(nested_cl()))
    )
    return _create_hyp_class(combined_attrs)


def just_class_with_type(tup):
    nested_cl = tup[1][0]
    combined_attrs = list(tup[0])
    combined_attrs.append(
        (
            _get_field(default_factory=nested_cl, _type=nested_cl),
            st.just(nested_cl()),
        )
    )
    return _create_hyp_class(combined_attrs)


def list_of_class(tup):
    nested_cl = tup[1][0]
    combined_attrs = list(tup[0])
    combined_attrs.append(
        (
            _get_field(default_factory=lambda: [nested_cl()]),
            st.just([nested_cl()]),
        )
    )
    return _create_hyp_class(combined_attrs)


def list_of_class_with_type(tup):
    nested_cl = tup[1][0]
    combined_attrs = list(tup[0])
    combined_attrs.append(
        (
            _get_field(
                default_factory=lambda: [nested_cl()],
                _type=typing.List[nested_cl],
            ),
            st.just([nested_cl()]),
        )
    )
    return _create_hyp_class(combined_attrs)


def dict_of_class(tup):
    nested_cl = tup[1][0]
    combined_attrs = list(tup[0])
    combined_attrs.append(
        (
            _get_field(default_factory=lambda: {"cls": nested_cl()}),
            st.just({"cls": nested_cl()}),
        )
    )
    return _create_hyp_class(combined_attrs)


def _create_hyp_nested_strategy(simple_class_strategy):
    """
    Create a recursive attrs class.
    Given a strategy for building (simpler) classes, create and return
    a strategy for building classes that have as an attribute:
        * just the simpler class
        * a list of simpler classes
        * a dict mapping the string "cls" to a simpler class.
    """
    # A strategy producing tuples of the form ([list of attributes], <given
    # class strategy>).
    attrs_and_classes = st.tuples(
        lists_of_attrs(defaults=True), simple_class_strategy
    )

    return (
        attrs_and_classes.flatmap(just_class)
        | attrs_and_classes.flatmap(just_class_with_type)
        | attrs_and_classes.flatmap(list_of_class)
        | attrs_and_classes.flatmap(list_of_class_with_type)
        | attrs_and_classes.flatmap(dict_of_class)
    )


@st.composite
def bare_attrs(draw, defaults=None):
    """
    Generate a tuple of an attribute and a strategy that yields values
    appropriate for that attribute.
    """
    default = MISSING
    if defaults is True or (defaults is None and draw(st.booleans())):
        default = None
    return _get_field(default=default), st.just(None)


@st.composite
def int_attrs(draw, defaults=None):
    """
    Generate a tuple of an attribute and a strategy that yields ints for that
    attribute.
    """
    default = MISSING
    if defaults is True or (defaults is None and draw(st.booleans())):
        default = draw(st.integers())
    return _get_field(default=default), st.integers()


@st.composite
def str_attrs(draw, defaults=None, type_annotations=None):
    """
    Generate a tuple of an attribute and a strategy that yields strs for that
    attribute.
    """
    default = MISSING
    if defaults is True or (defaults is None and draw(st.booleans())):
        default = draw(st.text())
    if (type_annotations is None and draw(st.booleans())) or type_annotations:
        type = unicode
    else:
        type = None
    return _get_field(default=default, _type=type), st.text()


@st.composite
def float_attrs(draw, defaults=None):
    """
    Generate a tuple of an attribute and a strategy that yields floats for that
    attribute.
    """
    default = MISSING
    if defaults is True or (defaults is None and draw(st.booleans())):
        default = draw(st.floats())
    return _get_field(default=default), st.floats()


@st.composite
def dict_attrs(draw, defaults=None):
    """
    Generate a tuple of an attribute and a strategy that yields dictionaries
    for that attribute. The dictionaries map strings to integers.
    """
    default = MISSING
    val_strat = st.dictionaries(keys=st.text(), values=st.integers())
    if defaults is True or (defaults is None and draw(st.booleans())):
        default_val = draw(val_strat)

        def meth():
            return default_val

        default = meth
    return _get_field(default_factory=default), val_strat


def simple_attrs(defaults=None):
    return (
        bare_attrs(defaults)
        | int_attrs(defaults)
        | str_attrs(defaults)
        | float_attrs(defaults)
        | dict_attrs(defaults)
    )


def lists_of_attrs(defaults=None, min_size=0):
    # Python functions support up to 255 arguments.
    return st.lists(
        simple_attrs(defaults), min_size=min_size, max_size=10
    ).map(lambda l: sorted(l, key=fields_sorting))


def simple_classes(defaults=None, min_attrs=0):
    """
    Return a strategy that yields tuples of simple classes and values to
    instantiate them.
    """
    return lists_of_attrs(defaults, min_size=min_attrs).flatmap(
        _create_hyp_class
    )


# Ok, so st.recursive works by taking a base strategy (in this case,
# simple_classes) and a special function. This function receives a strategy,
# and returns another strategy (building on top of the base strategy).
nested_classes = st.recursive(
    simple_classes(defaults=True), _create_hyp_nested_strategy
)
