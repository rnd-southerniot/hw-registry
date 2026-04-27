"""Rule functions for the pin-conflict checker.

Each rule is a pure function ``(graph, system) -> list[Diagnostic]``.
Rules read from the typed graph (built in ``graph.py``) and from the
``System`` model (loader). Rules don't mutate state; the orchestrator
collects all diagnostics and forwards them to the SARIF / text / JSON
emitters.

Rules cover:

  ERROR
  - GPIO_DOUBLE_USE              gpio_double_use
  - I2C_ADDR_CLASH               i2c_address_clash
  - VOLTAGE_MISMATCH             voltage_mismatch
  - MISSING_REQUIRED_INTERRUPT   missing_required_interrupt
  - ALT_FUNCTION_UNSUPPORTED     alt_function_unsupported (INFO for soft-extensions)

  WARN
  - STRAPPING_PIN_MISUSE         strapping_pin_misuse
  - CURRENT_BUDGET_EXCEEDED      current_budget_exceeded
  - MISSING_I2C_PULLUPS          missing_i2c_pullups
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import networkx as nx

from .diagnostic import Diagnostic, Severity
from .loader import ComponentPlacement, System

# --- Rule helpers --------------------------------------------------------


def _component_instances(graph: nx.MultiDiGraph) -> Iterable[tuple[str, dict[str, Any]]]:
    for node, data in graph.nodes(data=True):
        if data.get("kind") == "ComponentInstance":
            _kind, instance = node
            yield instance, data


def _signal_to_pin(graph: nx.MultiDiGraph) -> dict[tuple[str, str], str]:
    """Map (instance, signal) → physical pin id."""
    out: dict[tuple[str, str], str] = {}
    for src, tgt, data in graph.edges(data=True):
        if data.get("type") != "realized_by":
            continue
        kind, instance, signal_name = src
        if kind != "sig":
            continue
        _, pin_id = tgt
        out[(instance, signal_name)] = pin_id
    return out


def _pin_alt_functions(graph: nx.MultiDiGraph, pin_id: str) -> list[dict[str, Any]]:
    """Return the board pin's full ``alt_functions`` list.

    Reads from the pin node's stored ``data`` attribute, NOT from outgoing
    ``alt_function`` edges — those edges only exist for alts that target
    a PeripheralInstance (i.e. functions with a ``peripheral`` field). A
    plain ``{function: gpio, direction: bidir}`` alt has no peripheral
    and would otherwise be invisible.
    """
    pin_node = ("pin", pin_id)
    if pin_node not in graph:
        return []
    pin_data = graph.nodes[pin_node].get("data") or {}
    return list(pin_data.get("alt_functions") or [])


def _is_shared_bus_function(function: str | None) -> bool:
    """True if the function name describes a shared-bus signal (multiple
    components legitimately drive or sense the same physical pin)."""
    if not function:
        return False
    lowered = function.lower()
    # I²C: open-drain shared by all devices.
    # SPI: SCLK + MISO + MOSI shared across slaves; CS is per-slave.
    # 1-Wire: shared by all slaves.
    return any(
        token in lowered
        for token in ("i2c_sda", "i2c_scl", "spi_sclk", "spi_miso", "spi_mosi", "onewire")
    )


# --- ERROR rules ---------------------------------------------------------


def gpio_double_use(graph: nx.MultiDiGraph, _system: System) -> list[Diagnostic]:
    """A physical pin is used by ≥2 components and not on a shared-bus role."""
    diags: list[Diagnostic] = []

    # Group LogicalSignal nodes by the PhysicalPin they realize on.
    pin_users: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for src, tgt, data in graph.edges(data=True):
        if data.get("type") != "realized_by":
            continue
        kind, instance, signal_name = src
        if kind != "sig":
            continue
        _, pin_id = tgt
        pin_users[pin_id].append((instance, signal_name))

    for pin_id, users in pin_users.items():
        if len(users) <= 1:
            continue
        # Filter out users that are on a shared-bus role for this pin.
        offending: list[tuple[str, str]] = []
        for instance, signal_name in users:
            if _signal_is_shared_bus(graph, pin_id, signal_name):
                continue
            offending.append((instance, signal_name))
        if len(offending) <= 1:
            continue

        instances = sorted({i for i, _ in offending})
        diags.append(
            Diagnostic(
                id="GPIO_DOUBLE_USE",
                severity="error",
                rule="gpio_double_use",
                message=(
                    f"pin {pin_id} is assigned to {len(offending)} components "
                    f"({', '.join(instances)}) on non-shared roles"
                ),
                locations=[
                    {"component_instance": instance, "pin": pin_id, "signal": sig}
                    for instance, sig in offending
                ],
            )
        )
    return diags


def _signal_is_shared_bus(
    graph: nx.MultiDiGraph,
    pin_id: str,
    signal_name: str,
) -> bool:
    """Heuristic: a signal name like ``SDA`` mapped onto a pin whose
    alt_function table includes any matching shared-bus function counts
    as shared. Component authors using non-canonical names (``DATA``)
    won't satisfy this — that's intentional, prompts a name fix."""
    candidate = signal_name.lower()
    for alt in _pin_alt_functions(graph, pin_id):
        function = (alt.get("function") or "").lower()
        if not _is_shared_bus_function(function):
            continue
        # function="i2c_sda" matches signal="sda" / "SDA" / "i2c_sda".
        if candidate in function or function.endswith("_" + candidate):
            return True
    return False


def i2c_address_clash(graph: nx.MultiDiGraph, _system: System) -> list[Diagnostic]:
    """Two components on the same I²C bus with overlapping address options."""
    diags: list[Diagnostic] = []

    # Group i2c_address edges by PeripheralInstance.
    by_bus: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for src, tgt, data in graph.edges(data=True):
        if data.get("type") != "i2c_address":
            continue
        _kind, instance = src
        _, peri = tgt
        by_bus[peri].append((instance, dict(data)))

    for bus, attached in by_bus.items():
        if len(attached) <= 1:
            continue
        # Compare every pair.
        for i in range(len(attached)):
            for j in range(i + 1, len(attached)):
                inst_a, edge_a = attached[i]
                inst_b, edge_b = attached[j]
                clash = _i2c_clash_check(edge_a, edge_b)
                if clash is None:
                    continue
                addr, hint = clash
                diags.append(
                    Diagnostic(
                        id="I2C_ADDR_CLASH",
                        severity="error",
                        rule="i2c_address_clash",
                        message=(
                            f"components {inst_a} and {inst_b} both at I²C address "
                            f"0x{addr:02X} on bus {bus}; {hint}"
                        ),
                        locations=[
                            {"component_instance": inst_a, "bus": bus},
                            {"component_instance": inst_b, "bus": bus},
                        ],
                    )
                )
    return diags


def _i2c_clash_check(
    edge_a: dict[str, Any],
    edge_b: dict[str, Any],
) -> tuple[int, str] | None:
    """Return (clash_address, remediation_hint) if A and B clash, else None."""
    addr_a = edge_a.get("address")
    addr_b = edge_b.get("address")
    if addr_a is None or addr_b is None:
        return None
    if addr_a != addr_b:
        return None  # different default addresses, no clash

    opts_b = edge_b.get("address_pin_options") or [addr_b]

    # Both at same default — find an alternative on B that doesn't overlap A's defaults.
    alternatives_b = [a for a in opts_b if a != addr_a]
    if alternatives_b:
        suggested = alternatives_b[0]
        hint = f"set ADDR strap to 0x{suggested:02X} on the second instance"
    else:
        # No alternatives at all — clash is unavoidable without a level
        # shifter / bus mux.
        hint = "the second device offers no alternative address; use a separate I²C bus or a mux"
    return int(addr_a), hint


def voltage_mismatch(graph: nx.MultiDiGraph, system: System) -> list[Diagnostic]:
    """A component's electrical envelope is incompatible with the board's IO domain."""
    diags: list[Diagnostic] = []
    board_logic = (system.board.get("electrical") or {}).get("logic") or {}
    bus_voltage = board_logic.get("voltage_v")
    if bus_voltage is None:
        return diags

    for instance, data in _component_instances(graph):
        resolved = data.get("resolved") or {}
        electrical = resolved.get("electrical") or {}
        vcc = electrical.get("vcc") or {}
        component_max = vcc.get("max_v")
        component_logic = electrical.get("logic") or {}
        five_v_tol = component_logic.get("five_v_tolerant", False)

        if component_max is not None and component_max < bus_voltage:
            diags.append(
                Diagnostic(
                    id="VOLTAGE_MISMATCH",
                    severity="error",
                    rule="voltage_mismatch",
                    message=(f"{instance}: vcc.max_v {component_max} V < board IO {bus_voltage} V"),
                    locations=[{"component_instance": instance}],
                )
            )
        elif bus_voltage > 3.6 and not five_v_tol:
            diags.append(
                Diagnostic(
                    id="VOLTAGE_MISMATCH",
                    severity="error",
                    rule="voltage_mismatch",
                    message=(
                        f"{instance}: board IO {bus_voltage} V > 3.6 V and component "
                        f"is not five_v_tolerant"
                    ),
                    locations=[{"component_instance": instance}],
                )
            )
    return diags


def missing_required_interrupt(graph: nx.MultiDiGraph, _system: System) -> list[Diagnostic]:
    """Component declares ``constraints.interrupt.required: true`` but no IRQ pin mapping."""
    diags: list[Diagnostic] = []

    sig_pin = _signal_to_pin(graph)
    for instance, data in _component_instances(graph):
        resolved = data.get("resolved") or {}
        constraints = resolved.get("constraints") or {}
        irq = constraints.get("interrupt") or {}
        if not irq.get("required"):
            continue

        irq_pin_name = irq.get("pin") or "INT"
        # Did the system YAML map any signal that looks like the irq pin?
        candidates = {
            sig
            for (inst, sig) in sig_pin
            if inst == instance and sig.lower() == irq_pin_name.lower()
        }
        if candidates:
            continue

        diags.append(
            Diagnostic(
                id="MISSING_REQUIRED_INTERRUPT",
                severity="error",
                rule="missing_required_interrupt",
                message=(
                    f"{instance}: constraints.interrupt.required is true but no "
                    f"{irq_pin_name!r} pin mapping is provided"
                ),
                locations=[{"component_instance": instance}],
            )
        )
    return diags


def alt_function_unsupported(graph: nx.MultiDiGraph, _system: System) -> list[Diagnostic]:
    """Each (signal, physical_pin) assignment must match an AltFunction on the pin.

    Soft-fallback AltFunctions on the COMPONENT side (``_extended: true``)
    downgrade the diagnostic to INFO — we know the parent vocabulary
    didn't define this function, so the conflict checker reports
    informationally rather than failing the build.
    """
    diags: list[Diagnostic] = []

    for instance, ci_data in _component_instances(graph):
        resolved = ci_data.get("resolved") or {}
        component_alts_by_pin = _component_alt_function_index(resolved)

        for src, tgt, edge in graph.edges(data=True):
            if edge.get("type") != "uses":
                continue
            kind, ci_inst = src
            if ci_inst != instance:
                continue
            _, _, signal_name = tgt

            # Find the realizing physical pin.
            phys_pin = None
            for _sig, pin_node, e in graph.out_edges(tgt, data=True):
                if e.get("type") == "realized_by":
                    _, phys_pin = pin_node
                    break
            if phys_pin is None:
                continue

            if _signal_is_shared_bus(graph, phys_pin, signal_name):
                # I²C/SPI/1-Wire — function support is conventional; trust it.
                continue

            board_alts = _pin_alt_functions(graph, phys_pin)
            if _function_supported(signal_name, board_alts):
                continue

            # Not on the board's alt_function table for this pin.
            severity: Severity = (
                "info" if _is_extended_on_component(component_alts_by_pin, signal_name) else "error"
            )
            diags.append(
                Diagnostic(
                    id="ALT_FUNCTION_UNSUPPORTED",
                    severity=severity,
                    rule="alt_function_unsupported",
                    message=(
                        f"{instance}: signal {signal_name!r} on pin {phys_pin} "
                        f"is not in the board pin's alt_function table"
                    ),
                    locations=[
                        {"component_instance": instance, "pin": phys_pin, "signal": signal_name}
                    ],
                )
            )
    return diags


_BUS_TOKENS: dict[str, tuple[str, ...]] = {
    "i2c": ("i2c", "sda", "scl"),
    "spi": ("spi", "miso", "mosi", "sclk", "cipo", "copi"),
    "uart": ("uart", "rxd", "txd"),
    "i2s": ("i2s",),
    "onewire": ("onewire",),
    "usb": ("usb",),
}


def _function_supported(signal_name: str, board_alts: list[dict[str, Any]]) -> bool:
    """Loose compatibility check between a system-YAML signal name and a board pin.

    Strategy:

    - Identify the bus family of the signal (if any) by token match. e.g.
      ``uart2_tx`` → ``uart`` family; ``SDA`` → ``i2c`` family;
      ``RESET`` / ``IRQ`` / ``ALERT`` → no family (generic).
    - Bus-family signals accept any board function in the same family.
      We deliberately do NOT validate TX↔RX directionality from names —
      that requires understanding which side of the wire each component
      sits on; reviewers catch reversed cross-overs.
    - Family-less signals accept any pin that exposes a ``gpio``
      alt_function (i.e. can be a plain digital input/output) — RESET,
      ALERT, IRQ-style lines are firmware-driven generic GPIO.
    - On MCUs with full GPIO matrices (ESP32 family), almost everything
      is GPIO-capable so this rule fires rarely; on MCUs with fixed
      peripherals (STM32), it fires meaningfully when a peripheral
      isn't routable to a chosen pin.
    """
    candidate = signal_name.lower()

    family = None
    for fam, tokens in _BUS_TOKENS.items():
        if any(t in candidate for t in tokens):
            family = fam
            break

    if family is None:
        # Generic signal — accept any GPIO-capable pin.
        return any((alt.get("function") or "").lower() == "gpio" for alt in board_alts)

    family_tokens = _BUS_TOKENS[family]
    for alt in board_alts:
        function = (alt.get("function") or "").lower()
        if any(t in function for t in family_tokens):
            return True
    return False


def _component_alt_function_index(
    resolved: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Index a resolved component's pins by id → list of AltFunction dicts."""
    out: dict[str, list[dict[str, Any]]] = {}
    for pin in resolved.get("pins") or []:
        if isinstance(pin, dict) and "id" in pin:
            out[pin["id"]] = list(pin.get("alt_functions") or [])
    return out


