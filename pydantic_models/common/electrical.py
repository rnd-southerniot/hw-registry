"""Electrical specs shared across boards, modules, chips, and sensors."""

from pydantic import Field

from .identifiable import Strict


class VccSpec(Strict):
    """Supply voltage rail."""

    nominal_v: float = Field(description="Nominal supply voltage in volts.")
    min_v: float | None = Field(
        default=None, description="Minimum acceptable supply voltage in volts."
    )
    max_v: float | None = Field(
        default=None, description="Maximum acceptable supply voltage in volts."
    )


class LogicSpec(Strict):
    """Digital I/O voltage levels."""

    voltage_v: float = Field(description="I/O voltage in volts (typically 1.8, 3.3, or 5.0).")
    family: str | None = Field(
        default=None,
        description="Logic family identifier (e.g. CMOS, LVTTL).",
    )
    five_v_tolerant: bool = Field(
        default=False,
        description="True if I/O pins tolerate 5 V signals despite VCCIO < 5 V.",
    )


class CurrentDraw(Strict):
    """Typical and worst-case current consumption."""

    typical_mA: float | None = Field(default=None, description="Typical operating current in mA.")
    max_mA: float | None = Field(default=None, description="Worst-case operating current in mA.")
    sleep_uA: float | None = Field(default=None, description="Deep-sleep current in µA.")


class Electrical(Strict):
    """Aggregate electrical specifications for a component."""

    vcc: VccSpec = Field(description="Supply voltage rail.")
    logic: LogicSpec = Field(description="Digital I/O voltage levels.")
    current_draw: CurrentDraw | None = Field(
        default=None,
        description="Typical and worst-case current draw.",
    )
    power_budget_mA: float | None = Field(
        default=None,
        description="Total power budget at the board / module level in mA.",
    )
