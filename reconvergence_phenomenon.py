#!/usr/bin/env python3
"""
BIRTH_EDGE RECONVERGENCE PHENOMENON GAUNTLET V1

Purpose
-------
Search persisted BIRTH_EDGE experience for an underlying phenomenon
behind MODEL / WISDOM / DISCERNMENT / REALITY reconvergence.

IMPORTANT
---------
This module:

    - does NOT generate synthetic evidence
    - does NOT alter historical outcomes
    - does NOT train or modify the existing model
    - does NOT perform trading
    - does NOT manufacture convergence
    - does NOT overwrite persisted data

It analyzes only the historical reflection records already present.

Primary research questions
---------------------------

1. Is reconvergence temporally structured?
2. Is disagreement itself informative?
3. Do MODEL and WISDOM specialize in different cases?
4. Does disagreement tend to precede convergence?
5. Does convergence persist?
6. Does divergence persist?
7. Does the system exhibit state-transition structure?
8. Does confidence behave differently during convergence/divergence?
9. Are there recurring failure patterns?
10. Does the observed sequence contain evidence of a latent state?
11. Is the observed structure stronger than simple marginal expectations?
12. Can the phenomenon be characterized without changing the evidence?

The analyzer intentionally distinguishes:

    OBSERVED
    EXPECTED
    DELTA

where possible.

No random/synthetic control observations are created.
"""

import json
import math
import os
import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


REFLECTION_FILE = "data/ml_reflection.json"

VERSION = 1


