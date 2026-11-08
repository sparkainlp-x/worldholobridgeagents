#!/usr/bin/env python3
"""Seeded synthetic policy comparison; not evidence of deployment safety."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import time
from typing import Any
from uuid import UUID, uuid5

from jsonschema import Draft202012Validator, FormatChecker

from matrix_core.policy import decide_activation
from matrix_core.synthetic import NOW, SCENARIO_CLASSES, build_activation_case


ROOT = Path(__file__).parents[1]
SCHEMA_PATH = ROOT / "schemas" / "v0.1.0" / "core.schema.json"
_NAMESPACE = UUID("f0da39e8-47d1-4fdb-9be5-4db4cd5fc96f")
_REASON_CATALOG = {
    "ACTOR_ROLE_UNAUTHORIZED", "CONSENT_MISSING_EXPIRED_OR_REVOKED",
    "CURRENT_ACCEPTANCE_MISSING", "EQUIPMENT_MANIFEST_UNREVIEWED_OR_STALE",
    "EVIDENCE_UNREVIEWED_OR_UNKNOWN", "INSTALLATION_NOT_FOUND",
    "INVALID_INSTALLATION_STATE", "PARTICIPANT_UNAVAILABLE",
    "REQUIRED_CHECK_MISSING_STALE_OR_UNREVIEWED", "STOP_CONTROL_ACTIVE",
    "TENANT_MISMATCH", "DUPLICATE_RECORD_ID", "CROSS_TENANT_REFERENCE",
    "RELATIONSHIP_TARGET_MISSING", "RELATIONSHIP_TARGET_TYPE_INVALID",
}
_ORACLE_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_ORACLE_VALIDATOR = Draft202012Validator(
    _ORACLE_SCHEMA, format_checker=FormatChecker()
)


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def contract_oracle(case: dict[str, Any]) -> bool:
    """Independent, direct contract checklist; it does not call reference policy."""
    records = case["records"]
    if any(_ORACLE_VALIDATOR.is_valid(record) is False for record in records):
        return False
    ids = [row["id"] for row in records]
    if len(ids) != len(set(ids)):
        return False
    by_id = {row["id"]: row for row in records}
    tenant_id = case["actor"].get("tenant_id")
    installation = by_id.get(case["installation_id"])
    if not installation or installation.get("record_type") != "installation":
        return False
    if installation["tenant_id"] != tenant_id:
        return False
    if installation["status"] not in {"draft", "ready"} or installation["stop_requested"]:
        return False
    actor_memberships = [
        row for row in records
        if row.get("record_type") == "membership"
        and row.get("installation_id") == installation["id"]
        and row.get("participant_id") == case["actor"].get("id")
        and row.get("tenant_id") == tenant_id
        and row.get("active") is True
        and row.get("role") == case["actor"].get("role")
        and row.get("role") in {"facilitator", "tenant_admin"}
        and (row.get("valid_until") is None or _time(row["valid_until"]) > case["now"])
    ]
    if not actor_memberships:
        return False
    if any(
        row.get("record_type") == "evidence"
        and row.get("subject_id") == installation["id"]
        and row.get("tenant_id") == tenant_id
        and (
            row.get("review_status") != "reviewed"
            or row.get("execution_status") in {"not_run", "unknown", "failed"}
            or _time(row["expires_at"]) <= case["now"]
        )
        for row in records
    ):
        return False
    for participant_id in installation["participant_ids"]:
        participant = by_id.get(participant_id)
        if (
            not participant or participant.get("record_type") != "participant"
            or participant.get("tenant_id") != tenant_id or participant.get("status") != "active"
        ):
            return False
        consent_ok = any(
            row.get("record_type") == "consent"
            and row.get("participant_id") == participant_id
            and row.get("tenant_id") == tenant_id
            and row.get("purpose") == "installation_activation"
            and row.get("recipient") == "matrix-core"
            and "installation_status" in row.get("field_scopes", [])
            and row.get("revoked_at") is None
            and _time(row["valid_from"]) <= case["now"] < _time(row["expires_at"])
            for row in records
        )
        if not consent_ok:
            return False
        acceptance_ok = any(
            row.get("record_type") == "participant_acceptance"
            and row.get("installation_id") == installation["id"]
            and row.get("participant_id") == participant_id
            and row.get("tenant_id") == tenant_id
            and row.get("plan_version_id") == installation["plan_version_id"]
            and row.get("equipment_manifest_version_id")
            == installation["equipment_manifest_version_id"]
            and row.get("withdrawn_at") is None
            and _time(row["accepted_at"]) <= case["now"]
            for row in records
        )
        if not acceptance_ok:
            return False
    equipment_ok = any(
        row.get("record_type") == "equipment"
        and row.get("installation_id") == installation["id"]
        and row.get("tenant_id") == tenant_id
        and row.get("manifest_version_id") == installation["equipment_manifest_version_id"]
        and row.get("review_status") == "reviewed"
        and _time(row["reviewed_at"]) <= case["now"] < _time(row["expires_at"])
        and any(
            member.get("record_type") == "membership"
            and member.get("installation_id") == installation["id"]
            and member.get("participant_id") == row.get("reviewed_by")
            and member.get("tenant_id") == tenant_id
            and member.get("active") is True
            and member.get("role")
            in {"safety_reviewer", "accessibility_lead", "tenant_admin"}
            and (
                member.get("valid_until") is None
                or _time(member["valid_until"]) > case["now"]
            )
            for member in records
        )
        for row in records
    )
    if not equipment_ok:
        return False
    for required in installation["required_check_types"]:
        check_ok = any(
            row.get("record_type") == "installation_check"
            and row.get("installation_id") == installation["id"]
            and row.get("tenant_id") == tenant_id
            and row.get("check_type") == required
            and row.get("status") == "passed"
            and row.get("configuration_version") == installation["configuration_version"]
            and _time(row["completed_at"]) <= case["now"] < _time(row["expires_at"])
            and any(
                member.get("record_type") == "membership"
                and member.get("installation_id") == installation["id"]
                and member.get("participant_id") == row.get("reviewed_by")
                and member.get("tenant_id") == tenant_id
                and member.get("active") is True
                and member.get("role")
                in {"safety_reviewer", "accessibility_lead", "tenant_admin"}
                and (
                    member.get("valid_until") is None
                    or _time(member["valid_until"]) > case["now"]
                )
                for member in records
            )
            for row in records
        )
        if not check_ok:
            return False
    return True


def weak_boolean_baseline(case: dict[str, Any]) -> tuple[bool, str]:
    """Deliberately weak comparator: ignores tenant, expiry, version, and review."""
    rows = case["records"]
    flags = {
        "installation": next(
            (row for row in rows if row.get("id") == case["installation_id"]), None
        ),
        "has_consent": any(row.get("record_type") == "consent" for row in rows),
        "has_acceptance": any(row.get("record_type") == "participant_acceptance" for row in rows),
        "has_check": any(row.get("record_type") == "installation_check" for row in rows),
        "has_equipment": any(row.get("record_type") == "equipment" for row in rows),
    }
    installation = flags["installation"]
    allowed = bool(
        installation
        and installation.get("status") in {"draft", "ready"}
        and not installation.get("stop_requested")
        and case["actor"].get("role") in {"facilitator", "tenant_admin"}
        and all(flags[key] for key in ("has_consent", "has_acceptance", "has_check", "has_equipment"))
    )
    return allowed, "WEAK_BOOLEAN_GATE_ALLOW" if allowed else "WEAK_BOOLEAN_GATE_DENY"


def _wilson(successes: int, total: int, z: float = 1.96) -> dict[str, float] | None:
    if not total:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total**2)) ** 0.5) / denominator
    return {"lower_95": max(0.0, center - margin), "upper_95": min(1.0, center + margin)}


def _latency(values: list[int]) -> dict[str, float]:
    return {
        "median_ns": statistics.median(values) if values else 0,
        "p95_ns": sorted(values)[min(len(values) - 1, int(0.95 * len(values)))] if values else 0,
    }


def _metrics(
    rows: list[dict[str, Any]], decision_field: str
) -> dict[str, Any]:
    false_allows = sum(
        not row["oracle_allowed"] and row[decision_field] for row in rows
    )
    false_denials = sum(
        row["oracle_allowed"] and not row[decision_field] for row in rows
    )
    oracle_denied = sum(not row["oracle_allowed"] for row in rows)
    oracle_allowed = sum(row["oracle_allowed"] for row in rows)
    strict = decision_field == "strict_allowed"
    return {
        "scenario_count": len(rows),
        "oracle_allowed_denominator": oracle_allowed,
        "oracle_denied_denominator": oracle_denied,
        "false_allows": false_allows,
        "false_allow_rate": false_allows / oracle_denied if oracle_denied else None,
        "false_allow_wilson_95": _wilson(false_allows, oracle_denied),
        "false_denials": false_denials,
        "false_denial_rate": false_denials / oracle_allowed if oracle_allowed else None,
        "valid_action_completion": (
            (oracle_allowed - false_denials) / oracle_allowed if oracle_allowed else None
        ),
        "reason_codes_observed": sorted({
            reason for row in rows if not row[decision_field]
            for reason in (
                row.get("strict_reason_codes", [])
                if strict else [row["weak_baseline_reason"]]
            )
        }),
        "latency": _latency([
            row["strict_latency_ns"] if strict else row["baseline_latency_ns"]
            for row in rows
        ]),
    }


def run_benchmark(
    seed: int = 17, held_out_seed: int = 2026, count: int = 120
) -> dict[str, Any]:
    if seed == held_out_seed:
        raise ValueError("development and held-out seeds must differ")
    if count < len(SCENARIO_CLASSES):
        raise ValueError(f"count must be at least {len(SCENARIO_CLASSES)} to cover every class")
    warmup = build_activation_case(seed, "valid")
    decide_activation(
        warmup["records"], warmup["installation_id"], warmup["actor"], warmup["now"]
    )
    weak_boolean_baseline(warmup)
    contract_oracle(warmup)
    outcomes: list[dict[str, Any]] = []
    class_results: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dataset_seed, held_out in ((seed, False), (held_out_seed, True)):
        order = list(SCENARIO_CLASSES)
        random.Random(dataset_seed).shuffle(order)
        for index in range(count):
            scenario_class = order[index % len(order)]
            case_seed = dataset_seed * 1_000_000 + index
            case = build_activation_case(case_seed, scenario_class)
            started = time.perf_counter_ns()
            strict = decide_activation(
                case["records"], case["installation_id"], case["actor"], case["now"]
            )
            strict_latency = time.perf_counter_ns() - started
            started = time.perf_counter_ns()
            baseline_allowed, baseline_reason = weak_boolean_baseline(case)
            baseline_latency = time.perf_counter_ns() - started
            oracle_allowed = contract_oracle(case)
            result = {
                "seed": dataset_seed,
                "case_seed": case_seed,
                "held_out": held_out,
                "case_id": case["case_id"],
                "scenario_class": scenario_class,
                "policy_input": {
                    "installation_id": case["installation_id"],
                    "actor": case["actor"],
                    "now": case["now"].isoformat(),
                },
                "oracle_allowed": oracle_allowed,
                "strict_allowed": strict.allowed,
                "strict_reason_codes": list(strict.reason_codes),
                "weak_baseline_allowed": baseline_allowed,
                "weak_baseline_reason": baseline_reason,
                "strict_latency_ns": strict_latency,
                "baseline_latency_ns": baseline_latency,
                "records": case["records"],
            }
            outcomes.append(result)
            class_results[scenario_class].append(result)
    summary: dict[str, Any] = {}
    for label, decision_field in (
        ("strict", "strict_allowed"), ("weak_boolean_baseline", "weak_baseline_allowed")
    ):
        summary[label] = _metrics(outcomes, decision_field)
    summary["by_dataset"] = {
        dataset: {
            "scenario_count": sum(row["held_out"] is held_out for row in outcomes),
            "strict": _metrics(
                [row for row in outcomes if row["held_out"] is held_out], "strict_allowed"
            ),
            "weak_boolean_baseline": _metrics(
                [row for row in outcomes if row["held_out"] is held_out],
                "weak_baseline_allowed",
            ),
        }
        for dataset, held_out in (("development_seed", False), ("held_out_seed", True))
    }
    by_class = {}
    for scenario_class, rows in sorted(class_results.items()):
        by_class[scenario_class] = {
            "scenarios": len(rows),
            "oracle_denied": sum(not row["oracle_allowed"] for row in rows),
            "oracle_allowed": sum(row["oracle_allowed"] for row in rows),
            "strict_allows": sum(row["strict_allowed"] for row in rows),
            "baseline_allows": sum(row["weak_baseline_allowed"] for row in rows),
            "strict_false_allows": sum(
                not row["oracle_allowed"] and row["strict_allowed"] for row in rows
            ),
            "strict_false_denials": sum(
                row["oracle_allowed"] and not row["strict_allowed"] for row in rows
            ),
            "baseline_false_allows": sum(
                not row["oracle_allowed"] and row["weak_baseline_allowed"] for row in rows
            ),
            "baseline_false_denials": sum(
                row["oracle_allowed"] and not row["weak_baseline_allowed"] for row in rows
            ),
            "strict_reason_codes": sorted({
                reason for row in rows for reason in row["strict_reason_codes"]
            }),
        }
    schema_bytes = SCHEMA_PATH.read_bytes()
    config = {
        "seed": seed, "held_out_seed": held_out_seed, "count_per_seed": count,
        "scenario_classes": list(SCENARIO_CLASSES),
        "baseline": "deliberately weak boolean-gate comparator",
        "no_held_out_tuning": True,
        "warmup_calls_per_implementation": 1,
        "warmup_calls_per_implementation": 1,
    }
    config_sha = sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    try:
        code_revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT.parent, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT.parent, text=True
        ).strip())
        if dirty:
            code_revision += "-dirty"
        tracked_paths = subprocess.check_output(
            ["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT.parent, text=True
        ).splitlines()
    except (OSError, subprocess.CalledProcessError):
        code_revision = "unavailable"
        tracked_paths = []
        dirty = True
    worktree_hash = sha256()
    for relative_path in sorted(tracked_paths):
        path = ROOT.parent / relative_path
        if path.is_file():
            worktree_hash.update(relative_path.encode("utf-8"))
            worktree_hash.update(b"\0")
            worktree_hash.update(path.read_bytes())
            worktree_hash.update(b"\0")
    dependencies = []
    for package in ("jsonschema", "attrs", "pyrsistent"):
        try:
            dependencies.append(f"{package}=={importlib.metadata.version(package)}")
        except importlib.metadata.PackageNotFoundError:
            dependencies.append(f"{package}=unavailable")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest = {
        "schema_version": "0.1.0",
        "record_type": "evaluation_run_manifest",
        "id": str(uuid5(_NAMESPACE, f"run:{seed}:{held_out_seed}:{count}:{code_revision}")),
        "tenant_id": str(uuid5(_NAMESPACE, "benchmark-tenant")),
        "environment": "synthetic",
        "classification": "synthetic",
        "revision": 1,
        "created_at": now,
        "updated_at": now,
        "seed": seed,
        "config_sha256": config_sha,
        "code_revision": code_revision,
        "working_tree_sha256": worktree_hash.hexdigest(),
        "schema_sha256": sha256(schema_bytes).hexdigest(),
        "dependencies": dependencies,
        "run_command": " ".join(sys.argv),
        "runtime_metadata": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine() or "unknown",
            "processor": platform.processor() or "unknown",
            "cpu_count": str(os.cpu_count() or "unknown"),
        },
        "held_out": True,
    }
    Draft202012Validator(json.loads(schema_bytes), format_checker=FormatChecker()).validate(
        manifest
    )
    return {
        "label": "SYNTHETIC POLICY STRESS TEST — NOT DEPLOYMENT SAFETY EVIDENCE",
        "config": config,
        "manifest": manifest,
        "summary": summary,
        "per_class": by_class,
        "reason_code_coverage": {
            "strict_observed": len(set(summary["strict"]["reason_codes_observed"]) & _REASON_CATALOG),
            "strict_declared": len(_REASON_CATALOG),
            "strict_fraction": (
                len(set(summary["strict"]["reason_codes_observed"]) & _REASON_CATALOG)
                / len(_REASON_CATALOG)
            ),
            "strict_catalog": sorted(_REASON_CATALOG),
        },
        "correlation_note": (
            "Generated scenarios are deterministic policy cases, not independent human observations; "
            "Wilson intervals are descriptive scenario-level uncertainty only."
        ),
        "oracle_limitations": (
            "The oracle is separately implemented from the policy decision function but shares the "
            "v0.1.0 contract and its specification assumptions."
        ),
        "raw_outcomes": outcomes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--held-out-seed", type=int, default=2026)
    parser.add_argument("--count", type=int, default=120, help="scenarios per seed")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_benchmark(args.seed, args.held_out_seed, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    print(f"Raw outcomes and manifest: {args.output}")


if __name__ == "__main__":
    main()
