from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from meridian_expert.enums import TaskFamily
from meridian_expert.investigation.bundle_registry import BundleRegistry
from meridian_expert.llm.client import LLMClient
from meridian_expert.llm.prompt_loader import load_prompt
from meridian_expert.models.task import TaskBrief


@dataclass(frozen=True)
class RouteRule:
    route: str
    anchors: list[str]
    concepts: list[str]
    dependency_mode: str | None = None
    hotspot_tier: str | None = None
    compat_shim: bool = False
    under_tested: bool = False


class TriageModelOutput(BaseModel):
    task_family: TaskFamily = TaskFamily.THEORY
    repo_scope: str = "cross_repo"
    package_domain: str = "auto"
    audience: str = "engineer"
    output_format: str = "markdown"
    goal: str = ""
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    evidence_depth: str = "standard"
    snippets_allowed: bool = False
    appendix_requested: bool = False
    unknowns: list[str] = Field(default_factory=list)

    needs_clarification: bool = False
    clarification_questions: list[str] = Field(default_factory=list)
    family_confidence: float | None = None
    domain_confidence: float | None = None
    suggested_bundles: list[str] = Field(default_factory=list)
    anchor_concepts: list[str] = Field(default_factory=list)
    candidate_anchor_files: list[str] = Field(default_factory=list)
    cross_repo_route: str | None = None
    hotspot_tier: str | None = None
    dependency_mode: str | None = None
    is_compatibility_shim: bool = False
    under_tested_risk: bool = False
    attachment_requirements: list[str] = Field(default_factory=list)


EXPLICIT_AUX_FILE_RULES: dict[str, RouteRule] = {
    "control_contribution.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["Analyzer", "control contribution"],
        dependency_mode="compat_shim",
        hotspot_tier="tier_1",
        compat_shim=True,
    ),
    "predict.py": RouteRule(
        route="model_object_based_aux",
        anchors=["meridian/model/model.py"],
        concepts=["Meridian model", "posterior", "input_data"],
        dependency_mode="semi_internal",
        hotspot_tier="tier_1",
    ),
    "charts/transformed.py": RouteRule(
        route="model_object_based_aux",
        anchors=["meridian/model/model.py", "meridian/model/transformers.py"],
        concepts=["transformers", "adstock_hill"],
        dependency_mode="semi_internal",
        hotspot_tier="tier_1",
    ),
    "dashboard/nordic_client.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["Analyzer", "nordic client"],
        dependency_mode="compat_shim",
        hotspot_tier="tier_1",
        compat_shim=True,
    ),
    "nest/nest.py": RouteRule(
        route="decomposition_bridge_aux",
        anchors=["meridian/analysis/visualizer.py", "meridian/analysis/analyzer.py"],
        concepts=["MediaSummary", "nested decomposition"],
        dependency_mode="publicish_output",
        hotspot_tier="tier_1",
        under_tested=True,
    ),
    "multicollinearity.py": RouteRule(
        route="model_object_based_aux",
        anchors=["meridian/model/model.py"],
        concepts=["Meridian model", "media_tensors", "rf_tensors"],
        dependency_mode="semi_internal",
        hotspot_tier="tier_1",
    ),
    "roi.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["roi", "summary_metrics"],
        dependency_mode="public_api",
        hotspot_tier="tier_2",
    ),
    "residuals.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["residuals", "expected_vs_actual"],
        dependency_mode="public_api",
        hotspot_tier="tier_2",
    ),
    "actuals_vs_fitted.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["actuals_vs_fitted", "expected_vs_actual"],
        dependency_mode="public_api",
        hotspot_tier="tier_2",
    ),
    "curves.py": RouteRule(
        route="analyzer_based_aux",
        anchors=["meridian/analysis/analyzer.py"],
        concepts=["response_curves", "hill_curves", "optimal_freq"],
        dependency_mode="publicish_output",
        hotspot_tier="tier_2",
    ),
    "study/iterate.py": RouteRule(
        route="schema_convention_aux",
        anchors=["meridian/model/model.py", "meridian/schema/"],
        concepts=["duck-typed Meridian-like objects"],
        dependency_mode="duck_typed",
        hotspot_tier="tier_3",
    ),
    "coefficients.py": RouteRule(
        route="schema_convention_aux",
        anchors=["meridian/model/model.py", "meridian/schema/"],
        concepts=["coefficient charts", "posterior variable names"],
        dependency_mode="schema_convention",
        hotspot_tier="tier_2",
    ),
    "tstats.py": RouteRule(
        route="schema_convention_aux",
        anchors=["meridian/model/model.py", "meridian/schema/"],
        concepts=["t-stats", "posterior variable names"],
        dependency_mode="schema_convention",
        hotspot_tier="tier_2",
    ),
    "mass.py": RouteRule(
        route="schema_convention_aux",
        anchors=["meridian/model/model.py"],
        concepts=["schema conventions"],
        dependency_mode="duck_typed",
        hotspot_tier="tier_3",
    ),
}