def _is_extended_on_component(
    component_alts_by_pin: dict[str, list[dict[str, Any]]],
    signal_name: str,
) -> bool:
    """True if any component pin has a soft-fallback AltFunction matching signal_name."""
    target = signal_name.lower()
    for alts in component_alts_by_pin.values():
        for alt in alts:
            if not isinstance(alt, dict):
                continue
            if not alt.get("_extended"):
                continue
            if (alt.get("function") or "").lower() == target:
                return True
    return False


# --- WARN rules ----------------------------------------------------------


def strapping_pin_misuse(graph: nx.MultiDiGraph, system: System) -> list[Diagnostic]:
    """Any system use of a board strapping pin is a WARN."""
    diags: list[Diagnostic] = []
    strapping = set(system.board.get("strapping_pins") or [])
    if not strapping:
        return diags

    for src, tgt, edge in graph.edges(data=True):
        if edge.get("type") != "realized_by":
            continue
        _, pin_id = tgt
        if pin_id not in strapping:
            continue
        kind, instance, signal_name = src
        diags.append(
            Diagnostic(
                id="STRAPPING_PIN_MISUSE",
                severity="warning",
                rule="strapping_pin_misuse",
                message=(
                    f"{instance}: signal {signal_name!r} mapped to strapping pin "
                    f"{pin_id}; verify boot-time logic level matches strap value"
                ),
                locations=[{"component_instance": instance, "pin": pin_id, "signal": signal_name}],
            )
        )
    return diags


