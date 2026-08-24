#!/usr/bin/env python3

"""
BIRTH_EDGE — RECONVERGENCE PHENOMENON DISCOVERY ENGINE V1

Purpose
-------
Discover the underlying structure of the MODEL / WISDOM / REALITY
system without assuming in advance what the phenomenon is.

This engine:
    - uses persisted historical reflections only
    - does not modify historical evidence
    - does not generate synthetic cases
    - does not trade
    - does not alter the model
    - separates observation from interpretation
    - identifies recurring path-specific structures

Primary discovery questions
----------------------------
1. Which path breaks when convergence is lost?
2. Which paths remain anchored to REALITY?
3. Does disagreement precede divergence?
4. Does confidence/evidence change before divergence?
5. Which divergence states recur?
6. Does one path specialize in reality alignment?
7. Does divergence persist?
8. Does divergence reconverge?
9. Do the same state transitions repeat?
10. Is there evidence of a stable structural pattern?

The engine intentionally does NOT declare a phenomenon from
a tiny sample. It reports:
    OBSERVED
    CANDIDATE
    REPEATING
    STRUCTURALLY_SUPPORTED
    NOT_IDENTIFIABLE

The classification is evidence-size aware.
"""

import json
import math
import os
import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Optional


REFLECTION_FILE = "data/ml_reflection.json"