ANALYZER_SIGNALS = [
    "analyzer",
    "summary_metrics",
    "expected_vs_actual",
    "response_curves",
    "hill_curves",
    "optimal_freq",
    "roi.py",
    "residuals.py",
    "actuals_vs_fitted.py",
    "control_contribution.py",
    "nordic_client.py",
]

MODEL_OBJECT_SIGNALS = [
    "predict.py",
    "charts/transformed.py",
    "multicollinearity.py",
    "meridian model",
    "media_tensors",
    "rf_tensors",
    "adstock_hill",
    "knot_values",
    "mu_t",
    "posterior",
    "input_data",
]

DECOMPOSITION_SIGNALS = ["nest.py", "nested decomposition", "mediasummary", "contribution metrics", "decomposition semantics"]
FUTURE_INPUT_SIGNALS = ["future inputs", "coordinate validation", "channel matching", "population strictness"]
SCHEMA_SIGNALS = ["coefficient charts", "t-stats", "posterior variable names", "duck-typed meridian-like objects"]


def triage_from_text(text: str, llm_client: LLMClient | None = None) -> TaskBrief:
    fallback = deterministic_triage_from_text(text)
    model_result = _model_triage(text=text, fallback=fallback, llm_client=llm_client)
    merged = _merge_briefs(base=fallback, model=model_result)
    return _enrich_task_brief(merged, text)


def deterministic_triage_from_text(text: str) -> TaskBrief:
    lower = text.lower()
    family = TaskFamily.THEORY
    if any(k in lower for k in ["how do i use", "snippet", "example", "how to"]):
        family = TaskFamily.USAGE
    if any(k in lower for k in ["impact", "compatibility", "update", "risk", "upgrade"]):
        family = TaskFamily.UPDATES

    rule = _matched_explicit_rule(lower)
    route = rule.route if rule else None
    anchors = list(rule.anchors) if rule else []
    concepts = list(rule.concepts) if rule else []
    dependency_mode = rule.dependency_mode if rule else None
    hotspot_tier = rule.hotspot_tier if rule else None
    compat_shim = rule.compat_shim if rule else False
    under_tested = rule.under_tested if rule else False

    if route is None and any(signal in lower for signal in ANALYZER_SIGNALS):
        route = "analyzer_based_aux"
        anchors.append("meridian/analysis/analyzer.py")
        concepts.extend(["Analyzer", "summary_metrics"])
        dependency_mode = dependency_mode or "public_api"
    if route is None and any(signal in lower for signal in MODEL_OBJECT_SIGNALS):
        route = "model_object_based_aux"
        anchors.append("meridian/model/model.py")
        concepts.extend(["Meridian model", "posterior"])
        dependency_mode = dependency_mode or "semi_internal"
    if route is None and any(signal in lower for signal in DECOMPOSITION_SIGNALS):
        route = "decomposition_bridge_aux"
        anchors.extend(["meridian/analysis/visualizer.py", "meridian/analysis/analyzer.py"])
        concepts.extend(["MediaSummary", "decomposition"])
        dependency_mode = dependency_mode or "publicish_output"
    if route is None and any(signal in lower for signal in FUTURE_INPUT_SIGNALS):
        route = "future_input_contract_aux"
        anchors.append("meridian/data/input_data.py")
        concepts.extend(["future-input contract", "coordinate validation"])
        dependency_mode = dependency_mode or "public_api"
    if route is None and any(signal in lower for signal in SCHEMA_SIGNALS):
        route = "schema_convention_aux"
        concepts.extend(["schema convention", "duck typed"]) 
        dependency_mode = dependency_mode or "schema_convention"

    if route is None and any(token in lower for token in ["meridian/model/model.py", "adstock", "posterior"]):
        route = "meridian_model_core"
        anchors.append("meridian/model/model.py")
        concepts.append("model core")
    if route is None and any(token in lower for token in ["analysis/analyzer.py", "analyzer"]):
        route = "meridian_analyzer_core"
        anchors.append("meridian/analysis/analyzer.py")
        concepts.append("analyzer core")
    if route is None and "optimizer" in lower:
        route = "meridian_optimization"
        anchors.append("meridian/analysis/optimizer.py")
        concepts.append("optimization")
    if route is None:
        route = "generic_cross_repo"

    needs_clarification, questions, attachment_requirements, unknowns = _clarification_signal(text)

    package_domain = "analysis" if "analyzer" in lower else "model" if "model" in lower else "cross_repo"
    evidence_depth = "deep" if any(k in lower for k in ["deep", "full", "comprehensive", "root cause"]) else "standard"
    snippets_allowed = family == TaskFamily.USAGE

    suggested_bundles = _suggest_bundles(family=family, domain=package_domain)

    return TaskBrief(
        title=(text.splitlines()[0].strip() or "Untitled task")[:80],
        task_family=family,
        repo_scope="cross_repo",
        package_domain=package_domain,
        audience="engineer",
        output_format="markdown",
        goal=text[:400],
        constraints=[],
        success_criteria=[],
        evidence_depth=evidence_depth,
        snippets_allowed=snippets_allowed,
        appendix_requested=False,
        unknowns=unknowns,
        needs_clarification=needs_clarification,
        clarification_questions=questions,
        family_confidence=0.72,
        domain_confidence=0.7,
        suggested_bundles=suggested_bundles,
        anchor_concepts=_dedupe(concepts),
        candidate_anchor_files=_dedupe(anchors),
        cross_repo_route=route,
        hotspot_tier=hotspot_tier,
        dependency_mode=dependency_mode,
        is_compatibility_shim=compat_shim,
        under_tested_risk=under_tested,
        attachment_requirements=attachment_requirements,
    )


