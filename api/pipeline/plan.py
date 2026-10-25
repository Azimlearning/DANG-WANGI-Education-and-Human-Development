"""The Plan: what the planner (an LLM, or a hand-written fake) decides, as validated data. Layer 3 of the pipeline (D-23).

A Plan names controls with ranges, science models with parameters, readouts, and the words around them. It contains no code. The
assembler turns it into a page; the plan checks (plan_checks.py) judge it before any HTML exists. Strict and closed: unknown fields,
coerced types and out-of-range sizes are refused (hard constraint 7 spirit: fail closed).

Provenance: new in v4. The shape follows the PRD section 3.2 layer table and the research note's "data into a template" finding.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,23}$")]
Short = Annotated[str, StringConstraints(min_length=1, max_length=60)]
Sentence = Annotated[str, StringConstraints(min_length=1, max_length=240)]
Unit = Annotated[str, StringConstraints(min_length=1, max_length=12)]

Pattern = Literal["simulation", "virtual_experiment"]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class ControlSpec(_Strict):
    id: Slug
    label: Short
    unit: Unit
    min: float
    max: float
    value: float
    grid: int = Field(ge=1, le=40)
    surface: Literal["slider", "masses", "valve"] = "slider"
    """How the student operates the control. `masses` (Kit `massHanger`) is dragging equal masses onto a hanger: `grid` is then the number of masses. `valve` (Kit `valve`) is a stopcock the student holds or presses: `grid` is then the number of steps."""


class ConstantSpec(_Strict):
    id: Slug
    label: Short
    unit: Unit
    value: float


class ModelUse(_Strict):
    id: Slug
    """The instance id other parts of the Plan refer to."""
    model: Annotated[str, StringConstraints(pattern=r"^[a-z]+\.[a-z_]+$", max_length=40)]
    """The science model id in the Kit manifest, e.g. `mechanics.hookes`."""
    params: dict[Slug, float] = Field(max_length=8)
    inputs: dict[Slug, Slug] = Field(max_length=8)
    """Model input name to the id of a control or a constant."""


class ReadoutSpec(_Strict):
    label: Short
    unit: Unit
    digits: int = Field(ge=0, le=6)
    source: Slug
    """A model instance id."""
    convert_to: Unit | None = None


class GraphSpec(_Strict):
    title: Sentence
    x: Slug
    """A control id."""
    source: Slug
    label: Short
    unit: Unit
    digits: int = Field(ge=0, le=6)


class TableColumn(_Strict):
    label: Short
    unit: Unit
    source: Slug
    """A control id or a model instance id."""
    digits: int = Field(ge=0, le=6)


class TableSpec(_Strict):
    caption: Short
    columns: list[TableColumn] = Field(min_length=1, max_length=6)


class SceneSpec(_Strict):
    """A picture bound to a model's output. It draws the quantity and never prints it."""

    kind: Literal["spring", "titration"]
    source: Slug
    """What is drawn. A spring: a model instance id (the extension, in metres). A titration: a control id (the volume run in, in cm3)."""
    endpoint: Slug | None = None
    """A titration only: the model instance id of the end-point volume, where the indicator changes colour."""
    full: float = Field(gt=0, allow_inf_nan=False)
    """The value, in the source's unit, at which the picture is full (a spring fully stretched, a burette's capacity). A drawing scale; it is never shown."""

    @model_validator(mode="after")
    def _endpoint_only_for_a_titration(self) -> SceneSpec:
        if (self.kind == "titration") != (self.endpoint is not None):
            raise ValueError("a titration scene needs an endpoint, and no other scene has one")
        return self


class ExperimentCard(_Strict):
    aim: Sentence
    hypothesis: Sentence
    independent: Short
    dependent: Short
    controlled: list[Short] = Field(min_length=1, max_length=6)
    apparatus: list[Short] = Field(min_length=1, max_length=8)


class ConceptCheckSpec(_Strict):
    question: Sentence
    options: list[Annotated[str, StringConstraints(min_length=1, max_length=80)]] = Field(min_length=2, max_length=4)
    correct: int = Field(ge=0, le=3)
    explanation: Sentence


class PredictSpec(_Strict):
    prompt: Sentence
    choices: list[Annotated[str, StringConstraints(min_length=1, max_length=80)]] = Field(min_length=2, max_length=4)
    reveal: Sentence


class CustomSlot(_Strict):
    name: Slug
    purpose: Sentence


class Plan(_Strict):
    id: Slug
    title: Short
    goal: Sentence
    pattern: Pattern
    topic: Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+$", max_length=80)]
    experiment_ref: Slug | None = None
    note: Annotated[str, StringConstraints(min_length=1, max_length=400)]
    controls: list[ControlSpec] = Field(min_length=1, max_length=4)
    constants: list[ConstantSpec] = Field(default_factory=list, max_length=4)
    models: list[ModelUse] = Field(min_length=1, max_length=3)
    readouts: list[ReadoutSpec] = Field(min_length=1, max_length=4)
    graphs: list[GraphSpec] = Field(default_factory=list, max_length=2)
    scene: SceneSpec | None = None
    table: TableSpec | None = None
    experiment: ExperimentCard | None = None
    sentences: list[Sentence] = Field(default_factory=list, max_length=6)
    predict: PredictSpec | None = None
    hints: list[Sentence] = Field(default_factory=list, max_length=5)
    concept_check: ConceptCheckSpec | None = None
    worked_solution: list[Sentence] = Field(default_factory=list, max_length=6)
    steps: list[Sentence] = Field(default_factory=list, max_length=8)
    citation_ids: list[Slug] = Field(default_factory=list, max_length=6)
    presentation: Literal["peek", "stage"] = "stage"
    custom: list[CustomSlot] = Field(default_factory=list, max_length=3)

    def model_summaries(self) -> list[dict]:
        """The plan's models in the shape the verifier compares with the page (`plan_models`)."""
        return [{"id": m.model, "params": dict(m.params)} for m in self.models]


def parse(raw: str | bytes) -> Plan:
    """Parse a planner's JSON reply. Raises pydantic.ValidationError, which the plan checks report as PLAN-001."""
    return Plan.model_validate_json(raw)


def json_schema() -> dict:
    return Plan.model_json_schema()


if __name__ == "__main__":  # regenerate the schema file the planner prompt embeds
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "prompts" / "schemas" / "plan.schema.json"
    path.write_text(json.dumps(json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote", path)
