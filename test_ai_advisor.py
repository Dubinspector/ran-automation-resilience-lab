"""Regression / acceptance tests for the v2.6 bounded AI engineering decision gate."""

from copy import deepcopy
import json

from app.ai_advisor import (
    AIEngineeringAdvisor,
    AI_ACTUATION,
    AI_ROLE,
    OpenAIResponsesClient,
    build_ai_advisor_input,
    inject_ai_advisor_widget,
)


def expect(label, condition):
    print(f"{label}: {'PASS' if condition else 'FAIL'}")
    assert condition, label


def optimizer_result():
    return {
        "evaluation_id": "OPT-000123",
        "timestamp": "2026-08-31T08:00:00+00:00",
        "evaluation_mode": "READ_ONLY_NETWORK_SEARCH",
        "automatic_actuation": "DISABLED",
        "actuation_performed": False,
        "ran_state": "HEALTHY",
        "optimization_state": "OPPORTUNITY_FOUND",
        "active_version": "CONFIG-1.1",
        "target_cell": "CELL-JES-B-N28",
        "recommended_action": "REDUCE_TX_POWER",
        "proposed_change": "CELL-JES-B-N28: TX 45.0 -> 40.0 dBm (-5.0 dB)",
        "parameter": "tx_power_dbm",
        "current_value": 45.0,
        "target_value": 40.0,
        "delta": -5.0,
        "objective_gain": 7.2,
        "guardrail_verdict": "PASS",
        "review": "ENGINEERING_REVIEW_RECOMMENDED",
        "evidence": {
            "band": "n28",
            "rsrp_dbm": -87.0,
            "sinr_db": 14.0,
            "prb_utilization_pct": 42.0,
            "active_users": 96,
        },
        "predicted_network_effect": {
            "weighted_sinr_db": 0.42,
            "aggregate_prb_pp": -2.1,
            "max_prb_pp": -4.3,
            "served_ratio_pp": 0.0,
            "degraded_ue_change": 0,
        },
        "cell_impact": [
            {
                "cell_id": "CELL-DJI-C-N28",
                "sinr_delta_db": 1.58,
                "prb_delta_pp": -4.3,
                "active_ue_delta": 0,
            }
        ],
        "search_summary": {
            "configured_cells_scanned": 54,
            "candidates_evaluated": 8,
        },
        "context": {
            "weather": {
                "temperature_c": 20.0,
                "rain_rate_mm_per_h": 0.0,
            },
            "simulation_timestamp": "2026-08-31T10:00:00+02:00",
            "traffic_multiplier": 0.25,
            "steering_mode": "LOAD_AWARE",
        },
    }


def fake_provider_response():
    assessment = {
        "assessment_title": "Interference-limited optimization",
        "engineering_interpretation": (
            "The higher TX power is safe but produces a worse network-wide "
            "trade-off than the deterministic optimizer's selected candidate."
        ),
        "likely_cause": (
            "Additional serving-cell transmit power increases inter-cell "
            "interference without a measurable served-user benefit."
        ),
        "control_decision": "APPROVE",
        "decision_reason": (
            "The exact deterministic candidate passes guardrails, improves "
            "network-wide KPIs and has a bounded low-risk verification path."
        ),
        "risk_level": "LOW",
        "confidence": "HIGH",
        "rationale": [
            "Neighbor SINR improves in the selected lower-power candidate.",
            "Aggregate and maximum PRB utilization decrease.",
            "Served-user ratio remains unchanged.",
            "The candidate passes deterministic guardrails.",
        ],
        "recommended_verification": [
            "Observe serving and neighboring-cell SINR after the change.",
            "Verify PRB utilization over the next observation window.",
            "Confirm served-user ratio and degraded UE count remain stable.",
        ],
        "alternative_hypothesis": (
            "The observed gain may depend on the synthetic traffic snapshot; "
            "repeat under another representative load profile."
        ),
        "evidence_limitations": (
            "This assessment is based only on the supplied synthetic learning-lab evidence."
        ),
    }

    return {
        "id": "resp_test_123",
        "model": "gpt-5.4-mini-test",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(assessment),
                    }
                ],
            }
        ],
        "usage": {
            "input_tokens": 500,
            "output_tokens": 180,
            "total_tokens": 680,
        },
    }