def _model_triage(text: str, fallback: TaskBrief, llm_client: LLMClient | None) -> TaskBrief | None:
    client = llm_client or LLMClient()
    instructions = load_prompt("triage")
    structured_input = (
        "Classify and complete triage for the request. Always return valid schema fields.\n"
        "Use route labels: analyzer_based_aux, model_object_based_aux, decomposition_bridge_aux, future_input_contract_aux, "
        "schema_convention_aux, meridian_model_core, meridian_analyzer_core, meridian_optimization, generic_cross_repo.\n"
        f"\nRequest:\n{text}\n"
        f"\nFallback hint:\n{fallback.model_dump_json(indent=2)}"
    )
    try:
        out = client.generate_structured("triage", instructions, structured_input, TriageModelOutput)
    except Exception:
        return None

    try:
        return TaskBrief(
            title=(text.splitlines()[0].strip() or "Untitled task")[:80],
            task_family=out.task_family,
            repo_scope=out.repo_scope,
            package_domain=out.package_domain,
            audience=out.audience,
            output_format=out.output_format,
            goal=(out.goal or text)[:400],
            constraints=out.constraints,
            success_criteria=out.success_criteria,
            evidence_depth=out.evidence_depth,
            snippets_allowed=out.snippets_allowed,
            appendix_requested=out.appendix_requested,
            unknowns=out.unknowns,
            needs_clarification=out.needs_clarification,
            clarification_questions=out.clarification_questions,
            family_confidence=out.family_confidence,
            domain_confidence=out.domain_confidence,
            suggested_bundles=out.suggested_bundles,
            anchor_concepts=out.anchor_concepts,
            candidate_anchor_files=out.candidate_anchor_files,
            cross_repo_route=out.cross_repo_route,
            hotspot_tier=out.hotspot_tier,
            dependency_mode=out.dependency_mode,
            is_compatibility_shim=out.is_compatibility_shim,
            under_tested_risk=out.under_tested_risk,
            attachment_requirements=out.attachment_requirements,
        )
    except Exception:
        return None


def _merge_briefs(base: TaskBrief, model: TaskBrief | None) -> TaskBrief:
    if model is None:
        return base

    merged = base.model_copy(deep=True)
    for field_name in type(model).model_fields:
        model_value = getattr(model, field_name)
        base_value = getattr(base, field_name)

        if model_value in (None, ""):
            continue
        if isinstance(model_value, list):
            if model_value:
                setattr(merged, field_name, _dedupe([*base_value, *model_value]))
            continue
        if isinstance(model_value, bool):
            if model_value:
                setattr(merged, field_name, True)
            continue
        setattr(merged, field_name, model_value)

    if model.task_family:
        merged.task_family = model.task_family
    if model.family_confidence is not None:
        merged.family_confidence = model.family_confidence
    if model.domain_confidence is not None:
        merged.domain_confidence = model.domain_confidence

    if model.needs_clarification:
        merged.needs_clarification = True

    return merged


