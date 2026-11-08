#!/usr/bin/env python3
"""Planning-only sensitivity grid for estimating one binary feasibility proportion."""

import argparse
import json
import math


def sample_size(p: float, half_width: float, z: float) -> int:
    if not math.isfinite(p) or not 0 < p < 1:
        raise ValueError("p must be strictly between zero and one")
    if not math.isfinite(half_width) or not 0 < half_width < 1:
        raise ValueError("half_width must be strictly between zero and one")
    if not math.isfinite(z) or z <= 0:
        raise ValueError("z must be positive")
    return math.ceil(z * z * p * (1 - p) / (half_width * half_width))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p", default="0.2,0.5,0.8", help="assumed proportions")
    parser.add_argument(
        "--half-width", default="0.10,0.15,0.20",
        help="target normal-approximation confidence-interval half-widths",
    )
    parser.add_argument("--z", type=float, default=1.96, help="normal critical value")
    parser.add_argument(
        "--cluster-size", type=int, default=3,
        help="assumed average repeated observations per participant/site cluster",
    )
    parser.add_argument(
        "--icc", default="0,0.1,0.3",
        help="assumed intracluster correlations for design-effect sensitivity",
    )
    args = parser.parse_args()
    if args.cluster_size < 1:
        parser.error("--cluster-size must be at least one")
    iccs = [float(value) for value in args.icc.split(",")]
    if any(not math.isfinite(icc) or not 0 <= icc <= 1 for icc in iccs):
        parser.error("--icc values must be finite and between zero and one")
    assumptions = [
        {"assumed_p": p, "target_half_width": width, "z": args.z,
         "independent_observations_needed": sample_size(p, width, args.z),
         "assumed_cluster_size": args.cluster_size, "assumed_icc": icc,
         "design_effect": round(1 + (args.cluster_size - 1) * icc, 6),
         "cluster_adjusted_observations_sensitivity": math.ceil(
             sample_size(p, width, args.z)
             * (1 + (args.cluster_size - 1) * icc)
         )}
        for p in map(float, args.p.split(","))
        for width in map(float, args.half_width.split(","))
        for icc in iccs
    ]
    print(json.dumps({
        "label": "PLANNING SENSITIVITY ONLY — NOT POWER, EVIDENCE, OR A RECRUITMENT TARGET",
        "method": (
            "normal-approximation precision for one binary proportion, multiplied by "
            "1 + (cluster_size - 1) * ICC as a planning sensitivity only"
        ),
        "assumptions": assumptions,
        "limitations": [
            "Choose assumptions with reviewers before any human research.",
            "Cluster-size and ICC values are analyst-selected scenarios, not measured properties.",
            "The design-effect multiplication is approximate and does not provide power or design validation.",
            "No feasibility outcome, power, or validated effect is asserted.",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