class PhenomenonGauntlet:

    def __init__(
        self,
        reflection_path: str = REFLECTION_FILE,
    ):
        self.reflection_path = reflection_path
        self.reflections = self._load_reflections(
            reflection_path
        )

        self.cases = [
            self._analyze_case(
                index,
                reflection,
            )
            for index, reflection
            in enumerate(self.reflections)
        ]

    # ============================================================
    # SAFE NUMERIC HANDLING
    # ============================================================

    @staticmethod
    def safe_float(
        value,
        default: float = 0.0,
    ) -> float:

        try:
            if value is None:
                return default

            value = float(value)

            if not math.isfinite(value):
                return default

            return value

        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            return default

    @staticmethod
    def clip(
        value: float,
        low: float = 0.0,
        high: float = 1.0,
    ) -> float:

        return max(
            low,
            min(high, value),
        )

    @staticmethod
    def mean(
        values: List[float],
    ) -> float:

        if not values:
            return 0.0

        return statistics.fmean(values)

    # ============================================================
    # PERSISTENCE
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
            TypeError,
            json.JSONDecodeError,
        ):
            return []

    # ============================================================
    # SINGLE CASE
    # ============================================================

    def _analyze_case(
        self,
        index: int,
        reflection: dict,
    ) -> dict:

        probability = self.safe_float(
            reflection.get(
                "probability"
            ),
            0.5,
        )

        actual_raw = self.safe_float(
            reflection.get(
                "actual_outcome"
            ),
            0.0,
        )

        actual = (
            1.0
            if actual_raw >= 0.5
            else 0.0
        )

        model = (
            1.0
            if probability >= 0.5
            else 0.0
        )

        wisdom_score = self.clip(
            self.safe_float(
                reflection.get(
                    "wisdom_score"
                ),
                0.5,
            )
        )

        wisdom = (
            1.0
            if wisdom_score >= 0.5
            else 0.0
        )

        evidence_agreement = self.clip(
            self.safe_float(
                reflection.get(
                    "evidence_agreement"
                ),
                0.0,
            )
        )

        evidence_strength = self.clip(
            self.safe_float(
                reflection.get(
                    "evidence_strength"
                ),
                0.0,
            )
        )

        confidence = self.clip(
            self.safe_float(
                reflection.get(
                    "model_confidence"
                ),
                0.0,
            )
        )

        confidence_alignment = self.clip(
            self.safe_float(
                reflection.get(
                    "confidence_alignment"
                ),
                0.0,
            )
        )

        prediction_error = self.clip(
            self.safe_float(
                reflection.get(
                    "prediction_error"
                ),
                abs(
                    probability - actual
                ),
            )
        )

        reflection_score = self.clip(
            self.safe_float(
                reflection.get(
                    "reflection_score"
                ),
                0.0,
            )
        )

        model_wisdom = (
            model == wisdom
        )

        model_reality = (
            model == actual
        )

        wisdom_reality = (
            wisdom == actual
        )

        three_way = (
            model
            == wisdom
            == actual
        )

        if three_way:
            state = "FULL_CONVERGENCE"

        elif (
            model_reality
            and not wisdom_reality
        ):
            state = "WISDOM_DIVERGENCE"

        elif (
            wisdom_reality
            and not model_reality
        ):
            state = "MODEL_DIVERGENCE"

        elif (
            model_wisdom
            and not model_reality
        ):
            state = "SHARED_WRONG"

        else:
            state = "MULTIPLE_DIVERGENCE"

        failures = []

        if not model_wisdom:
            failures.append(
                "MODEL_WISDOM"
            )

        if not model_reality:
            failures.append(
                "MODEL_REALITY"
            )

        if not wisdom_reality:
            failures.append(
                "WISDOM_REALITY"
            )

        if not failures:
            failure_class = "NO_FAILURE"

        elif len(failures) == 1:
            failure_class = failures[0]

        else:
            failure_class = "MULTIPLE_PATHS"

        case_id = (
            reflection.get("id")
            or reflection.get("case_id")
            or reflection.get("event_id")
            or f"reflection_{index + 1}"
        )

        return {
            "index": index,
            "case_id": str(case_id),

            "model": model,
            "wisdom": wisdom,
            "actual": actual,

            "model_wisdom": model_wisdom,
            "model_reality": model_reality,
            "wisdom_reality": wisdom_reality,
            "three_way": three_way,

            "state": state,

            "failures": failures,
            "failure_class": failure_class,

            "probability": probability,
            "wisdom_score": wisdom_score,

            "confidence": confidence,
            "confidence_alignment":
                confidence_alignment,

            "evidence_agreement":
                evidence_agreement,

            "evidence_strength":
                evidence_strength,

            "prediction_error":
                prediction_error,

            "reflection_score":
                reflection_score,
        }

    # ============================================================
    # BASIC SUMMARY
    # ============================================================

    def basic_summary(self) -> dict:

        n = len(self.cases)

        if n == 0:
            return {
                "status": "NO_EXPERIENCE",
                "cases": 0,
            }

        return {
            "status": "ANALYZABLE",
            "cases": n,

            "full_convergence":
                self._rate(
                    [
                        c["three_way"]
                        for c in self.cases
                    ]
                ),

            "model_reality":
                self._rate(
                    [
                        c["model_reality"]
                        for c in self.cases
                    ]
                ),

            "wisdom_reality":
                self._rate(
                    [
                        c["wisdom_reality"]
                        for c in self.cases
                    ]
                ),

            "model_wisdom":
                self._rate(
                    [
                        c["model_wisdom"]
                        for c in self.cases
                    ]
                ),

            "mean_prediction_error":
                self.mean(
                    [
                        c["prediction_error"]
                        for c in self.cases
                    ]
                ),

            "mean_confidence":
                self.mean(
                    [
                        c["confidence"]
                        for c in self.cases
                    ]
                ),

            "mean_evidence_strength":
                self.mean(
                    [
                        c["evidence_strength"]
                        for c in self.cases
                    ]
                ),
        }

    @staticmethod
    def _rate(
        values,
    ) -> float:

        if not values:
            return 0.0

        return sum(
            1
            for value in values
            if value
        ) / len(values)

    # ============================================================
    # TEST 1 — ERROR TOPOLOGY
    # ============================================================

    def error_topology(self) -> dict:

        counts = Counter(
            c["failure_class"]
            for c in self.cases
        )

        total = len(self.cases)

        return {
            "test":
                "ERROR_TOPOLOGY",

            "total_cases":
                total,

            "classes":
                dict(counts),

            "rates":
                {
                    key:
                    (
                        value / total
                        if total
                        else 0.0
                    )
                    for key, value
                    in counts.items()
                },
        }

    # ============================================================
    # TEST 2 — PATH SPECIALIZATION
    # ============================================================

    def path_specialization(self) -> dict:

        model_correct = [
            c
            for c in self.cases
            if c["model_reality"]
        ]

        wisdom_correct = [
            c
            for c in self.cases
            if c["wisdom_reality"]
        ]

        model_only = [
            c
            for c in self.cases
            if (
                c["model_reality"]
                and not c["wisdom_reality"]
            )
        ]

        wisdom_only = [
            c
            for c in self.cases
            if (
                c["wisdom_reality"]
                and not c["model_reality"]
            )
        ]

        both = [
            c
            for c in self.cases
            if (
                c["model_reality"]
                and c["wisdom_reality"]
            )
        ]

        neither = [
            c
            for c in self.cases
            if (
                not c["model_reality"]
                and not c["wisdom_reality"]
            )
        ]

        return {
            "test":
                "PATH_SPECIALIZATION",

            "model_only":
                len(model_only),

            "wisdom_only":
                len(wisdom_only),

            "both_correct":
                len(both),

            "both_wrong":
                len(neither),

            "model_correct_total":
                len(model_correct),

            "wisdom_correct_total":
                len(wisdom_correct),

            "model_only_rate":
                self._rate(
                    [
                        True
                        for _ in model_only
                    ]
                )
                if self.cases
                else 0.0,

            "wisdom_only_rate":
                self._rate(
                    [
                        True
                        for _ in wisdom_only
                    ]
                )
                if self.cases
                else 0.0,

            "model_correct_cases":
                [
                    c["case_id"]
                    for c in model_only
                ],

            "wisdom_correct_cases":
                [
                    c["case_id"]
                    for c in wisdom_only
                ],
        }

    # ============================================================
    # TEST 3 — DISAGREEMENT INFORMATION VALUE
    # ============================================================

    def disagreement_information(self) -> dict:

        agreement = [
            c
            for c in self.cases
            if c["model_wisdom"]
        ]

        disagreement = [
            c
            for c in self.cases
            if not c["model_wisdom"]
        ]

        def convergence_rate(
            group,
        ):
            return self._rate(
                [
                    c["three_way"]
                    for c in group
                ]
            )

        def reality_rate(
            group,
        ):
            return self._rate(
                [
                    c["model_reality"]
                    for c in group
                ]
            )

        agreement_convergence = (
            convergence_rate(
                agreement
            )
        )

        disagreement_convergence = (
            convergence_rate(
                disagreement
            )
        )

        agreement_reality = (
            reality_rate(
                agreement
            )
        )

        disagreement_reality = (
            reality_rate(
                disagreement
            )
        )

        return {
            "test":
                "DISAGREEMENT_INFORMATION",

            "agreement_cases":
                len(agreement),

            "disagreement_cases":
                len(disagreement),

            "agreement_convergence":
                agreement_convergence,

            "disagreement_convergence":
                disagreement_convergence,

            "convergence_delta":
                (
                    disagreement_convergence
                    - agreement_convergence
                ),

            "agreement_model_reality":
                agreement_reality,

            "disagreement_model_reality":
                disagreement_reality,

            "model_reality_delta":
                (
                    disagreement_reality
                    - agreement_reality
                ),

            "interpretation":
                self._interpret_delta(
                    disagreement_convergence
                    - agreement_convergence
                ),
        }

    @staticmethod
    def _interpret_delta(
        delta: float,
    ) -> str:

        if delta >= 0.10:
            return (
                "DISAGREEMENT_ASSOCIATED_WITH_HIGHER_"
                "CONVERGENCE"
            )

        if delta <= -0.10:
            return (
                "DISAGREEMENT_ASSOCIATED_WITH_LOWER_"
                "CONVERGENCE"
            )

        return (
            "NO_STRONG_OBSERVED_ASSOCIATION"
        )

    # ============================================================
    # TEST 4 — CONFIDENCE / REALITY
    # ============================================================

    def confidence_analysis(self) -> dict:

        convergent = [
            c
            for c in self.cases
            if c["three_way"]
        ]

        divergent = [
            c
            for c in self.cases
            if not c["three_way"]
        ]

        return {
            "test":
                "CONFIDENCE_REALITY",

            "convergent_cases":
                len(convergent),

            "divergent_cases":
                len(divergent),

            "convergent_mean_confidence":
                self.mean(
                    [
                        c["confidence"]
                        for c in convergent
                    ]
                ),

            "divergent_mean_confidence":
                self.mean(
                    [
                        c["confidence"]
                        for c in divergent
                    ]
                ),

            "convergent_mean_prediction_error":
                self.mean(
                    [
                        c["prediction_error"]
                        for c in convergent
                    ]
                ),

            "divergent_mean_prediction_error":
                self.mean(
                    [
                        c["prediction_error"]
                        for c in divergent
                    ]
                ),

            "confidence_alignment_convergent":
                self.mean(
                    [
                        c["confidence_alignment"]
                        for c in convergent
                    ]
                ),

            "confidence_alignment_divergent":
                self.mean(
                    [
                        c["confidence_alignment"]
                        for c in divergent
                    ]
                ),
        }

    # ============================================================
    # TEST 5 — TEMPORAL BLOCKS
    # ============================================================

    def temporal_blocks(
        self,
        blocks: int = 4,
    ) -> dict:

        n = len(self.cases)

        if n == 0:
            return {
                "test":
                    "TEMPORAL_BLOCKS",
                "status":
                    "NO_EXPERIENCE",
                "blocks": [],
            }

        blocks = max(
            1,
            min(
                int(blocks),
                n,
            ),
        )

        result = []

        base_size = n // blocks
        remainder = n % blocks

        start = 0

        for block_index in range(
            blocks
        ):

            size = (
                base_size
                + (
                    1
                    if block_index
                    < remainder
                    else 0
                )
            )

            end = start + size

            group = self.cases[
                start:end
            ]

            result.append(
                {
                    "block":
                        block_index + 1,

                    "start_case":
                        start + 1,

                    "end_case":
                        end,

                    "count":
                        len(group),

                    "three_way":
                        self._rate(
                            [
                                c["three_way"]
                                for c in group
                            ]
                        ),

                    "model_reality":
                        self._rate(
                            [
                                c["model_reality"]
                                for c in group
                            ]
                        ),

                    "wisdom_reality":
                        self._rate(
                            [
                                c["wisdom_reality"]
                                for c in group
                            ]
                        ),

                    "model_wisdom":
                        self._rate(
                            [
                                c["model_wisdom"]
                                for c in group
                            ]
                        ),

                    "prediction_error":
                        self.mean(
                            [
                                c["prediction_error"]
                                for c in group
                            ]
                        ),

                    "confidence":
                        self.mean(
                            [
                                c["confidence"]
                                for c in group
                            ]
                        ),
                }
            )

            start = end

        return {
            "test":
                "TEMPORAL_BLOCKS",

            "blocks":
                result,

            "first_to_last_three_way_delta":
                (
                    result[-1]["three_way"]
                    - result[0]["three_way"]
                    if len(result) >= 2
                    else 0.0
                ),

            "first_to_last_error_delta":
                (
                    result[-1]["prediction_error"]
                    - result[0]["prediction_error"]
                    if len(result) >= 2
                    else 0.0
                ),
        }

    # ============================================================
    # TEST 6 — STATE TRANSITIONS
    # ============================================================

    def state_transitions(self) -> dict:

        transitions = Counter()

        states = [
            c["state"]
            for c in self.cases
        ]

        for previous, current in zip(
            states,
            states[1:],
        ):
            transitions[
                f"{previous} -> {current}"
            ] += 1

        return {
            "test":
                "STATE_TRANSITIONS",

            "cases":
                len(states),

            "transitions":
                dict(transitions),

            "transition_count":
                max(
                    0,
                    len(states) - 1,
                ),

            "states":
                dict(
                    Counter(states)
                ),
        }

    # ============================================================
    # TEST 7 — CONVERGENCE PERSISTENCE
    # ============================================================

    def persistence_analysis(self) -> dict:

        if len(self.cases) < 2:
            return {
                "test":
                    "CONVERGENCE_PERSISTENCE",

                "status":
                    "INSUFFICIENT_HISTORY",
            }

        convergent_following_convergence = []
        divergent_following_divergence = []

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            if previous["three_way"]:
                convergent_following_convergence.append(
                    current["three_way"]
                )

            if not previous["three_way"]:
                divergent_following_divergence.append(
                    not current["three_way"]
                )

        return {
            "test":
                "CONVERGENCE_PERSISTENCE",

            "convergence_following_convergence":
                self._rate(
                    convergent_following_convergence
                ),

            "divergence_following_divergence":
                self._rate(
                    divergent_following_divergence
                ),

            "convergence_transition_count":
                len(
                    convergent_following_convergence
                ),

            "divergence_transition_count":
                len(
                    divergent_following_divergence
                ),
        }

    # ============================================================
    # TEST 8 — FAILURE RECURRENCE
    # ============================================================

    def failure_recurrence(self) -> dict:

        failure_sequence = [
            c["failure_class"]
            for c in self.cases
            if c["failure_class"]
            != "NO_FAILURE"
        ]

        adjacent_same = 0

        for previous, current in zip(
            failure_sequence,
            failure_sequence[1:],
        ):
            if previous == current:
                adjacent_same += 1

        counts = Counter(
            failure_sequence
        )

        return {
            "test":
                "FAILURE_RECURRENCE",

            "failure_cases":
                len(failure_sequence),

            "failure_classes":
                dict(counts),

            "adjacent_same_failure_class":
                adjacent_same,

            "unique_failure_classes":
                len(counts),
        }

    # ============================================================
    # TEST 9 — FAILURE TRANSITIONS
    # ============================================================

    def failure_transitions(self) -> dict:

        transitions = Counter()

        for previous, current in zip(
            self.cases,
            self.cases[1:],
        ):

            previous_failure = (
                previous["failure_class"]
            )

            current_failure = (
                current["failure_class"]
            )

            transitions[
                f"{previous_failure} -> "
                f"{current_failure}"
            ] += 1

        return {
            "test":
                "FAILURE_TRANSITIONS",

            "transitions":
                dict(transitions),
        }

    # ============================================================
    # TEST 10 — RUN LENGTHS
    # ============================================================

    def run_lengths(self) -> dict:

        if not self.cases:
            return {
                "test":
                    "RUN_LENGTHS",
                "status":
                    "NO_EXPERIENCE",
            }

        runs = []

        current_state = (
            "CONVERGENT"
            if self.cases[0]["three_way"]
            else "DIVERGENT"
        )

        length = 0

        for case in self.cases:

            state = (
                "CONVERGENT"
                if case["three_way"]
                else "DIVERGENT"
            )

            if state == current_state:
                length += 1

            else:
                runs.append(
                    {
                        "state":
                            current_state,
                        "length":
                            length,
                    }
                )

                current_state = state
                length = 1

        runs.append(
            {
                "state":
                    current_state,
                "length":
                    length,
            }
        )

        convergence_runs = [
            r["length"]
            for r in runs
            if r["state"]
            == "CONVERGENT"
        ]

        divergence_runs = [
            r["length"]
            for r in runs
            if r["state"]
            == "DIVERGENT"
        ]

        return {
            "test":
                "RUN_LENGTHS",

            "runs":
                runs,

            "convergence_max_run":
                max(
                    convergence_runs,
                    default=0,
                ),

            "divergence_max_run":
                max(
                    divergence_runs,
                    default=0,
                ),

            "convergence_mean_run":
                self.mean(
                    convergence_runs
                ),

            "divergence_mean_run":
                self.mean(
                    divergence_runs
                ),
        }

    # ============================================================
    # TEST 11 — PRE/POST DISAGREEMENT
    # ============================================================

    def disagreement_followup(self) -> dict:

        disagreement_followups = []

        agreement_followups = []

        for index in range(
            len(self.cases) - 1
        ):

            current = self.cases[index]
            following = self.cases[index + 1]

            if current["model_wisdom"]:
                agreement_followups.append(
                    following["three_way"]
                )

            else:
                disagreement_followups.append(
                    following["three_way"]
                )

        agreement_rate = self._rate(
            agreement_followups
        )

        disagreement_rate = self._rate(
            disagreement_followups
        )

        return {
            "test":
                "DISAGREEMENT_FOLLOWUP",

            "agreement_followups":
                len(agreement_followups),

            "disagreement_followups":
                len(disagreement_followups),

            "next_case_convergence_after_agreement":
                agreement_rate,

            "next_case_convergence_after_disagreement":
                disagreement_rate,

            "delta":
                (
                    disagreement_rate
                    - agreement_rate
                ),

            "interpretation":
                self._interpret_delta(
                    disagreement_rate
                    - agreement_rate
                ),
        }

    # ============================================================
    # TEST 12 — LOCAL CONTEXT
    # ============================================================

    def local_context(self) -> dict:

        rows = []

        for index, case in enumerate(
            self.cases
        ):

            previous = (
                self.cases[index - 1]
                if index > 0
                else None
            )

            following = (
                self.cases[index + 1]
                if index + 1
                < len(self.cases)
                else None
            )

            rows.append(
                {
                    "case_id":
                        case["case_id"],

                    "index":
                        index,

                    "state":
                        case["state"],

                    "failure_class":
                        case["failure_class"],

                    "previous_state":
                        (
                            previous["state"]
                            if previous
                            else None
                        ),

                    "next_state":
                        (
                            following["state"]
                            if following
                            else None
                        ),

                    "previous_three_way":
                        (
                            previous["three_way"]
                            if previous
                            else None
                        ),

                    "next_three_way":
                        (
                            following["three_way"]
                            if following
                            else None
                        ),
                }
            )

        return {
            "test":
                "LOCAL_CONTEXT",

            "cases":
                rows,
        }

    # ============================================================
    # TEST 13 — EVIDENCE CONDITIONING
    # ============================================================

    def evidence_conditioning(
        self,
    ) -> dict:

        strong = [
            c
            for c in self.cases
            if c["evidence_strength"]
            >= 0.5
        ]

        weak = [
            c
            for c in self.cases
            if c["evidence_strength"]
            < 0.5
        ]

        high_agreement = [
            c
            for c in self.cases
            if c["evidence_agreement"]
            >= 0.5
        ]

        low_agreement = [
            c
            for c in self.cases
            if c["evidence_agreement"]
            < 0.5
        ]

        return {
            "test":
                "EVIDENCE_CONDITIONING",

            "strong_evidence_cases":
                len(strong),

            "weak_evidence_cases":
                len(weak),

            "strong_evidence_convergence":
                self._rate(
                    [
                        c["three_way"]
                        for c in strong
                    ]
                ),

            "weak_evidence_convergence":
                self._rate(
                    [
                        c["three_way"]
                        for c in weak
                    ]
                ),

            "high_agreement_cases":
                len(high_agreement),

            "low_agreement_cases":
                len(low_agreement),

            "high_agreement_convergence":
                self._rate(
                    [
                        c["three_way"]
                        for c in high_agreement
                    ]
                ),

            "low_agreement_convergence":
                self._rate(
                    [
                        c["three_way"]
                        for c in low_agreement
                    ]
                ),
        }

    # ============================================================
    # TEST 14 — DIRECTIONAL PATTERNS
    # ============================================================

    def directional_patterns(self) -> dict:

        patterns = Counter()

        for case in self.cases:

            pattern = (
                f"M{int(case['model'])}"
                f"W{int(case['wisdom'])}"
                f"R{int(case['actual'])}"
            )

            patterns[pattern] += 1

        return {
            "test":
                "DIRECTIONAL_PATTERNS",

            "patterns":
                dict(patterns),

            "pattern_count":
                len(patterns),

            "total_cases":
                len(self.cases),
        }

    # ============================================================
    # TEST 15 — SEQUENTIAL RECONVERGENCE
    # ============================================================

    def sequential_reconvergence(
        self,
    ) -> dict:

        results = []

        if len(self.cases) < 2:
            return {
                "test":
                    "SEQUENTIAL_RECONVERGENCE",

                "status":
                    "INSUFFICIENT_HISTORY",

                "sequence":
                    [],
            }

        for index in range(
            1,
            len(self.cases),
        ):

            previous = self.cases[
                index - 1
            ]

            current = self.cases[
                index
            ]

            results.append(
                {
                    "from_case":
                        previous["case_id"],

                    "to_case":
                        current["case_id"],

                    "from_state":
                        previous["state"],

                    "to_state":
                        current["state"],

                    "reconverged":
                        (
                            not previous["three_way"]
                            and current["three_way"]
                        ),

                    "persisted":
                        (
                            previous["three_way"]
                            and current["three_way"]
                        ),

                    "newly_diverged":
                        (
                            previous["three_way"]
                            and not current["three_way"]
                        ),

                    "remained_divergent":
                        (
                            not previous["three_way"]
                            and not current["three_way"]
                        ),
                }
            )

        return {
            "test":
                "SEQUENTIAL_RECONVERGENCE",

            "sequence":
                results,

            "reconvergence_events":
                sum(
                    1
                    for r in results
                    if r["reconverged"]
                ),

            "persistence_events":
                sum(
                    1
                    for r in results
                    if r["persisted"]
                ),

            "new_divergence_events":
                sum(
                    1
                    for r in results
                    if r["newly_diverged"]
                ),

            "persistent_divergence_events":
                sum(
                    1
                    for r in results
                    if r["remained_divergent"]
                ),
        }

    # ============================================================
    # TEST 16 — STATE ENTROPY
    # ============================================================

    def state_entropy(self) -> dict:

        states = [
            (
                "CONVERGENT"
                if c["three_way"]
                else "DIVERGENT"
            )
            for c in self.cases
        ]

        counts = Counter(states)
        total = len(states)

        if total == 0:
            return {
                "test":
                    "STATE_ENTROPY",

                "entropy":
                    0.0,

                "status":
                    "NO_EXPERIENCE",
            }

        entropy = 0.0

        for count in counts.values():

            probability = (
                count / total
            )

            if probability > 0:
                entropy -= (
                    probability
                    * math.log2(
                        probability
                    )
                )

        return {
            "test":
                "STATE_ENTROPY",

            "entropy_bits":
                entropy,

            "state_counts":
                dict(counts),

            "possible_binary_entropy_max":
                1.0,
        }

    # ============================================================
    # TEST 17 — FIRST/LAST TRAJECTORY
    # ============================================================

    def trajectory(self) -> dict:

        if not self.cases:
            return {
                "test":
                    "TRAJECTORY",
                "status":
                    "NO_EXPERIENCE",
            }

        first = self.cases[0]
        last = self.cases[-1]

        metrics = [
            "three_way",
            "model_reality",
            "wisdom_reality",
            "model_wisdom",
            "confidence",
            "prediction_error",
            "evidence_strength",
            "evidence_agreement",
        ]

        delta = {}

        for metric in metrics:

            delta[metric] = (
                self.safe_float(
                    last[metric]
                )
                - self.safe_float(
                    first[metric]
                )
            )

        return {
            "test":
                "TRAJECTORY",

            "first_case":
                first["case_id"],

            "last_case":
                last["case_id"],

            "delta":
                delta,
        }

    # ============================================================
    # TEST 18 — OBSERVED VERSUS MARGINAL EXPECTATION
    # ============================================================

    def marginal_expectation(
        self,
    ) -> dict:

        n = len(self.cases)

        if n == 0:
            return {
                "test":
                    "MARGINAL_EXPECTATION",

                "status":
                    "NO_EXPERIENCE",
            }

        model_positive = self._rate(
            [
                c["model"]
                for c in self.cases
            ]
        )

        wisdom_positive = self._rate(
            [
                c["wisdom"]
                for c in self.cases
            ]
        )

        reality_positive = self._rate(
            [
                c["actual"]
                for c in self.cases
            ]
        )

        expected_all_positive = (
            model_positive
            * wisdom_positive
            * reality_positive
        )

        expected_all_negative = (
            (1.0 - model_positive)
            * (1.0 - wisdom_positive)
            * (1.0 - reality_positive)
        )

        expected_three_way_independence = (
            expected_all_positive
            + expected_all_negative
        )

        observed_three_way = self._rate(
            [
                c["three_way"]
                for c in self.cases
            ]
        )

        return {
            "test":
                "MARGINAL_EXPECTATION",

            "model_positive_rate":
                model_positive,

            "wisdom_positive_rate":
                wisdom_positive,

            "reality_positive_rate":
                reality_positive,

            "observed_three_way":
                observed_three_way,

            "independence_expected_three_way":
                expected_three_way_independence,

            "observed_minus_expected":
                (
                    observed_three_way
                    - expected_three_way_independence
                ),

            "warning":
                (
                    "This is a descriptive marginal "
                    "baseline, not a statistical "
                    "significance test."
                ),
        }

    # ============================================================
    # TEST 19 — CASE DIAGNOSTIC MAP
    # ============================================================

    def diagnostic_map(self) -> List[dict]:

        result = []

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

            elif case["model_wisdom"]:

                diagnostic = (
                    "MODEL_AND_WISDOM_AGREE_BUT_WRONG"
                )

            else:

                diagnostic = (
                    "MODEL_WISDOM_DIVERGENCE"
                )

            result.append(
                {
                    "case_id":
                        case["case_id"],

                    "index":
                        case["index"],

                    "model":
                        case["model"],

                    "wisdom":
                        case["wisdom"],

                    "reality":
                        case["actual"],

                    "state":
                        case["state"],

                    "diagnostic":
                        diagnostic,

                    "failure_class":
                        case["failure_class"],

                    "failures":
                        case["failures"],
                }
            )

        return result

    # ============================================================
    # PHENOMENON SYNTHESIS
    # ============================================================

    def phenomenon_summary(
        self,
        report: dict,
    ) -> dict:

        basic = report[
            "basic_summary"
        ]

        if not self.cases:

            return {
                "classification":
                    "NO_OBSERVABLE_PHENOMENON",

                "confidence":
                    "NONE",

                "reason":
                    "No persisted experience.",
            }

        n = len(self.cases)

        if n < 4:

            return {
                "classification":
                    "PHENOMENON_NOT_YET_IDENTIFIABLE",

                "confidence":
                    "LOW",

                "reason":
                    (
                        "The engine is operating, "
                        "but the persisted history "
                        "is too small to establish "
                        "temporal or transition "
                        "structure."
                    ),

                "observed":
                    {
                        "cases":
                            n,

                        "three_way":
                            basic[
                                "full_convergence"
                            ],
                    },
            }

        information = report[
            "disagreement_information"
        ]

        persistence = report[
            "persistence"
        ]

        marginal = report[
            "marginal_expectation"
        ]

        trajectory = report[
            "trajectory"
        ]

        signals = []

        if abs(
            information[
                "convergence_delta"
            ]
        ) >= 0.10:

            signals.append(
                "DISAGREEMENT_HAS_OBSERVED_ASSOCIATION"
            )

        if (
            persistence[
                "convergence_following_convergence"
            ] >= 0.60
        ):

            signals.append(
                "CONVERGENCE_PERSISTENCE"
            )

        if (
            persistence[
                "divergence_following_divergence"
            ] >= 0.60
        ):

            signals.append(
                "DIVERGENCE_PERSISTENCE"
            )

        if (
            marginal[
                "observed_minus_expected"
            ] >= 0.10
        ):

            signals.append(
                "THREE_WAY_EXCEEDS_MARGINAL_BASELINE"
            )

        if (
            abs(
                trajectory[
                    "delta"
                ][
                    "three_way"
                ]
            )
            >= 0.10
        ):

            signals.append(
                "TEMPORAL_TRAJECTORY"
            )

        if len(signals) >= 3:

            classification = (
                "MULTI_SIGNAL_RECONVERGENCE_PHENOMENON"
            )

            confidence = "MEDIUM"

        elif len(signals) >= 1:

            classification = (
                "PRELIMINARY_RECONVERGENCE_STRUCTURE"
            )

            confidence = "LOW_TO_MEDIUM"

        else:

            classification = (
                "NO_STRONG_STRUCTURE_DETECTED"
            )

            confidence = "LOW"

        return {
            "classification":
                classification,

            "confidence":
                confidence,

            "signal_count":
                len(signals),

            "signals":
                signals,

            "important_caveat":
                (
                    "These are discovery signals, "
                    "not proof of causality or "
                    "statistical significance."
                ),
        }

    # ============================================================
    # COMPLETE REPORT
    # ============================================================

    def run(
        self,
    ) -> dict:

        report = {
            "engine":
                "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_GAUNTLET",

            "version":
                VERSION,

            "data_source":
                os.path.abspath(
                    self.reflection_path
                ),

            "data_integrity":
                {
                    "historical_records":
                        len(self.reflections),

                    "analyzed_cases":
                        len(self.cases),

                    "synthetic_data_used":
                        False,

                    "historical_data_modified":
                        False,

                    "model_modified":
                        False,

                    "trading_performed":
                        False,
                },

            "basic_summary":
                self.basic_summary(),

            "error_topology":
                self.error_topology(),

            "path_specialization":
                self.path_specialization(),

            "disagreement_information":
                self.disagreement_information(),

            "confidence_analysis":
                self.confidence_analysis(),

            "temporal_blocks":
                self.temporal_blocks(),

            "state_transitions":
                self.state_transitions(),

            "persistence":
                self.persistence_analysis(),

            "failure_recurrence":
                self.failure_recurrence(),

            "failure_transitions":
                self.failure_transitions(),

            "run_lengths":
                self.run_lengths(),

            "disagreement_followup":
                self.disagreement_followup(),

            "local_context":
                self.local_context(),

            "evidence_conditioning":
                self.evidence_conditioning(),

            "directional_patterns":
                self.directional_patterns(),

            "sequential_reconvergence":
                self.sequential_reconvergence(),

            "state_entropy":
                self.state_entropy(),

            "trajectory":
                self.trajectory(),

            "marginal_expectation":
                self.marginal_expectation(),

            "case_diagnostics":
                self.diagnostic_map(),
        }

        report[
            "phenomenon"
        ] = self.phenomenon_summary(
            report
        )

        return report


