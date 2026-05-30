"""Registries that make validators (and custom logic) serializable by name.

Two registries live here:

1. The **validator-type** registry maps a ``type_name`` to its
   :class:`~puzzcombinator.validation.base.Validator` subclass, so the codec can
   rebuild any validator from ``{"type": ..., "params": ...}``.
2. The **custom-function** registry maps a name to a ``Callable[[str], bool]``.
   Arbitrary Python functions can't be serialized, so a
   :class:`~puzzcombinator.validation.builtins.CustomFn` validator stores only
   the *name*; the host application registers the implementation at import time.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from puzzcombinator.errors import RegistryError

if TYPE_CHECKING:
    from puzzcombinator.validation.base import Validator

_VALIDATOR_TYPES: dict[str, type[Validator]] = {}
_CUSTOM_FNS: dict[str, Callable[[str], bool]] = {}


def register_validator[V: type[Validator]](cls: V) -> V:
    """Class decorator: register a validator subclass under its ``type_name``."""
    _VALIDATOR_TYPES[cls.type_name] = cls
    return cls


def build_validator(type_name: str, params: dict[str, Any]) -> Validator:
    """Reconstruct a validator from its serialized ``type_name`` and ``params``."""
    try:
        cls = _VALIDATOR_TYPES[type_name]
    except KeyError:
        raise RegistryError(
            f"unknown validator type {type_name!r}; known: {sorted(_VALIDATOR_TYPES)}"
        ) from None
    return cls.from_params(params)


def register_custom_fn(name: str) -> Callable[[Callable[[str], bool]], Callable[[str], bool]]:
    """Decorator: register a named predicate for use by ``CustomFn`` validators."""

    def decorator(fn: Callable[[str], bool]) -> Callable[[str], bool]:
        _CUSTOM_FNS[name] = fn
        return fn

    return decorator


def get_custom_fn(name: str) -> Callable[[str], bool]:
    """Look up a registered custom predicate, or raise :class:`RegistryError`."""
    try:
        return _CUSTOM_FNS[name]
    except KeyError:
        raise RegistryError(
            f"unknown custom validator fn {name!r}; known: {sorted(_CUSTOM_FNS)}"
        ) from None
