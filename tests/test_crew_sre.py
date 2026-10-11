"""Unit tests for the CrewAI Multi-Agent SRE Triage Engine."""

from unittest.mock import MagicMock, patch

import pytest

from src.crew.sre_crew import SREIncidentCrew
from src.schemas.triage_result import CrewSRETriageResult
from src.schemas.universal_alert import UniversalAlertPayload


@pytest.mark.asyncio
async def test_sre_crew_fallback_diagnosis_payment_gateway_high_severity() -> None:
    """Verify SRE crew heuristic fallback produces rich triage for payment gateway failures."""
    crew_engine = SREIncidentCrew(llm=None)

    alert = UniversalAlertPayload(
        service_name="distributed-payment-gateway",
        environment="production",
        error_message="Postgres connection pool exhausted: timeout waiting for connection after 15000ms",
        error_type="ConnectionStarvation",
        raw_logs={"active_connections": 100, "pool_max": 100},
        metrics={"p99_latency_ms": 5200},
        trace_id="trace-pmt-001",
    )

    result = await crew_engine.execute_triage(alert)

    assert isinstance(result, CrewSRETriageResult)
    assert result.severity_level == "High"
    assert "distributed-payment-gateway" in result.impact_assessment
    assert len(result.anomalies_detected) > 0
    assert "PostgreSQL connection exhaustion" in result.root_cause_analysis
    assert len(result.remediation_runbook) >= 3
    assert result.rollback_guidance is not None
    assert len(result.preventative_measures) > 0


@pytest.mark.asyncio
async def test_sre_crew_fallback_diagnosis_stripe_gateway_timeout_medium_severity() -> (
    None
):
    """Verify Medium severity classification for third-party payment rail timeout."""
    crew_engine = SREIncidentCrew(llm=None)

    alert = UniversalAlertPayload(
        service_name="payment-gateway",
        environment="production",
        error_message="Stripe API 504 Gateway Timeout during settlement capture",
        error_type="GatewayTimeout",
    )

    result = await crew_engine.execute_triage(alert)

    assert result.severity_level == "Medium"
    assert (
        "Stripe" in result.root_cause_analysis
        or "timeout" in result.root_cause_analysis.lower()
    )
    assert len(result.remediation_runbook) > 0


@pytest.mark.asyncio
async def test_sre_crew_fallback_diagnosis_low_severity() -> None:
    """Verify Low severity classification for minor non-critical anomalies."""
    crew_engine = SREIncidentCrew(llm=None)

    alert = UniversalAlertPayload(
        service_name="reporting-worker",
        environment="staging",
        error_message="Minor cache miss count elevated",
        error_type="CacheWarning",
    )

    result = await crew_engine.execute_triage(alert)

    assert result.severity_level == "Low"
    assert "reporting-worker" in result.root_cause_analysis


@pytest.mark.asyncio
async def test_sre_crew_execute_triage_with_mocked_crew_pydantic_output() -> None:
    """Verify execute_triage extracts Pydantic result when CrewAI succeeds."""
    mock_crew_output = MagicMock()
    expected_result = CrewSRETriageResult(
        root_cause_analysis="Mocked RCA from multi-agent crew",
        severity_level="High",
        remediation_runbook=["kubectl rollout restart deployment/service"],
        impact_assessment="Mocked impact statement",
        anomalies_detected=["Anomaly 1", "Anomaly 2"],
    )
    mock_crew_output.pydantic = expected_result

    with (
        patch("src.crew.sre_crew.create_sre_agents") as mock_agents,
        patch("src.crew.sre_crew.create_sre_tasks") as mock_tasks,
        patch("src.crew.sre_crew.Crew") as mock_crew_cls,
        patch("src.crew.sre_crew.get_settings") as mock_settings,
    ):
        mock_settings.return_value.GEMINI_API_KEY = "live-test-key"
        mock_agents.return_value = {"a": MagicMock()}
        mock_tasks.return_value = [MagicMock()]

        mock_instance = MagicMock()
        mock_instance.kickoff.return_value = mock_crew_output
        mock_crew_cls.return_value = mock_instance

        crew_engine = SREIncidentCrew()
        crew_engine.settings = mock_settings.return_value
        crew_engine._llm = MagicMock()

        alert = UniversalAlertPayload(
            service_name="payment-api",
            error_message="Connection timed out",
        )

        result = await crew_engine.execute_triage(alert)
        assert result == expected_result
        assert result.root_cause_analysis == "Mocked RCA from multi-agent crew"


def test_sre_crew_llm_provider_building() -> None:
    """Verify _build_llm handles different configured provider options safely."""
    # Test with gemini
    with patch("src.crew.sre_crew.get_settings") as mock_settings:
        mock_settings.return_value.LLM_PROVIDER = "gemini"
        mock_settings.return_value.GEMINI_API_KEY = "test-api-key"

        crew_engine = SREIncidentCrew()
        assert crew_engine._llm is not None

    # Test with ollama
    with patch("src.crew.sre_crew.get_settings") as mock_settings:
        mock_settings.return_value.LLM_PROVIDER = "ollama"
        mock_settings.return_value.OLLAMA_MODEL = "llama3.2"
        mock_settings.return_value.OLLAMA_BASE_URL = "http://localhost:11434"

        crew_engine = SREIncidentCrew()
        assert crew_engine._llm is not None