# ================================================================
# CLI
# ================================================================

def print_section(
    title: str,
):
    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def main():

    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE PHENOMENON GAUNTLET V1")
    print("SEARCHING FOR UNDERLYING STRUCTURE IN PERSISTED EXPERIENCE")
    print("=" * 76)

    engine = PhenomenonGauntlet()

    report = engine.run()

    print()
    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    phenomenon = report[
        "phenomenon"
    ]

    print_section(
        "PHENOMENON DISCOVERY VERDICT"
    )

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

    if "signal_count" in phenomenon:

        print(
            "SIGNALS:",
            phenomenon[
                "signal_count"
            ],
        )

        for signal in phenomenon.get(
            "signals",
            [],
        ):

            print(
                "  +",
                signal,
            )

    print_section(
        "CORE OBSERVATION"
    )

    basic = report[
        "basic_summary"
    ]

    print(
        "CASES:",
        basic.get(
            "cases",
            0,
        ),
    )

    print(
        "THREE-WAY:",
        round(
            basic.get(
                "full_convergence",
                0.0,
            ),
            6,
        ),
    )

    print(
        "MODEL → REALITY:",
        round(
            basic.get(
                "model_reality",
                0.0,
            ),
            6,
        ),
    )

    print(
        "WISDOM → REALITY:",
        round(
            basic.get(
                "wisdom_reality",
                0.0,
            ),
            6,
        ),
    )

    print(
        "MODEL ↔ WISDOM:",
        round(
            basic.get(
                "model_wisdom",
                0.0,
            ),
            6,
        ),
    )

    print_section(
        "DISAGREEMENT INFORMATION"
    )

    disagreement = report[
        "disagreement_information"
    ]

    print(
        "AGREEMENT CASES:",
        disagreement[
            "agreement_cases"
        ],
    )

    print(
        "DISAGREEMENT CASES:",
        disagreement[
            "disagreement_cases"
        ],
    )

    print(
        "CONVERGENCE AFTER AGREEMENT:",
        round(
            disagreement[
                "agreement_convergence"
            ],
            6,
        ),
    )

    print(
        "CONVERGENCE AFTER DISAGREEMENT:",
        round(
            disagreement[
                "disagreement_convergence"
            ],
            6,
        ),
    )

    print(
        "DELTA:",
        round(
            disagreement[
                "convergence_delta"
            ],
            6,
        ),
    )

    print_section(
        "TEMPORAL STRUCTURE"
    )

    temporal = report[
        "temporal_blocks"
    ]

    for block in temporal.get(
        "blocks",
        [],
    ):

        print(
            f"BLOCK {block['block']}: "
            f"cases={block['count']} "
            f"three_way={block['three_way']:.6f} "
            f"error={block['prediction_error']:.6f}"
        )

    print_section(
        "STATE TRANSITIONS"
    )

    transitions = report[
        "state_transitions"
    ]

    for key, value in transitions[
        "transitions"
    ].items():

        print(
            f"{key}: {value}"
        )

    print_section(
        "PERSISTENCE"
    )

    persistence = report[
        "persistence"
    ]

    for key, value in persistence.items():

        if key == "test":
            continue

        if isinstance(
            value,
            float,
        ):

            print(
                key + ":",
                round(
                    value,
                    6,
                ),
            )

        else:

            print(
                key + ":",
                value,
            )

    print_section(
        "MARGINAL BASELINE"
    )

    marginal = report[
        "marginal_expectation"
    ]

    print(
        "OBSERVED THREE-WAY:",
        round(
            marginal.get(
                "observed_three_way",
                0.0,
            ),
            6,
        ),
    )

    print(
        "INDEPENDENCE EXPECTATION:",
        round(
            marginal.get(
                "independence_expected_three_way",
                0.0,
            ),
            6,
        ),
    )

    print(
        "OBSERVED - EXPECTED:",
        round(
            marginal.get(
                "observed_minus_expected",
                0.0,
            ),
            6,
        ),
    )

    print_section(
        "PER-CASE DIAGNOSTICS"
    )

    for case in report[
        "case_diagnostics"
    ]:

        print(
            f"CASE {case['index'] + 1}: "
            f"{case['case_id']}"
        )

        print(
            "  MODEL:",
            case["model"],
            "WISDOM:",
            case["wisdom"],
            "REALITY:",
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
            "  FAILURE:",
            case["failure_class"],
        )

        print(
            "  FAILED PATHS:",
            case["failures"],
        )

    print_section(
        "NOMINALITY"
    )

    integrity = report[
        "data_integrity"
    ]

    nominal = (
        integrity[
            "synthetic_data_used"
        ] is False
        and integrity[
            "historical_data_modified"
        ] is False
        and integrity[
            "model_modified"
        ] is False
        and integrity[
            "trading_performed"
        ] is False
    )

    print(
        "ENGINE OPERATION:",
        "💯 NOMINAL"
        if nominal
        else "NON-NOMINAL",
    )

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

    print()
    print("=" * 76)
    print("GAUNTLET COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