class PhenomenonDiscovery:

    VERSION = 1

    PATHS = (
        "MODEL",
        "WISDOM",
    )

    def __init__(
        self,
        reflection_path: str = REFLECTION_FILE,
    ):
        self.reflection_path = reflection_path
        self.reflections = self._load_reflections(
            reflection_path
        )

        self.cases = [
            self._normalize_case(
                reflection,
                index,
            )
            for index, reflection
            in enumerate(self.reflections)
        ]

    # ============================================================
    # SAFE UTILITIES
    # ============================================================

    @staticmethod
    def _safe_float(
        value,
        default: float = 0.0,
    ) -> float:

        try:
            if value is None:
                return default

            result = float(value)

            if not math.isfinite(result):
                return default

            return result

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return default

    @staticmethod
    def _clip(
        value: float,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:

        return max(
            low,
            min(high, value),
        )

    @staticmethod
    def _mean(
        values: List[float],
    ) -> float:

        if not values:
            return 0.0

        return statistics.fmean(values)

    # ============================================================
    # LOAD
    # ============================================================

    @staticmethod
    def _load_reflections(
        path: str,
    ) -> List[dict]:

        path = os.path.abspath(path)

        if not os.path.exists(path):
            return []

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as handle:

                payload = json.load(handle)

            if isinstance(payload, dict):
                payload = payload.get(
                    "reflections",
                    [],
                )

            if not isinstance(payload, list):
                return []

            return [
                item
                for item in payload
                if isinstance(item, dict)
            ]

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            return []

    # ============================================================
    # NORMALIZATION
    # ============================================================

    def _normalize_case(
        self,
        reflection: dict,
        index: int,
    ) -> dict:

        probability = self._safe_float(
            reflection.get(
                "probability"
            ),
            0.5,
        )

        wisdom_score = self._clip(
            self._safe_float(
                reflection.get(
                    "wisdom_score"
                ),
                0.5,
            )
        )

        actual_raw = self._safe_float(
            reflection.get(
                "actual_outcome"
            ),
            0.0,
        )

        model = (
            1
            if probability >= 0.5
            else 0
        )

        wisdom = (
            1
            if wisdom_score >= 0.5
            else 0
        )

        reality = (
            1
            if actual_raw >= 0.5
            else 0
        )

        model_reality = (
            model == reality
        )

        wisdom_reality = (
            wisdom == reality
        )

        model_wisdom = (
            model == wisdom
        )

        three_way = (
            model == wisdom == reality
        )

        if three_way:

            state = "FULL_CONVERGENCE"

        elif model_reality and not wisdom_reality:

            state = "WISDOM_DIVERGENCE"

        elif wisdom_reality and not model_reality:

            state = "MODEL_DIVERGENCE"

        elif model_wisdom and not model_reality:

            state = "SHARED_REALITY_FAILURE"

        else:

            state = "MULTI_PATH_DIVERGENCE"

        if model_reality and not wisdom_reality:

            broken_paths = [
                "WISDOM"
            ]

        elif wisdom_reality and not model_reality:

            broken_paths = [
                "MODEL"
            ]

        elif three_way:

            broken_paths = []

        else:

            broken_paths = []

            if not model_reality:
                broken_paths.append(
                    "MODEL"
                )

            if not wisdom_reality:
                broken_paths.append(
                    "WISDOM"
                )

        case_id = (
            reflection.get("id")
            or reflection.get("case_id")
            or reflection.get("event_id")
            or f"reflection_{index + 1}"
        )

        return {
            "index": index,
            "case_id": case_id,

            "model": model,
            "wisdom": wisdom,
            "reality": reality,

            "model_reality": model_reality,
            "wisdom_reality": wisdom_reality,
            "model_wisdom": model_wisdom,
            "three_way": three_way,

            "state": state,
            "broken_paths": broken_paths,

            "probability": probability,
            "wisdom_score": wisdom_score,

            "confidence": self._clip(
                self._safe_float(
                    reflection.get(
                        "model_confidence"
                    ),
                    0.0,
                )
            ),

            "evidence_agreement": self._clip(
                self._safe_float(
                    reflection.get(
                        "evidence_agreement"
                    ),
                    0.0,
                )
            ),

            "evidence_strength": self._clip(
                self._safe_float(
                    reflection.get(
                        "evidence_strength"
                    ),
                    0.0,
                )
            ),

            "prediction_error": self._clip(
                self._safe_float(
                    reflection.get(
                        "prediction_error"
                    ),
                    abs(
                        probability
                        - reality
                    ),
                )
            ),

            "reflection_score": self._clip(
                self._safe_float(
                    reflection.get(
                        "reflection_score"
                    ),
                    0.0,
                )
            ),
        }

    # ============================================================
    # BASIC STRUCTURE
    # ============================================================

    def basic_structure(self) -> Dict[str, object]:

        total = len(self.cases)

        if total == 0:

            return {
                "test": "BASIC_STRUCTURE",
                "status": "NO_EXPERIENCE",
                "cases": 0,
            }

        states = Counter(
            case["state"]
            for case in self.cases
        )

        return {
            "test": "BASIC_STRUCTURE",
            "cases": total,
            "states": dict(states),

            "full_convergence_rate":
                self._mean([
                    float(
                        case["three_way"]
                    )
                    for case in self.cases
                ]),

            "model_reality_rate":
                self._mean([
                    float(
                        case["model_reality"]
                    )
                    for case in self.cases
                ]),

            "wisdom_reality_rate":
                self._mean([
                    float(
                        case["wisdom_reality"]
                    )
                    for case in self.cases
                ]),

            "model_wisdom_rate":
                self._mean([
                    float(
                        case["model_wisdom"]
                    )
                    for case in self.cases
                ]),
        }

    # ============================================================
    # PATH SPECIALIZATION
    # ============================================================

    def path_specialization(self) -> Dict[str, object]:

        model_correct = [
            case
            for case in self.cases
            if case["model_reality"]
        ]

        wisdom_correct = [
            case
            for case in self.cases
            if case["wisdom_reality"]
        ]

        model_only = [
            case
            for case in self.cases
            if (
                case["model_reality"]
                and not case["wisdom_reality"]
            )
        ]

        wisdom_only = [
            case
            for case in self.cases
            if (
                case["wisdom_reality"]
                and not case["model_reality"]
            )
        ]

        both = [
            case
            for case in self.cases
            if (
                case["model_reality"]
                and case["wisdom_reality"]
            )
        ]

        neither = [
            case
            for case in self.cases
            if (
                not case["model_reality"]
                and not case["wisdom_reality"]
            )
        ]

        total = len(self.cases)

        return {
            "test": "PATH_SPECIALIZATION",

            "model_correct": len(
                model_correct
            ),

            "wisdom_correct": len(
                wisdom_correct
            ),

            "model_only": len(
                model_only
            ),

            "wisdom_only": len(
                wisdom_only
            ),

            "both_correct": len(
                both
            ),

            "both_wrong": len(
                neither
            ),

            "model_only_rate":
                len(model_only) / total
                if total else 0.0,

            "wisdom_only_rate":
                len(wisdom_only) / total
                if total else 0.0,

            "model_cases": [
                case["case_id"]
                for case in model_only
            ],

            "wisdom_cases": [
                case["case_id"]
                for case in wisdom_only
            ],
        }

    # ============================================================
    # FIRST-BREAK DETECTION
    # ============================================================

    def first_break_analysis(self) -> Dict[str, object]:

        counts = Counter()

        for case in self.cases:

            if case["three_way"]:
                counts["NONE"] += 1
                continue

            if (
                case["model_reality"]
                and not case["wisdom_reality"]
            ):
                counts["WISDOM"] += 1

            elif (
                case["wisdom_reality"]
                and not case["model_reality"]
            ):
                counts["MODEL"] += 1

            elif (
                not case["model_reality"]
                and not case["wisdom_reality"]
            ):
                counts["MULTIPLE"] += 1

        total_failures = (
            sum(counts.values())
            - counts["NONE"]
        )

        return {
            "test": "FIRST_BREAK",
            "counts": dict(counts),
            "failure_cases": total_failures,

            "dominant_break_path":
                (
                    max(
                        (
                            "MODEL",
                            "WISDOM",
                            "MULTIPLE",
                        ),
                        key=lambda key:
                            counts[key],
                    )
                    if total_failures
                    else "NONE"
                ),
        }

    # ============================================================
    # DIRECTIONAL SIGNATURES
    # ============================================================

    def directional_signatures(self) -> Dict[str, object]:

        signatures = Counter()

        for case in self.cases:

            signature = (
                f"M{case['model']}"
                f"W{case['wisdom']}"
                f"R{case['reality']}"
            )

            signatures[signature] += 1

        return {
            "test": "DIRECTIONAL_SIGNATURES",
            "signatures": dict(signatures),
            "unique_signatures":
                len(signatures),
            "total_cases":
                len(self.cases),
        }

    # ============================================================
    # STATE TRANSITIONS
    # ============================================================

    def state_transitions(self) -> Dict[str, object]:

        transitions = Counter()

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            transition = (
                f"{previous['state']}"
                f" -> "
                f"{current['state']}"
            )

            transitions[transition] += 1

        return {
            "test": "STATE_TRANSITIONS",
            "transition_count":
                len(self.cases) - 1
                if self.cases
                else 0,
            "unique_transitions":
                len(transitions),
            "transitions":
                dict(transitions),
        }

    # ============================================================
    # PATH TRANSITIONS
    # ============================================================

    def path_transitions(self) -> Dict[str, object]:

        transitions = Counter()

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            previous_signature = (
                f"M{previous['model']}"
                f"W{previous['wisdom']}"
                f"R{previous['reality']}"
            )

            current_signature = (
                f"M{current['model']}"
                f"W{current['wisdom']}"
                f"R{current['reality']}"
            )

            transitions[
                f"{previous_signature}"
                f" -> "
                f"{current_signature}"
            ] += 1

        return {
            "test": "PATH_TRANSITIONS",
            "transitions":
                dict(transitions),
        }

    # ============================================================
    # PRECURSOR ANALYSIS
    # ============================================================

    def precursor_analysis(self) -> Dict[str, object]:

        if len(self.cases) < 2:

            return {
                "test": "PRECURSOR_ANALYSIS",
                "status": "INSUFFICIENT_HISTORY",
            }

        divergence_cases = []
        convergence_cases = []

        for index in range(1, len(self.cases)):

            previous = self.cases[
                index - 1
            ]

            current = self.cases[
                index
            ]

            if current["three_way"]:

                continue

            current_divergent = True

            previous_divergent = (
                not previous["three_way"]
            )

            if previous_divergent:

                divergence_cases.append(
                    (
                        previous,
                        current,
                    )
                )

            else:

                convergence_cases.append(
                    (
                        previous,
                        current,
                    )
                )

        def means(
            pairs,
        ):

            if not pairs:
                return {}

            previous = [
                pair[0]
                for pair in pairs
            ]

            current = [
                pair[1]
                for pair in pairs
            ]

            return {
                "previous_confidence":
                    self._mean([
                        case["confidence"]
                        for case in previous
                    ]),

                "current_confidence":
                    self._mean([
                        case["confidence"]
                        for case in current
                    ]),

                "previous_evidence_agreement":
                    self._mean([
                        case[
                            "evidence_agreement"
                        ]
                        for case in previous
                    ]),

                "current_evidence_agreement":
                    self._mean([
                        case[
                            "evidence_agreement"
                        ]
                        for case in current
                    ]),

                "previous_evidence_strength":
                    self._mean([
                        case[
                            "evidence_strength"
                        ]
                        for case in previous
                    ]),

                "current_evidence_strength":
                    self._mean([
                        case[
                            "evidence_strength"
                        ]
                        for case in current
                    ]),
            }

        return {
            "test": "PRECURSOR_ANALYSIS",

            "new_divergence_events":
                len(convergence_cases),

            "persistent_divergence_events":
                len(divergence_cases),

            "new_divergence_context":
                means(
                    convergence_cases
                ),

            "persistent_divergence_context":
                means(
                    divergence_cases
                ),
        }

    # ============================================================
    # DIVERGENCE → RECONVERGENCE
    # ============================================================

    def reconvergence_analysis(self) -> Dict[str, object]:

        divergence_to_convergence = 0
        divergence_to_divergence = 0

        transitions = []

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            previous_divergent = (
                not previous["three_way"]
            )

            current_convergent = (
                current["three_way"]
            )

            if previous_divergent:

                if current_convergent:

                    divergence_to_convergence += 1

                    transitions.append({
                        "from":
                            previous["case_id"],
                        "to":
                            current["case_id"],
                        "event":
                            "RECONVERGENCE",
                    })

                else:

                    divergence_to_divergence += 1

        denominator = (
            divergence_to_convergence
            + divergence_to_divergence
        )

        return {
            "test":
                "DIVERGENCE_RECONVERGENCE",

            "divergence_to_convergence":
                divergence_to_convergence,

            "divergence_to_divergence":
                divergence_to_divergence,

            "reconvergence_rate":
                (
                    divergence_to_convergence
                    / denominator
                    if denominator
                    else 0.0
                ),

            "events":
                transitions,
        }

    # ============================================================
    # PERSISTENCE
    # ============================================================

    def persistence_analysis(self) -> Dict[str, object]:

        convergence_following_convergence = 0
        divergence_following_divergence = 0

        convergence_transitions = 0
        divergence_transitions = 0

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            if previous["three_way"]:

                convergence_transitions += 1

                if current["three_way"]:
                    convergence_following_convergence += 1

            else:

                divergence_transitions += 1

                if not current["three_way"]:
                    divergence_following_divergence += 1

        return {
            "test":
                "STATE_PERSISTENCE",

            "convergence_following_convergence":
                convergence_following_convergence,

            "convergence_transition_count":
                convergence_transitions,

            "convergence_persistence_rate":
                (
                    convergence_following_convergence
                    / convergence_transitions
                    if convergence_transitions
                    else 0.0
                ),

            "divergence_following_divergence":
                divergence_following_divergence,

            "divergence_transition_count":
                divergence_transitions,

            "divergence_persistence_rate":
                (
                    divergence_following_divergence
                    / divergence_transitions
                    if divergence_transitions
                    else 0.0
                ),
        }

    # ============================================================
    # EVIDENCE CONDITIONING
    # ============================================================

    def evidence_conditioning(self) -> Dict[str, object]:

        if not self.cases:

            return {
                "test":
                    "EVIDENCE_CONDITIONING",
                "status":
                    "NO_EXPERIENCE",
            }

        agreement_values = [
            case["evidence_agreement"]
            for case in self.cases
        ]

        strength_values = [
            case["evidence_strength"]
            for case in self.cases
        ]

        agreement_midpoint = (
            statistics.median(
                agreement_values
            )
        )

        strength_midpoint = (
            statistics.median(
                strength_values
            )
        )

        high_agreement = [
            case
            for case in self.cases
            if (
                case[
                    "evidence_agreement"
                ]
                >= agreement_midpoint
            )
        ]

        low_agreement = [
            case
            for case in self.cases
            if (
                case[
                    "evidence_agreement"
                ]
                < agreement_midpoint
            )
        ]

        strong = [
            case
            for case in self.cases
            if (
                case[
                    "evidence_strength"
                ]
                >= strength_midpoint
            )
        ]

        weak = [
            case
            for case in self.cases
            if (
                case[
                    "evidence_strength"
                ]
                < strength_midpoint
            )
        ]

        def convergence_rate(
            cases,
        ):

            return self._mean([
                float(
                    case["three_way"]
                )
                for case in cases
            ])

        return {
            "test":
                "EVIDENCE_CONDITIONING",

            "agreement_median":
                agreement_midpoint,

            "strength_median":
                strength_midpoint,

            "high_agreement_cases":
                len(high_agreement),

            "low_agreement_cases":
                len(low_agreement),

            "high_agreement_convergence":
                convergence_rate(
                    high_agreement
                ),

            "low_agreement_convergence":
                convergence_rate(
                    low_agreement
                ),

            "strong_evidence_cases":
                len(strong),

            "weak_evidence_cases":
                len(weak),

            "strong_evidence_convergence":
                convergence_rate(
                    strong
                ),

            "weak_evidence_convergence":
                convergence_rate(
                    weak
                ),
        }

    # ============================================================
    # CONFIDENCE CONDITIONING
    # ============================================================

    def confidence_conditioning(self) -> Dict[str, object]:

        if not self.cases:

            return {
                "test":
                    "CONFIDENCE_CONDITIONING",
                "status":
                    "NO_EXPERIENCE",
            }

        median = statistics.median([
            case["confidence"]
            for case in self.cases
        ])

        high = [
            case
            for case in self.cases
            if case["confidence"] >= median
        ]

        low = [
            case
            for case in self.cases
            if case["confidence"] < median
        ]

        def rate(
            cases,
        ):

            return self._mean([
                float(
                    case["three_way"]
                )
                for case in cases
            ])

        return {
            "test":
                "CONFIDENCE_CONDITIONING",

            "confidence_median":
                median,

            "high_confidence_cases":
                len(high),

            "low_confidence_cases":
                len(low),

            "high_confidence_convergence":
                rate(high),

            "low_confidence_convergence":
                rate(low),
        }

    # ============================================================
    # PATH STATE MAP
    # ============================================================

    def path_state_map(self) -> Dict[str, object]:

        map_data = []

        for case in self.cases:

            map_data.append({
                "case_id":
                    case["case_id"],

                "index":
                    case["index"],

                "MODEL":
                    case["model"],

                "WISDOM":
                    case["wisdom"],

                "REALITY":
                    case["reality"],

                "model_reality":
                    case["model_reality"],

                "wisdom_reality":
                    case["wisdom_reality"],

                "three_way":
                    case["three_way"],

                "state":
                    case["state"],

                "broken_paths":
                    case["broken_paths"],
            })

        return {
            "test":
                "PATH_STATE_MAP",

            "cases":
                map_data,
        }

    # ============================================================
    # CANDIDATE PATTERN DETECTOR
    # ============================================================

    def candidate_patterns(self) -> Dict[str, object]:

        total = len(self.cases)

        if total == 0:

            return {
                "test":
                    "CANDIDATE_PATTERNS",

                "classification":
                    "NOT_IDENTIFIABLE",

                "candidates": [],
            }

        candidates = []

        model_reality = sum(
            case["model_reality"]
            for case in self.cases
        )

        wisdom_reality = sum(
            case["wisdom_reality"]
            for case in self.cases
        )

        model_only = sum(
            (
                case["model_reality"]
                and not case["wisdom_reality"]
            )
            for case in self.cases
        )

        wisdom_only = sum(
            (
                case["wisdom_reality"]
                and not case["model_reality"]
            )
            for case in self.cases
        )

        # --------------------------------------------------------
        # MODEL REALITY ANCHOR
        # --------------------------------------------------------

        model_rate = (
            model_reality / total
        )

        wisdom_rate = (
            wisdom_reality / total
        )

        if (
            total >= 2
            and model_rate > wisdom_rate
        ):

            candidates.append({
                "name":
                    "MODEL_REALITY_ANCHOR",

                "description":
                    "MODEL remains reality-aligned "
                    "more frequently than WISDOM.",

                "support_cases":
                    model_reality,

                "rate":
                    model_rate,
            })

        # --------------------------------------------------------
        # WISDOM REALITY ANCHOR
        # --------------------------------------------------------

        if (
            total >= 2
            and wisdom_rate > model_rate
        ):

            candidates.append({
                "name":
                    "WISDOM_REALITY_ANCHOR",

                "description":
                    "WISDOM remains reality-aligned "
                    "more frequently than MODEL.",

                "support_cases":
                    wisdom_reality,

                "rate":
                    wisdom_rate,
            })

        # --------------------------------------------------------
        # MODEL-ONLY SPECIALIZATION
        # --------------------------------------------------------

        if model_only:

            candidates.append({
                "name":
                    "MODEL_ONLY_REALITY_SPECIALIZATION",

                "description":
                    "At least one case exists where "
                    "MODEL matches REALITY while "
                    "WISDOM does not.",

                "support_cases":
                    model_only,

                "rate":
                    model_only / total,
            })

        # --------------------------------------------------------
        # WISDOM-ONLY SPECIALIZATION
        # --------------------------------------------------------

        if wisdom_only:

            candidates.append({
                "name":
                    "WISDOM_ONLY_REALITY_SPECIALIZATION",

                "description":
                    "At least one case exists where "
                    "WISDOM matches REALITY while "
                    "MODEL does not.",

                "support_cases":
                    wisdom_only,

                "rate":
                    wisdom_only / total,
            })

        # --------------------------------------------------------
        # RECURRING STRUCTURE
        # --------------------------------------------------------

        states = Counter(
            case["state"]
            for case in self.cases
        )

        recurring_states = {
            state: count
            for state, count
            in states.items()
            if count >= 2
        }

        if recurring_states:

            candidates.append({
                "name":
                    "RECURRING_STATE_STRUCTURE",

                "description":
                    "At least one structural state "
                    "appears more than once.",

                "support_cases":
                    sum(
                        recurring_states.values()
                    ),

                "states":
                    recurring_states,
            })

        # --------------------------------------------------------
        # RECURRING TRANSITION
        # --------------------------------------------------------

        transitions = Counter()

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            transitions[
                (
                    previous["state"],
                    current["state"]
                )
            ] += 1

        recurring_transitions = {
            f"{a} -> {b}": count
            for (
                a,
                b
            ), count in transitions.items()
            if count >= 2
        }

        if recurring_transitions:

            candidates.append({
                "name":
                    "RECURRING_STATE_TRANSITION",

                "description":
                    "The same state transition "
                    "occurs multiple times.",

                "support_cases":
                    sum(
                        recurring_transitions.values()
                    ),

                "transitions":
                    recurring_transitions,
            })

        # --------------------------------------------------------
        # CLASSIFICATION
        # --------------------------------------------------------

        if not candidates:

            classification = (
                "NO_REPEATED_STRUCTURE"
            )

        elif total < 5:

            classification = (
                "CANDIDATE_PATTERN"
            )

        elif any(
            candidate["name"]
            == "RECURRING_STATE_TRANSITION"
            for candidate in candidates
        ):

            classification = (
                "REPEATING_STRUCTURAL_PATTERN"
            )

        else:

            classification = (
                "STRUCTURAL_PATTERN_OBSERVED"
            )

        return {
            "test":
                "CANDIDATE_PATTERNS",

            "classification":
                classification,

            "candidates":
                candidates,
        }

    # ============================================================
    # PHENOMENON HYPOTHESES
    # ============================================================

    def hypotheses(self) -> Dict[str, object]:

        patterns = (
            self.candidate_patterns()
        )

        hypotheses = []

        for candidate in patterns[
            "candidates"
        ]:

            name = candidate[
                "name"
            ]

            if name == (
                "MODEL_ONLY_REALITY_SPECIALIZATION"
            ):

                hypotheses.append({
                    "hypothesis":
                        "PATH-SPECIFIC REALITY ANCHORING",

                    "observation":
                        "MODEL has remained aligned "
                        "with REALITY in cases where "
                        "WISDOM diverged.",

                    "status":
                        "CANDIDATE",

                    "warning":
                        "Requires repeated independent "
                        "cases before generalization.",
                })

            elif name == (
                "WISDOM_ONLY_REALITY_SPECIALIZATION"
            ):

                hypotheses.append({
                    "hypothesis":
                        "WISDOM-SPECIFIC REALITY ANCHORING",

                    "observation":
                        "WISDOM has remained aligned "
                        "with REALITY in cases where "
                        "MODEL diverged.",

                    "status":
                        "CANDIDATE",

                    "warning":
                        "Requires repeated independent "
                        "cases before generalization.",
                })

            elif name == (
                "RECURRING_STATE_STRUCTURE"
            ):

                hypotheses.append({
                    "hypothesis":
                        "RECURRING CONVERGENCE STATE",

                    "observation":
                        "The same path relationship "
                        "state appears repeatedly.",

                    "status":
                        "CANDIDATE",
                })

            elif name == (
                "RECURRING_STATE_TRANSITION"
            ):

                hypotheses.append({
                    "hypothesis":
                        "RECURRING PATH TRANSITION",

                    "observation":
                        "The same path relationship "
                        "transition occurs repeatedly.",

                    "status":
                        "CANDIDATE",
                })

        return {
            "test":
                "PHENOMENON_HYPOTHESES",

            "hypotheses":
                hypotheses,
        }

    # ============================================================
    # PER-CASE DIAGNOSTICS
    # ============================================================

    def diagnostics(self) -> List[dict]:

        output = []

        for case in self.cases:

            if case["three_way"]:

                diagnostic = (
                    "FULL_CONVERGENCE"
                )

            elif (
                case["model_reality"]
                and not case["wisdom_reality"]
            ):

                diagnostic = (
                    "MODEL_CORRECT_WISDOM_WRONG"
                )

            elif (
                case["wisdom_reality"]
                and not case["model_reality"]
            ):

                diagnostic = (
                    "WISDOM_CORRECT_MODEL_WRONG"
                )

            else:

                diagnostic = (
                    "MULTI_PATH_REALITY_DIVERGENCE"
                )

            output.append({
                "index":
                    case["index"],

                "case_id":
                    case["case_id"],

                "model":
                    case["model"],

                "wisdom":
                    case["wisdom"],

                "reality":
                    case["reality"],

                "state":
                    case["state"],

                "diagnostic":
                    diagnostic,

                "broken_paths":
                    case["broken_paths"],
            })

        return output

    # ============================================================
    # DISCOVERY VERDICT
    # ============================================================

    def discovery_verdict(self) -> Dict[str, object]:

        total = len(self.cases)

        if total == 0:

            return {
                "classification":
                    "NO_DATA",

                "confidence":
                    "NONE",

                "reason":
                    "No persisted reflections "
                    "were available.",
            }

        if total < 3:

            return {
                "classification":
                    "PHENOMENON_NOT_YET_IDENTIFIABLE",

                "confidence":
                    "LOW",

                "reason":
                    "The current historical record "
                    "contains fewer than three cases. "
                    "Observed structure is reported, "
                    "but recurrence cannot yet be established.",
            }

        if total < 5:

            return {
                "classification":
                    "CANDIDATE_PHENOMENON",

                "confidence":
                    "LOW",

                "reason":
                    "A structural candidate exists, "
                    "but the historical sample remains small.",
            }

        patterns = (
            self.candidate_patterns()
        )

        if patterns[
            "classification"
        ] == "REPEATING_STRUCTURAL_PATTERN":

            return {
                "classification":
                    "REPEATING_STRUCTURAL_PHENOMENON",

                "confidence":
                    "MODERATE",

                "reason":
                    "Repeated state or transition "
                    "structure has been observed.",
            }

        return {
            "classification":
                "STRUCTURAL_PATTERN_OBSERVED",

            "confidence":
                "LOW_TO_MODERATE",

            "reason":
                "Multiple cases exist and a "
                "structural relationship has been observed, "
                "but further validation is required.",
        }

    # ============================================================
    # FULL REPORT
    # ============================================================

    def report(self) -> Dict[str, object]:

        return {
            "engine":
                "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_DISCOVERY",

            "version":
                self.VERSION,

            "data_source":
                os.path.abspath(
                    self.reflection_path
                ),

            "data_integrity": {
                "historical_records":
                    len(self.reflections),

                "analyzed_cases":
                    len(self.cases),

                "historical_data_modified":
                    False,

                "synthetic_data_used":
                    False,

                "model_modified":
                    False,

                "trading_performed":
                    False,
            },

            "basic_structure":
                self.basic_structure(),

            "directional_signatures":
                self.directional_signatures(),

            "path_specialization":
                self.path_specialization(),

            "first_break":
                self.first_break_analysis(),

            "state_transitions":
                self.state_transitions(),

            "path_transitions":
                self.path_transitions(),

            "precursor_analysis":
                self.precursor_analysis(),

            "reconvergence":
                self.reconvergence_analysis(),

            "persistence":
                self.persistence_analysis(),

            "evidence_conditioning":
                self.evidence_conditioning(),

            "confidence_conditioning":
                self.confidence_conditioning(),

            "path_state_map":
                self.path_state_map(),

            "candidate_patterns":
                self.candidate_patterns(),

            "hypotheses":
                self.hypotheses(),

            "case_diagnostics":
                self.diagnostics(),

            "phenomenon":
                self.discovery_verdict(),
        }


# ================================================================
# CLI
# ================================================================

def main():

    print("=" * 76)
    print(
        "BIRTH_EDGE RECONVERGENCE "
        "PHENOMENON DISCOVERY V1"
    )
    print(
        "SEARCHING FOR UNDERLYING STRUCTURE"
    )
    print("=" * 76)

    engine = PhenomenonDiscovery()

    report = engine.report()

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    print()
    print("=" * 76)
    print("PHENOMENON DISCOVERY VERDICT")
    print("=" * 76)

    phenomenon = report[
        "phenomenon"
    ]

    print(
        "CLASSIFICATION:",
        phenomenon[
            "classification"
        ],
    )

    print(
        "CONFIDENCE:",
        phenomenon[
            "confidence"
        ],
    )

    print(
        "REASON:",
        phenomenon[
            "reason"
        ],
    )

    print()
    print("=" * 76)
    print("PATH SPECIALIZATION")
    print("=" * 76)

    specialization = report[
        "path_specialization"
    ]

    print(
        "MODEL CORRECT:",
        specialization[
            "model_correct"
        ],
    )

    print(
        "WISDOM CORRECT:",
        specialization[
            "wisdom_correct"
        ],
    )

    print(
        "MODEL-ONLY:",
        specialization[
            "model_only"
        ],
    )

    print(
        "WISDOM-ONLY:",
        specialization[
            "wisdom_only"
        ],
    )

    print()
    print("=" * 76)
    print("FIRST BREAK")
    print("=" * 76)

    first_break = report[
        "first_break"
    ]

    print(
        "DOMINANT BREAK PATH:",
        first_break[
            "dominant_break_path"
        ],
    )

    print(
        "BREAK COUNTS:",
        first_break[
            "counts"
        ],
    )

    print()
    print("=" * 76)
    print("CANDIDATE PATTERNS")
    print("=" * 76)

    patterns = report[
        "candidate_patterns"
    ]

    print(
        "CLASSIFICATION:",
        patterns[
            "classification"
        ],
    )

    for candidate in patterns[
        "candidates"
    ]:

        print()
        print(
            "PATTERN:",
            candidate[
                "name"
            ],
        )

        print(
            "DESCRIPTION:",
            candidate[
                "description"
            ],
        )

        print(
            "SUPPORT:",
            candidate.get(
                "support_cases",
                0,
            ),
        )

    print()
    print("=" * 76)
    print("PHENOMENON HYPOTHESES")
    print("=" * 76)

    hypotheses = report[
        "hypotheses"
    ][
        "hypotheses"
    ]

    if not hypotheses:

        print(
            "No candidate hypotheses yet."
        )

    else:

        for item in hypotheses:

            print()
            print(
                "HYPOTHESIS:",
                item[
                    "hypothesis"
                ],
            )

            print(
                "OBSERVATION:",
                item[
                    "observation"
                ],
            )

            print(
                "STATUS:",
                item[
                    "status"
                ],
            )

            if "warning" in item:

                print(
                    "WARNING:",
                    item[
                        "warning"
                    ],
                )

    print()
    print("=" * 76)
    print("PER-CASE DIAGNOSTICS")
    print("=" * 76)

    for case in report[
        "case_diagnostics"
    ]:

        print()
        print(
            f"CASE {case['index'] + 1}: "
            f"{case['case_id']}"
        )

        print(
            "  MODEL:",
            case["model"],
        )

        print(
            "  WISDOM:",
            case["wisdom"],
        )

        print(
            "  REALITY:",
            case["reality"],
        )

        print(
            "  STATE:",
            case["state"],
        )

        print(
            "  DIAGNOSTIC:",
            case["diagnostic"],
        )

        print(
            "  BROKEN PATHS:",
            case["broken_paths"],
        )

    print()
    print("=" * 76)
    print("DATA INTEGRITY")
    print("=" * 76)

    integrity = report[
        "data_integrity"
    ]

    print(
        "HISTORICAL RECORDS:",
        integrity[
            "historical_records"
        ],
    )

    print(
        "ANALYZED CASES:",
        integrity[
            "analyzed_cases"
        ],
    )

    print(
        "HISTORICAL DATA MODIFIED:",
        integrity[
            "historical_data_modified"
        ],
    )

    print(
        "SYNTHETIC DATA USED:",
        integrity[
            "synthetic_data_used"
        ],
    )

    print(
        "MODEL MODIFIED:",
        integrity[
            "model_modified"
        ],
    )

    print(
        "TRADING PERFORMED:",
        integrity[
            "trading_performed"
        ],
    )

    print()
    print("=" * 76)
    print("GAUNTLET COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
