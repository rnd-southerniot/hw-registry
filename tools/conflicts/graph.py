"""Build the typed graph that the rules query.

Node types
----------

- ``("pin", <pin_id>)`` — PhysicalPin. A board GPIO. Carries the board's
  full pin record on the ``data`` attribute.
- ``("peri", <peripheral>)`` — PeripheralInstance. A peripheral instance
  on the SoC, e.g. ``i2c0``, ``spi2``. Derived by walking every board
  pin's ``alt_functions[].peripheral``.
- ``("ci", <instance>)`` — ComponentInstance. A placement on the system,
  e.g. ``u2``. Carries the component's resolved record on ``resolved``.
- ``("sig", <instance>, <signal>)`` — LogicalSignal. The signal a
  component instance uses, e.g. ``("sig", "u2", "SDA")``. Per-instance
  scoped — a separate node per (instance, signal) pair.

Edge types
----------

- ``uses`` — ComponentInstance → LogicalSignal.
- ``realized_by`` — LogicalSignal → PhysicalPin.
- ``alt_function`` — PhysicalPin → PeripheralInstance, with
  ``function`` / ``direction`` / ``open_drain`` / ``_extended`` data.
- ``i2c_address`` — ComponentInstance → PeripheralInstance, with
  ``address`` / ``address_pin_options`` data. Edge exists only when the
  component declares an I²C address AND the rule infers which
  PeripheralInstance the bus realizes onto.
- ``voltage_requires`` — held as a ComponentInstance node attribute
  rather than an edge in the MVP graph (no second-party Voltage node yet).

The graph is a ``networkx.MultiDiGraph`` so two edges between the same
pair (e.g. pin → i2c0 via SDA + the same pin → i2c0 via SCL on a
different mux key) coexist.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from .loader import ComponentPlacement, System

# Tuple-shaped node ids — unique by type + key.
PinNode = tuple[str, str]  # ("pin", pin_id)
PeriNode = tuple[str, str]  # ("peri", peripheral_id)
CiNode = tuple[str, str]  # ("ci", instance)
SigNode = tuple[str, str, str]  # ("sig", instance, signal_name)


def build_graph(system: System) -> nx.MultiDiGraph:
    """Construct the typed graph from a loaded *system*."""
    g: nx.MultiDiGraph = nx.MultiDiGraph()

    _add_board_pins(g, system.board)
    _add_peripherals(g, system.board)
    _add_alt_function_edges(g, system.board)

    for placement in system.components:
        _add_component(g, placement, system.board)

    return g


def _add_board_pins(g: nx.MultiDiGraph, board: dict[str, Any]) -> None:
    for pin in board.get("pins") or []:
        if not isinstance(pin, dict) or "id" not in pin:
            continue
        g.add_node(
            ("pin", pin["id"]),
            kind="PhysicalPin",
            data=pin,
        )


def _add_peripherals(g: nx.MultiDiGraph, board: dict[str, Any]) -> None:
    """Derive PeripheralInstance nodes from the board's pin alt_function table."""
    seen: set[str] = set()
    for pin in board.get("pins") or []:
        for alt in pin.get("alt_functions") or []:
            peri = alt.get("peripheral") if isinstance(alt, dict) else None
            if peri and peri not in seen:
                seen.add(peri)
                g.add_node(("peri", peri), kind="PeripheralInstance")


def _add_alt_function_edges(g: nx.MultiDiGraph, board: dict[str, Any]) -> None:
    """Each (pin, peripheral) pair gets an ``alt_function`` edge per function."""
    for pin in board.get("pins") or []:
        pin_id = pin.get("id") if isinstance(pin, dict) else None
        if not isinstance(pin_id, str):
            continue
        for alt in pin.get("alt_functions") or []:
            if not isinstance(alt, dict):
                continue
            peri = alt.get("peripheral")
            if not peri:
                continue
            g.add_edge(
                ("pin", pin_id),
                ("peri", peri),
                type="alt_function",
                function=alt.get("function"),
                direction=alt.get("direction"),
                open_drain=alt.get("open_drain", False),
                extended=bool(alt.get("_extended")),
            )


def _add_component(
    g: nx.MultiDiGraph,
    placement: ComponentPlacement,
    board: dict[str, Any],
) -> None:
    ci_node: CiNode = ("ci", placement.instance)
    g.add_node(
        ci_node,
        kind="ComponentInstance",
        ref=placement.ref,
        resolved=placement.resolved,
    )

    # uses + realized_by edges per pin assignment
    for signal_name, physical_pin in placement.pins.items():
        sig_node: SigNode = ("sig", placement.instance, signal_name)
        g.add_node(sig_node, kind="LogicalSignal", instance=placement.instance, signal=signal_name)
        g.add_edge(ci_node, sig_node, type="uses")

        pin_node: PinNode = ("pin", physical_pin)
        if pin_node in g:
            g.add_edge(sig_node, pin_node, type="realized_by")

    # i2c_address edge: the component declares constraints.i2c.address.
    # Resolve the bus by looking at the SDA pin's alt_function table.
    constraints = placement.resolved.get("constraints") or {}
    i2c = constraints.get("i2c") if isinstance(constraints, dict) else None
    if isinstance(i2c, dict) and "address" in i2c:
        peripheral = _infer_i2c_peripheral(g, placement)
        if peripheral is not None:
            g.add_edge(
                ci_node,
                ("peri", peripheral),
                type="i2c_address",
                address=i2c.get("address"),
                address_pin_options=i2c.get("address_pin_options") or [i2c.get("address")],
                requires_pullups_ohms=i2c.get("requires_pullups_ohms"),
            )


def _infer_i2c_peripheral(g: nx.MultiDiGraph, placement: ComponentPlacement) -> str | None:
    """Look at the SDA-bearing pin assignment; return the i2c peripheral name.

    The system YAML's pin-name keys (e.g. ``SDA``) are component-side; the
    board's pins carry alt_functions like ``i2c_sda`` with a ``peripheral:
    i2c0`` pointer. The match is fuzzy by design: any signal-name that
    contains "sda" (case-insensitive) is treated as the I²C SDA wire.
    """
    for signal_name, physical_pin in placement.pins.items():
        if "sda" not in signal_name.lower():
            continue
        pin_node: PinNode = ("pin", physical_pin)
        for _, peri_node, edge_data in g.out_edges(pin_node, data=True):
            if edge_data.get("type") != "alt_function":
                continue
            if (edge_data.get("function") or "").lower().endswith("sda"):
                _kind, peri_id = peri_node
                return str(peri_id)
    return None