def main():
    print("=" * 96)
    print("V2.6 BOUNDED AI ENGINEERING DECISION GATE REGRESSION / ACCEPTANCE TEST")
    print("=" * 96)

    source = optimizer_result()
    advisor_input = build_ai_advisor_input(
        source,
        alarms=[
            {
                "cell_id": "CELL-DJI-C-N28",
                "severity": "MINOR",
                "type": "DEMO_ALARM",
                "detail": "synthetic test alarm",
                "secret": "must-not-pass-through",
            }
        ],
    )

    expect(
        "AI input contains the requested engineering evidence groups",
        all(
            key in advisor_input
            for key in (
                "current_state",
                "candidate_result",
                "network_effect",
                "guardrails",
                "alarms",
                "weather",
                "traffic",
            )
        ),
    )

    expect(
        "AI input is bounded and does not leak arbitrary alarm fields",
        "secret" not in advisor_input["alarms"][0]
        and len(advisor_input["top_affected_cells"]) <= 8,
    )

    calls = []

    def fake_transport(url, headers, body, timeout_seconds):
        calls.append(
            {
                "url": url,
                "headers": deepcopy(headers),
                "body": deepcopy(body),
                "timeout": timeout_seconds,
            }
        )
        return fake_provider_response()

    client = OpenAIResponsesClient(
        api_key="test-key",
        model="gpt-5.4-mini",
        transport=fake_transport,
    )
    advisor = AIEngineeringAdvisor(client=client, enabled=True)

    result = advisor.analyze(advisor_input)

    expect(
        "Provider request uses Responses API Structured Outputs and store=false",
        len(calls) == 1
        and calls[0]["url"].endswith("/responses")
        and calls[0]["body"]["text"]["format"]["type"] == "json_schema"
        and calls[0]["body"]["text"]["format"]["strict"] is True
        and calls[0]["body"]["store"] is False,
    )

    expect(
        "AI returns only a bounded decision and direct actuation remains disabled",
        result["status"] == "AVAILABLE"
        and result["role"] == AI_ROLE
        and result["ai_actuation"] == AI_ACTUATION,
    )

    expect(
        "Deterministic optimizer decision cannot be overridden by model output",
        result["optimizer_decision"]["target_cell"] == "CELL-JES-B-N28"
        and result["optimizer_decision"]["recommended_action"] == "REDUCE_TX_POWER"
        and result["optimizer_decision"]["target_value"] == 40.0,
    )

    expect(
        "Structured AI result exposes bounded decision, cause, risk and verification",
        result["assessment"]["control_decision"] == "APPROVE"
        and result["assessment"]["confidence"] == "HIGH"
        and result["assessment"]["risk_level"] == "LOW"
        and len(result["assessment"]["recommended_verification"]) >= 2
        and "interference" in result["assessment"]["likely_cause"].lower(),
    )

    cached = advisor.analyze(advisor_input)
    expect(
        "Repeated analysis of the same optimizer evaluation is cached",
        cached.get("cache_hit") is True and len(calls) == 1,
    )

    missing_key_client = OpenAIResponsesClient(api_key="")
    no_key = AIEngineeringAdvisor(
        client=missing_key_client,
        enabled=True,
    ).analyze(advisor_input)
    expect(
        "Missing API key preserves optimizer authority and fails closed for AI actuation",
        no_key["status"] == "NOT_CONFIGURED"
        and no_key["optimizer_decision"]["recommended_action"] == "REDUCE_TX_POWER"
        and no_key["assessment"] is None,
    )

    def failing_transport(url, headers, body, timeout_seconds):
        raise TimeoutError("synthetic provider timeout")

    failing = AIEngineeringAdvisor(
        client=OpenAIResponsesClient(
            api_key="test-key",
            transport=failing_transport,
        ),
        enabled=True,
    ).analyze(advisor_input)
    expect(
        "Provider failure is isolated from the deterministic control loop",
        failing["status"] == "UNAVAILABLE"
        and failing["ai_actuation"] == AI_ACTUATION
        and failing["optimizer_decision"]["target_value"] == 40.0,
    )

    html = inject_ai_advisor_widget(
        '<html><head></head><body><div class="container"></div></body></html>'
    )
    expect(
        "Dashboard exposes AI advisor role, optimizer decision and verification card",
        "AI Engineering Decision Gate" in html
        and "AI control decision" in html
        and "Optimizer decision" in html
        and "Verify after action" in html
        and "/ai-advisor/analyze-latest" in html,
    )

    import app.main as main_module
    expect(
        "FastAPI v2.6 imports without requiring an API key at startup",
        main_module.app is not None
        and main_module.ai_advisor is not None,
    )

    print("\nOVERALL V2.6 AI DECISION GATE TEST: PASS")


if __name__ == "__main__":
    main()
