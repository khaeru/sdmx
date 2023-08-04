"""Parse structure information from item description."""
import logging
import operator
import re
from typing import Callable, Dict, List, Optional, Tuple, Union

from sdmx.model.common import DEFAULT_LOCALE, Item, ItemScheme

log = logging.getLogger(__name__)


#: Operators understood by :func:`parse_item_description`
OPS = {"+": operator.add, "-": operator.sub, "=": operator.eq}


def parse_item_description(
    item: Item, locale: Optional[str] = None
) -> List[Tuple[Callable, str]]:
    """Parse the :attr:`.description` of `item` for a structure expression.

    A common—but **non-standard**—SDMX usage is that :class:`Items <.Item>` in
    :class:`ItemSchemes <.ItemScheme>` contain structure expressions in their
    :attr:`description <.NameableArtefact.description>`. These may resemble::

        A = B + C - D

    …indicating that data for ``A`` can be computed by adding data for ``B`` and ``C``
    and subtracting data for ``D``. In this usage, ``A`` matches the
    :attr:`.IdentifiableArtefact.id` of the `item`, and ``B``, ``C``, and ``D`` are
    usually the IDs of other Items in the same ItemScheme.

    Another form is::

        B + C - D

    In this case, the left-hand side and "=" are omitted.

    :func:`parse_item_description` parses these expressions, returning a list of tuples.
    In each tuple, the first element gives the operation to be applied (in the above,
    examples, implicitly :func:`~operator.add` for "B"), and the second element is the
    ID of the operand.

    Other descriptions are not (yet) supported, including:

    - Multi-line descriptions, in which the structure expression occurs on one line.
    - Structure expressions that appear on lines with other text, for example::

          Some text; A = B + C - D

    Parameters
    ----------
    locale : str
        Use this :attr:`localization <.localizations>` of `item`'s description, instead
        of the default (:obj:`.DEFAULT_LOCALE` or the sole localization).

    Returns
    -------
    list of tuple of (operator, str)
        The list is empty if:

        - `item` has no :attr:`description`.
        - The description does not contain a structure expression.
        - An expression like "A = B + …" exists, but ``A`` does not match the ID of
          `item`.

    Example
    -------
    >>> from sdmx.model.common import Code
    >>> from sdmx.util.item_structure import parse_item_description
    >>> c = Code(id="A", description="A = B + C - D")
    >>> parse_item_description(c)
    [(<function _operator.add(a, b, /)>, 'B'),
     (<function _operator.add(a, b, /)>, 'C'),
     (<function _operator.sub(a, b, /)>, 'D')]

    """
    desc = item.description

    if len(desc.localizations) == 0:
        return []
    elif locale:
        text = desc.localizations[locale]
    else:
        if len(desc.localizations) > 1 and not locale:
            log.warning(
                f">1 localization for {item}.description; using "
                f".localized_default({DEFAULT_LOCALE!r})"
            )
        text = str(desc)

    # Split the text by operator-like expressions (+, -, =) and handle tokens
    result = []
    current_op = operator.add
    current_id = ""
    for token in re.split(r"\s*([\+=-])\s*", text):
        op = OPS.get(token)
        if op is None:
            # The ID of another Item in the ItemScheme → store
            current_id = token
        elif op is operator.eq:
            # An "=" separating the LHS and RHS of the equation → check and discard
            if current_id != item.id:
                log.debug(
                    f'Left-hand side "{current_id} = " does not match ID of {item!r}'
                )
                return []
        else:
            # Any other operator → add the previous (operator, ID) to result; store
            result.append((current_op, current_id))
            current_op = op

    # Add remaining item, if any
    if current_id:
        result.append((current_op, current_id))

    return result


def parse_item(
    itemscheme: ItemScheme, id=str, **kwargs
) -> List[Tuple[Callable, Union[Item, str]]]:
    """Parse a structure expression for the item in `itemscheme` with the given `id`.

    In addition to the behaviour of :func:`parse_item_description`, :func:`parse_item`
    replaces—where possible—the operand :class:`str` IDs with references to specific
    other :class:`Items <.Item>` in the `itemscheme`.

    Where not possible, the operand is returned as-is. For example, in an expression
    like::

        A = B + C - D (until 2022) - E

    …``B``, ``C``, and ``E`` may resolve to references to particular other items, while
    the string "D (until 2022)" will be returned as-is, and not further parsed as a
    reference to an item with ID ``D``. (This functionality may be added in a future
    version of :mod:`sdmx`.)

    Parameters
    ----------
    kwargs :
        Passed to :func:`parse_item_description`.

    Returns
    -------
    list of tuple of (operator, operand)
        Where possible, `operand` is a reference to an existing item in `itemscheme`;
        otherwise the same :class:`str` as returned by :func:`parse_item_description`.
    """

    # Validate
    result, missing = [], []
    for op, operand in parse_item_description(itemscheme[id], **kwargs):
        try:
            # Retrieve the item with ID matching `operand`
            item = itemscheme[operand]
        except KeyError:
            # No such item
            missing.append(operand)
            item = operand
        # Store
        result.append((op, item))

    if len(missing) == len(result) > 0:
        log.debug(f'No tokens matching IDs in "{itemscheme[id].description!s}"')
        return []
    elif len(missing):
        log.debug(
            f"In expression for {itemscheme}[{id}], could not parse item(s): "
            + ", ".join(map(repr, missing))
        )

    return result


def parse_all(
    itemscheme: ItemScheme, **kwargs
) -> Dict[str, List[Tuple[Callable, Union[Item, str]]]]:
    """Parse structure expressions for every item in `itemscheme`.

    Parameters
    ----------
    kwargs :
        Passed to :func:`parse_item_description` via :func:`parse_item`.

    Returns
    -------
    dict of (Item → list)
        Keys are references to the items of `itemscheme`. Values are the results of
        :func:`parse_item`, i.e. possibly empty.
    """
    return {item: parse_item(itemscheme, item.id) for item in itemscheme}
