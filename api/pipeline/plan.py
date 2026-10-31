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
    surface: Literal["slider", "masses", "valve", "dial", "planets"] = "slider"
    """How the student operates the control. `masses` (Kit `massHanger`) is dragging equal masses onto a hanger: `grid` is then the number of masses. `valve` (Kit `valve`) is a stopcock the student holds or presses, and `dial` (Kit `dial`) is a knob the student turns: `grid` is then the number of steps. `planets` (Kit `planetPicker`, W18) is dragging a test mass between the eight planets: min 1, max 8, grid 7, unit `planet`."""


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

    kind: Literal["spring", "titration", "fermentation", "orbit", "refraction", "pressure"]
    source: Slug
    """What is drawn. A spring or a pressure tank: a model instance id (the extension, in metres; the pressure, in Pa). A titration, a fermentation, an orbit or a refraction: a control id (the volume run in, in cm3; the glucose fermented, in mol; the launch speed, in km/s; the angle of incidence, in deg)."""
    endpoint: Slug | None = None
    """A titration only: the model instance id of the end-point volume, where the indicator changes colour."""
    model: Slug | None = None
    """A fermentation: the model instance id of the energy released, fed by the control the scene draws. An orbit: the model instance id of the circular speed. A refraction: the model instance id of the angle of refraction, fed by the control the scene draws."""
    escape: Slug | None = None
    """An orbit only: the model instance id of the escape speed, fed by the same radius constant as the circular speed."""
    full: float = Field(gt=0, allow_inf_nan=False)
    """The value, in the source's unit, at which the picture is full (a spring fully stretched, a burette's capacity; 90 for a refraction, the whole range of an angle). A drawing scale; it is never shown."""

    @model_validator(mode="after")
    def _endpoint_only_for_a_titration(self) -> SceneSpec:
        if (self.kind == "titration") != (self.endpoint is not None):
            raise ValueError("a titration scene needs an endpoint, and no other scene has one")
        if (self.kind in ("fermentation", "orbit", "refraction")) != (self.model is not None):
            raise ValueError("a fermentation, an orbit or a refraction scene needs a model, and no other scene has one")
        if (self.kind == "orbit") != (self.escape is not None):
            raise ValueError("an orbit scene needs an escape speed, and no other scene has one")
        return self


class ChannelBind(_Strict):
    source: Slug
    """A control id or a model instance id: the number this channel draws."""
    full: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    """A fraction channel only: the value drawn as full (a full beaker, the biggest flame). A drawing scale; it is never shown."""


class DropBind(_Strict):
    """Items the student drags onto a part (W17, D-70): each one is one step of a slider with 2 to 8 steps."""

    source: Slug
    """The id of the slider the items add up to."""
    item: Annotated[str, StringConstraints(min_length=1, max_length=40)]
    """What one item is, in the student's words ("Spoon of salt")."""


class ApparatusPart(_Strict):
    """One piece of apparatus on the bench (W16, D-66): a part from the Kit's apparatus catalogue, its label, and what each channel draws. A channel bound to a slider
    gets a grip the student drags on the drawing when the part has one there (W17, D-69); `drop` gives the part a tray of items to drag onto it."""

    kind: Annotated[str, StringConstraints(pattern=r"^[a-z_]{2,24}$")]
    label: Short
    channels: dict[Slug, ChannelBind] = Field(min_length=1, max_length=4)
    drop: DropBind | None = None


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
    apparatus: list[ApparatusPart] = Field(default_factory=list, max_length=4)
    """The bench (W16): up to four reusable parts, each channel bound to a control or a model instance."""
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
    fit: Literal["full", "partial"] = "full"
    """The planner's own judgement (W18, D-76): `full` when this lab shows what the question asks with the Kit's models, `partial` when the Kit has no model for the core
    quantity of the question and the lab can only show something near it. A partial fit is sent to the Free lane first, with this Plan as the fallback."""
    missing: Sentence | None = None
    """With `fit` partial: in one sentence, what the Kit cannot show (for the trace and the Kit gap log)."""

    def model_summaries(self) -> list[dict]:
        """The plan's models in the shape the verifier compares with the page (`plan_models`)."""
        out: list[dict] = []
        for m in self.models:
            entry: dict = {"id": m.model, "params": dict(m.params)}
            readouts = [r.label for r in self.readouts if r.source == m.id]
            series = [g.label for g in self.graphs if g.source == m.id] + [c.label for c in (self.table.columns if self.table else []) if c.source == m.id]
            drawn = self.scene is not None and m.id in {self.scene.source if self.scene.kind in ("spring", "pressure") else None, self.scene.endpoint, self.scene.model, self.scene.escape}
            on_bench = any(ch.source == m.id for part in self.apparatus for ch in part.channels.values())
            # Which instance feeds which value matters when one model is used twice (two energies, two concentrations): the verifier compares each of these with the page.
            if readouts:
                entry["readouts"] = readouts
            if series:
                entry["series"] = series
            if drawn:
                entry["scene"] = True
            if on_bench:
                entry["apparatus"] = True
            out.append(entry)
        return out


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
