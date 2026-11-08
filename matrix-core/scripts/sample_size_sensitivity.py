#!/usr/bin/env python3
"""Planning-only sensitivity grid for estimating one binary feasibility proportion."""

import argparse
import json
import math


def sample_size(p: float, half_width: float, z: float) -> int:
    if not 0 < p < 1:
        raise ValueError("p must be strictly between zero and one")
    if not 0 < half_width < 1:
        raise ValueError("half_width must be strictly between zero and one")
    if z <= 0:
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
    args = parser.parse_args()
    assumptions = [
        {"assumed_p": p, "target_half_width": width, "z": args.z,
         "independent_observations_needed": sample_size(p, width, args.z)}
        for p in map(float, args.p.split(","))
        for width in map(float, args.half_width.split(","))
    ]
    print(json.dumps({
        "label": "PLANNING SENSITIVITY ONLY — NOT POWER, EVIDENCE, OR A RECRUITMENT TARGET",
        "method": "normal-approximation precision for one binary proportion; no clustering adjustment",
        "assumptions": assumptions,
        "limitations": [
            "Choose assumptions with reviewers before any human research.",
            "The formula assumes independent observations; repeated tasks or sites require a design effect.",
            "No feasibility outcome, power, or validated effect is asserted.",
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