def current_budget_exceeded(_graph: nx.MultiDiGraph, system: System) -> list[Diagnostic]:
    """Sum of typ_active_mA across components exceeds board.electrical.power_budget_mA."""
    budget = (system.board.get("electrical") or {}).get("power_budget_mA")
    if budget is None:
        return []

    total = 0.0
    for placement in system.components:
        electrical = placement.resolved.get("electrical") or {}
        current_draw = electrical.get("current_draw") or {}
        typ_active = current_draw.get("typ_active_mA")
        if typ_active is not None:
            total += float(typ_active)

    if total <= float(budget):
        return []

    return [
        Diagnostic(
            id="CURRENT_BUDGET_EXCEEDED",
            severity="warning",
            rule="current_budget_exceeded",
            message=(
                f"summed component current {total:.1f} mA > board "
                f"power_budget_mA {float(budget):.1f}"
            ),
            locations=[{"component_instance": p.instance} for p in system.components],
        )
    ]


def missing_i2c_pullups(graph: nx.MultiDiGraph, system: System) -> list[Diagnostic]:
    """An I²C bus in use, no component declares pullups, no system-level declaration."""
    diags: list[Diagnostic] = []

    # Did the system YAML's components opt in to a system-level declaration?
    # The blueprint does not formalize this yet — treat absence as no declaration.

    by_bus_components: dict[str, list[ComponentPlacement]] = defaultdict(list)
    by_bus_pullups: dict[str, list[int]] = defaultdict(list)

    for src, tgt, edge in graph.edges(data=True):
        if edge.get("type") != "i2c_address":
            continue
        _kind, instance = src
        _, peri = tgt
        # Find the placement.
        placement = next((p for p in system.components if p.instance == instance), None)
        if placement is None:
            continue
        by_bus_components[peri].append(placement)
        if edge.get("requires_pullups_ohms"):
            by_bus_pullups[peri].append(int(edge["requires_pullups_ohms"]))

    for bus, components in by_bus_components.items():
        if by_bus_pullups[bus]:
            continue  # at least one component declared pullup requirements
        instance_names = sorted(p.instance for p in components)
        diags.append(
            Diagnostic(
                id="MISSING_I2C_PULLUPS",
                severity="warning",
                rule="missing_i2c_pullups",
                message=(
                    f"I²C bus {bus} ({', '.join(instance_names)}) has no component "
                    f"declaring requires_pullups_ohms; ensure pullups are present on "
                    f"the board"
                ),
                locations=[{"component_instance": p.instance, "bus": bus} for p in components],
            )
        )
    return diags


# --- Orchestrator --------------------------------------------------------

ALL_RULES = (
    gpio_double_use,
    i2c_address_clash,
    voltage_mismatch,
    missing_required_interrupt,
    alt_function_unsupported,
    strapping_pin_misuse,
    current_budget_exceeded,
    missing_i2c_pullups,
)


def run_all(graph: nx.MultiDiGraph, system: System) -> list[Diagnostic]:
    """Run every rule and return aggregated diagnostics."""
    diags: list[Diagnostic] = []
    for rule in ALL_RULES:
        diags.extend(rule(graph, system))
    return diags