def _enrich_task_brief(brief: TaskBrief, text: str) -> TaskBrief:
    lower = text.lower()
    rule = _matched_explicit_rule(lower)
    if rule:
        brief.cross_repo_route = rule.route
        brief.candidate_anchor_files = _dedupe([*brief.candidate_anchor_files, *rule.anchors])
        brief.anchor_concepts = _dedupe([*brief.anchor_concepts, *rule.concepts])
        brief.dependency_mode = brief.dependency_mode or rule.dependency_mode
        brief.hotspot_tier = brief.hotspot_tier or rule.hotspot_tier
        brief.is_compatibility_shim = brief.is_compatibility_shim or rule.compat_shim
        brief.under_tested_risk = brief.under_tested_risk or rule.under_tested

    if brief.cross_repo_route == "analyzer_based_aux":
        brief.candidate_anchor_files = _dedupe([*brief.candidate_anchor_files, "meridian/analysis/analyzer.py"])
    if brief.cross_repo_route == "model_object_based_aux":
        brief.candidate_anchor_files = _dedupe([*brief.candidate_anchor_files, "meridian/model/model.py"])
    if brief.cross_repo_route == "decomposition_bridge_aux":
        brief.candidate_anchor_files = _dedupe([*brief.candidate_anchor_files, "meridian/analysis/visualizer.py", "meridian/analysis/analyzer.py"])
    if brief.cross_repo_route == "future_input_contract_aux":
        brief.candidate_anchor_files = _dedupe([*brief.candidate_anchor_files, "meridian/data/input_data.py"])

    if not brief.suggested_bundles:
        brief.suggested_bundles = _suggest_bundles(brief.task_family, brief.package_domain)

    if brief.needs_clarification and not brief.clarification_questions:
        needs_clarification, questions, attachment_requirements, unknowns = _clarification_signal(text)
        brief.needs_clarification = needs_clarification
        brief.clarification_questions = questions
        brief.attachment_requirements = _dedupe([*brief.attachment_requirements, *attachment_requirements])
        brief.unknowns = _dedupe([*brief.unknowns, *unknowns])

    return brief


def _matched_explicit_rule(lower: str) -> RouteRule | None:
    for key, rule in EXPLICIT_AUX_FILE_RULES.items():
        if key in lower:
            return rule
    return None


def _clarification_signal(text: str) -> tuple[bool, list[str], list[str], list[str]]:
    lower = text.lower()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    missing: list[str] = []
    questions: list[str] = []
    attachment_requirements: list[str] = []

    has_goal = any(
        token in lower
        for token in [
            "need",
            "want",
            "explain",
            "investigate",
            "debug",
            "implement",
            "fix",
            "identify",
            "list",
            "find",
            "locate",
            "trace",
            "summarize",
            "describe",
            "what",
            "which",
            "why",
            "how",
        ]
    )
    has_scope = any(token in lower for token in ["meridian", "meridian_aux", "repo", ".py", "analysis", "model", "dashboard"])
    has_output = any(token in lower for token in ["output", "format", "markdown", "summary", "report", "table"])
    has_audience = any(token in lower for token in ["audience", "engineer", "pm", "analyst", "team"])
    has_context = any(token in lower for token in ["traceback", "error", "failing", "snippet", "stack", "exception", "repro"])

    if len(" ".join(lines)) < 30 or not has_goal:
        missing.append("concrete goal")
        questions.append("What exact question or outcome do you want from this task?")
    if not has_scope:
        missing.append("repo scope")
        questions.append("Which repo and file/module should this focus on (meridian, meridian_aux, or both)?")
    if not has_output and len(text.strip()) < 40:
        questions.append("What output format do you want (short answer, deep report, code patch, checklist)?")
    if not has_audience and len(text.strip()) < 40:
        questions.append("Who is the audience for the final output?")

    if any(token in lower for token in ["error", "bug", "failing", "traceback", "broken"]) and not has_context:
        missing.append("failing context")
        questions.append("Please share the failing snippet, stack trace, or reproducible command.")
        attachment_requirements.append("error logs or stack trace")

    return bool(missing), _dedupe(questions), _dedupe(attachment_requirements), [f"Missing {item}" for item in missing]


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _suggest_bundles(family: TaskFamily, domain: str) -> list[str]:
    bundle_registry = BundleRegistry()
    bundles = bundle_registry.rank_for(family.value, domain)
    if not bundles:
        bundles = bundle_registry.list()
    return [bundle["name"] for bundle in bundles[:2]]


def build_clarification_markdown(brief: TaskBrief) -> str:
    lines = ["# Clarification request", "", "Please provide the following before we continue triage:", ""]
    for question in brief.clarification_questions:
        lines.append(f"- {question}")
    if brief.attachment_requirements:
        lines.extend(["", "## Attachments requested"])
        lines.extend([f"- {item}" for item in brief.attachment_requirements])
    return "\n".join(lines) + "\n"
