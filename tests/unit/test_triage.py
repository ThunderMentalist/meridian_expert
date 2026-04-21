from __future__ import annotations

from pydantic import BaseModel

from meridian_expert.enums import TaskFamily, TaskState
from meridian_expert.llm.client import DeterministicFakeBackend, LLMClient
from meridian_expert.llm.profiles import ModelProfile
from meridian_expert.orchestration.state_machine import can_transition
from meridian_expert.orchestration.triage import (
    TriageModelOutput,
    build_clarification_markdown,
    deterministic_triage_from_text,
    triage_from_text,
)


class StaticTriageBackend(DeterministicFakeBackend):
    def __init__(self, payload: dict):
        self.payload = payload

    def generate_structured(self, profile, instructions, input_text, schema_model):
        return schema_model.model_validate(self.payload)


def _triage_profiles() -> dict[str, ModelProfile]:
    return {
        "triage": ModelProfile(alias="triage", model="gpt-test", reasoning_effort="medium"),
    }


def test_clear_theory_task_no_clarification() -> None:
    payload = TriageModelOutput(
        task_family=TaskFamily.THEORY,
        goal="Explain Meridian model orchestration.",
        needs_clarification=False,
        family_confidence=0.92,
        domain_confidence=0.85,
        cross_repo_route="meridian_model_core",
        candidate_anchor_files=["meridian/model/model.py"],
    ).model_dump()
    client = LLMClient(backend=StaticTriageBackend(payload), profiles=_triage_profiles())

    brief = triage_from_text("Explain how Meridian model.py orchestrates internals.", llm_client=client)

    assert brief.task_family == TaskFamily.THEORY
    assert brief.needs_clarification is False
    assert brief.cross_repo_route == "meridian_model_core"


def test_ambiguous_task_requests_clarification() -> None:
    brief = deterministic_triage_from_text("Help please")

    assert brief.needs_clarification is True
    assert brief.clarification_questions
    assert any("goal" in unknown.lower() for unknown in brief.unknowns)


def test_control_contribution_maps_to_analyzer_compat_shim() -> None:
    brief = deterministic_triage_from_text("Need impact analysis for src/meridian_aux/contribution/control_contribution.py")

    assert brief.cross_repo_route == "analyzer_based_aux"
    assert "meridian/analysis/analyzer.py" in brief.candidate_anchor_files
    assert brief.is_compatibility_shim is True
    assert brief.hotspot_tier == "tier_1"


def test_predict_maps_to_model_object_route() -> None:
    brief = deterministic_triage_from_text("Investigate src/meridian_aux/predict/predict.py posterior drift")

    assert brief.cross_repo_route == "model_object_based_aux"
    assert "meridian/model/model.py" in brief.candidate_anchor_files


def test_nest_sets_under_tested_risk() -> None:
    brief = deterministic_triage_from_text("Can you review src/meridian_aux/nest/nest.py nested decomposition behavior?")

    assert brief.cross_repo_route == "decomposition_bridge_aux"
    assert brief.under_tested_risk is True
    assert "meridian/analysis/visualizer.py" in brief.candidate_anchor_files


def test_fallback_heuristic_without_live_llm() -> None:
    class RaisingBackend(DeterministicFakeBackend):
        def generate_structured(self, profile, instructions, input_text, schema_model: type[BaseModel]):
            raise RuntimeError("offline")

    client = LLMClient(backend=RaisingBackend(), profiles=_triage_profiles())
    brief = triage_from_text("Need details on predict.py and input_data behavior", llm_client=client)

    assert brief.cross_repo_route == "model_object_based_aux"
    assert "meridian/model/model.py" in brief.candidate_anchor_files


def test_state_transitions_for_clarification_path() -> None:
    assert can_transition(TaskState.NEW, TaskState.NEEDS_CLARIFICATION)
    assert can_transition(TaskState.NEW, TaskState.TRIAGED)
    assert can_transition(TaskState.NEEDS_CLARIFICATION, TaskState.TRIAGED)


def test_clarification_markdown_template() -> None:
    brief = deterministic_triage_from_text("bug")
    content = build_clarification_markdown(brief, "T-20260421-0001")

    assert content.startswith("# Clarification request")
    assert "task confirm T-20260421-0001" in content


def test_clarified_direct_request_is_concrete_goal_once_scope_is_present() -> None:
    clarified = (
        "Identify the Bayesian MCMC algorithm that samples the posterior and list what the default hyper-parameters are.\n\n"
        "## Clarification response\n"
        "In the core Meridian repo, identify the Bayesian MCMC algorithm used to sample the posterior and list the default "
        "sampler hyper-parameters. Focus on Meridian itself, not meridian_aux."
    )

    brief = deterministic_triage_from_text(clarified)

    assert brief.needs_clarification is False
    assert all("concrete goal" not in unknown.lower() for unknown in brief.unknowns)


def test_direct_scoped_code_question_is_triaged_without_clarification() -> None:
    prompt = (
        "Only search the Meridian package to determine the answer to the following question. Focus only on the meridian repo, "
        "specifically the model/prior code paths. Do not use meridian_aux. What is the default distribution type, and what are "
        "the default distribution parameters, for the beta coefficient on media variables when using an ROI prior with default "
        "settings? Return a short markdown answer grounded in the Meridian code paths you used."
    )
    brief = triage_from_text(prompt, llm_client=LLMClient(backend=DeterministicFakeBackend(), profiles=_triage_profiles()))
    assert brief.needs_clarification is False


def test_confirmation_marker_unblocks_when_goal_and_scope_exist() -> None:
    text = (
        "Investigate model priors in meridian/model/model.py and explain defaults.\n\n"
        "## Clarification confirmation\n"
        "Yes, proceed with the current interpretation."
    )
    brief = triage_from_text(text, llm_client=LLMClient(backend=DeterministicFakeBackend(), profiles=_triage_profiles()))
    assert brief.needs_clarification is False
