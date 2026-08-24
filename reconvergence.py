#!/usr/bin/env python3

"""
BIRTH_EDGE RECONVERGENCE V2

Purpose
-------
Measure whether independent evidence paths converge toward realized
outcomes across persisted historical experience.

Paths:

    MODEL
       │
       ├── prediction probability
       ├── model direction
       └── model confidence
       │
    WISDOM
       │
       └── wisdom direction
       │
    DISCERNMENT
       │
       ├── evidence agreement
       └── evidence strength
       │
    REALITY
       │
       └── actual historical outcome

V2 changes
----------
1. Three-way convergence is calculated explicitly:

       MODEL == WISDOM == REALITY

2. Per-case diagnostics identify exactly which relationship failed.

3. Three-way failures distinguish:
       - MODEL_WISDOM
       - MODEL_REALITY
       - WISDOM_REALITY
       - MULTIPLE_PATHS
       - NO_FAILURE

4. No synthetic evidence.
5. No altered historical outcomes.
6. No trading.
7. No automatic modification of persisted evidence.

Only persisted experience is analyzed.
"""

import json
import math
import os
import statistics
from typing import Dict, List, Optional


MODEL_FILE = "data/ml_model.json"
MEMORY_FILE = "data/ml_memory.json"
REFLECTION_FILE = "data/ml_reflection.json"


class ReconvergenceEngine:

    VERSION = 2

    def __init__(
        self,
        reflection_path: str = REFLECTION_FILE,
        memory_path: str = MEMORY_FILE,
        model_path: str = MODEL_FILE,
    ):
        self.reflection_path = reflection_path
        self.memory_path = memory_path
        self.model_path = model_path

        self.reflections = self._load_list(
            reflection_path,
            "reflections",
        )

        self.memory = self._load_list(
            memory_path,
            "memory",
        )

        self.model = self._load_dict(
            model_path,
        )

    # ============================================================
    # SAFE NUMERIC HANDLING
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
        low: float,
        high: float,
    ) -> float:
        return max(
            low,
            min(high, value),
        )

    # ============================================================
    # PERSISTENCE
    # ============================================================

    @staticmethod
    def _load_list(
        path: str,
        key: str,
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
                    key,
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

    @staticmethod
    def _load_dict(
        path: str,
    ) -> dict:

        path = os.path.abspath(path)

        if not os.path.exists(path):
            return {}

        try:
            with open(
                path,
                "r",
                encoding="utf-8",
            ) as handle:

                payload = json.load(handle)

            return (
                payload
                if isinstance(payload, dict)
                else {}
            )

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            return {}

    # ============================================================
    # SINGLE REFLECTION ANALYSIS
    # ============================================================

    def analyze_reflection(
        self,
        reflection: dict,
    ) -> Dict[str, object]:

        probability = self._safe_float(
            reflection.get("probability"),
            0.5,
        )

        actual_raw = self._safe_float(
            reflection.get("actual_outcome"),
            0.0,
        )

        actual = (
            1.0
            if actual_raw >= 0.5
            else 0.0
        )

        model_direction = (
            1.0
            if probability >= 0.5
            else 0.0
        )

        wisdom_score = self._clip(
            self._safe_float(
                reflection.get(
                    "wisdom_score"
                ),
                0.5,
            ),
            0.0,
            1.0,
        )

        wisdom_direction = (
            1.0
            if wisdom_score >= 0.5
            else 0.0
        )

        agreement = self._clip(
            self._safe_float(
                reflection.get(
                    "evidence_agreement"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        evidence_strength = self._clip(
            self._safe_float(
                reflection.get(
                    "evidence_strength"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        confidence = self._clip(
            self._safe_float(
                reflection.get(
                    "model_confidence"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        reflection_score = self._clip(
            self._safe_float(
                reflection.get(
                    "reflection_score"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        prediction_error = self._clip(
            self._safe_float(
                reflection.get(
                    "prediction_error"
                ),
                abs(probability - actual),
            ),
            0.0,
            1.0,
        )

        # ========================================================
        # EXPLICIT PATH RELATIONSHIPS
        # ========================================================

        model_wisdom_agreement = (
            1.0
            if model_direction == wisdom_direction
            else 0.0
        )

        model_reality_alignment = (
            1.0
            if model_direction == actual
            else 0.0
        )

        wisdom_reality_alignment = (
            1.0
            if wisdom_direction == actual
            else 0.0
        )

        # ========================================================
        # CORRECT THREE-WAY CONVERGENCE
        #
        # This is intentionally NOT inferred from pairwise
        # averages.
        #
        # It requires all three independently:
        #
        #     MODEL == WISDOM == REALITY
        # ========================================================

        three_way_convergence = (
            1.0
            if (
                model_direction
                == wisdom_direction
                == actual
            )
            else 0.0
        )

        # ========================================================
        # PER-CASE FAILURE DIAGNOSTICS
        # ========================================================

        failures = []

        if model_direction != wisdom_direction:
            failures.append(
                "MODEL_WISDOM"
            )

        if model_direction != actual:
            failures.append(
                "MODEL_REALITY"
            )

        if wisdom_direction != actual:
            failures.append(
                "WISDOM_REALITY"
            )

        if not failures:
            failure_class = "NO_FAILURE"

        elif len(failures) == 1:
            failure_class = failures[0]

        else:
            failure_class = "MULTIPLE_PATHS"

        # ========================================================
        # HUMAN-READABLE DIAGNOSTIC
        # ========================================================

        diagnostic = self._build_diagnostic(
            model_direction=model_direction,
            wisdom_direction=wisdom_direction,
            actual=actual,
            failures=failures,
        )

        # ========================================================
        # CONFIDENCE ALIGNMENT
        # ========================================================

        confidence_alignment = self._clip(
            self._safe_float(
                reflection.get(
                    "confidence_alignment"
                ),
                0.0,
            ),
            0.0,
            1.0,
        )

        # ========================================================
        # RECONVERGENCE SCORE
        # ========================================================

        reconvergence_score = (
            0.20 * model_reality_alignment
            + 0.20 * wisdom_reality_alignment
            + 0.15 * model_wisdom_agreement
            + 0.15 * agreement
            + 0.15 * confidence_alignment
            + 0.15 * reflection_score
        )

        reconvergence_score = self._clip(
            reconvergence_score,
            0.0,
            1.0,
        )

        return {
            "model_direction": model_direction,
            "wisdom_direction": wisdom_direction,
            "actual_outcome": actual,

            "model_reality_alignment":
                model_reality_alignment,

            "wisdom_reality_alignment":
                wisdom_reality_alignment,

            "model_wisdom_agreement":
                model_wisdom_agreement,

            "three_way_convergence":
                three_way_convergence,

            "failure_paths":
                failures,

            "failure_class":
                failure_class,

            "diagnostic":
                diagnostic,

            "evidence_agreement":
                agreement,

            "evidence_strength":
                evidence_strength,

            "model_confidence":
                confidence,

            "confidence_alignment":
                confidence_alignment,

            "prediction_error":
                prediction_error,

            "reflection_score":
                reflection_score,

            "reconvergence_score":
                reconvergence_score,
        }

    # ============================================================
    # DIAGNOSTIC BUILDER
    # ============================================================

    @staticmethod
    def _build_diagnostic(
        model_direction: float,
        wisdom_direction: float,
        actual: float,
        failures: List[str],
    ) -> str:

        def label(value):
            return (
                "POSITIVE"
                if value >= 0.5
                else "NEGATIVE"
            )

        model = label(model_direction)
        wisdom = label(wisdom_direction)
        reality = label(actual)

        if not failures:
            return (
                "FULL_CONVERGENCE: "
                f"MODEL={model}, "
                f"WISDOM={wisdom}, "
                f"REALITY={reality}"
            )

        if failures == ["MODEL_WISDOM"]:
            return (
                "MODEL_WISDOM_DIVERGENCE: "
                f"MODEL={model}, "
                f"WISDOM={wisdom}, "
                f"REALITY={reality}; "
                "both paths independently match reality."
            )

        if failures == ["MODEL_REALITY"]:
            return (
                "MODEL_REALITY_FAILURE: "
                f"MODEL={model}, "
                f"WISDOM={wisdom}, "
                f"REALITY={reality}; "
                "wisdom matches reality but model does not."
            )

        if failures == ["WISDOM_REALITY"]:
            return (
                "WISDOM_REALITY_FAILURE: "
                f"MODEL={model}, "
                f"WISDOM={wisdom}, "
                f"REALITY={reality}; "
                "model matches reality but wisdom does not."
            )

        return (
            "MULTIPLE_PATH_FAILURE: "
            f"MODEL={model}, "
            f"WISDOM={wisdom}, "
            f"REALITY={reality}; "
            f"failed_paths={','.join(failures)}"
        )

    # ============================================================
    # GLOBAL RECONVERGENCE
    # ============================================================

    def analyze(
        self,
        window: Optional[int] = None,
    ) -> Dict[str, object]:

        reflections = list(
            self.reflections
        )

        if window is not None:

            try:
                window = int(window)

            except (
                TypeError,
                ValueError,
            ):
                window = None

            if window is not None:

                window = max(
                    1,
                    window,
                )

                reflections = reflections[
                    -window:
                ]

        if not reflections:

            return {
                "version": self.VERSION,
                "status": "NO_EXPERIENCE",
                "reflection_count": 0,
                "reconvergence_score": 0.0,
                "three_way_convergence": 0.0,
                "model_reality_alignment": 0.0,
                "wisdom_reality_alignment": 0.0,
                "model_wisdom_agreement": 0.0,
                "confidence_alignment": 0.0,
                "prediction_error": 0.0,
                "evidence_agreement": 0.0,
                "evidence_strength": 0.0,
                "trend": "UNDETERMINED",
                "window": window,
            }

        analyzed = [
            self.analyze_reflection(
                reflection
            )
            for reflection in reflections
        ]

        def mean(key: str) -> float:

            values = [
                self._safe_float(
                    item.get(key),
                    0.0,
                )
                for item in analyzed
            ]

            return (
                statistics.fmean(values)
                if values
                else 0.0
            )

        score = mean(
            "reconvergence_score"
        )

        three_way = mean(
            "three_way_convergence"
        )

        model_reality = mean(
            "model_reality_alignment"
        )

        wisdom_reality = mean(
            "wisdom_reality_alignment"
        )

        model_wisdom = mean(
            "model_wisdom_agreement"
        )

        confidence_alignment = mean(
            "confidence_alignment"
        )

        prediction_error = mean(
            "prediction_error"
        )

        evidence_agreement = mean(
            "evidence_agreement"
        )

        evidence_strength = mean(
            "evidence_strength"
        )

        trend = self._temporal_trend(
            analyzed
        )

        # ========================================================
        # CLASSIFICATION
        # ========================================================

        if len(reflections) < 3:

            status = "INSUFFICIENT_HISTORY"

        elif score >= 0.75:

            status = "STRONG_RECONVERGENCE"

        elif score >= 0.60:

            status = "RECONVERGING"

        elif score >= 0.45:

            status = "PARTIAL_RECONVERGENCE"

        else:

            status = "DIVERGENT"

        return {
            "version": self.VERSION,

            "status":
                status,

            "reflection_count":
                len(reflections),

            "memory_count":
                len(self.memory),

            "reconvergence_score":
                score,

            "three_way_convergence":
                three_way,

            "model_reality_alignment":
                model_reality,

            "wisdom_reality_alignment":
                wisdom_reality,

            "model_wisdom_agreement":
                model_wisdom,

            "confidence_alignment":
                confidence_alignment,

            "prediction_error":
                prediction_error,

            "evidence_agreement":
                evidence_agreement,

            "evidence_strength":
                evidence_strength,

            "trend":
                trend,

            "window":
                window,
        }

    # ============================================================
    # TEMPORAL TREND
    # ============================================================

    def _temporal_trend(
        self,
        analyzed: List[dict],
    ) -> str:

        if len(analyzed) < 4:
            return "UNDETERMINED"

        midpoint = len(analyzed) // 2

        early = analyzed[
            :midpoint
        ]

        late = analyzed[
            midpoint:
        ]

        def avg(
            group,
            key,
        ):

            values = [
                self._safe_float(
                    item.get(key),
                    0.0,
                )
                for item in group
            ]

            return (
                statistics.fmean(values)
                if values
                else 0.0
            )

        early_score = avg(
            early,
            "reconvergence_score",
        )

        late_score = avg(
            late,
            "reconvergence_score",
        )

        delta = (
            late_score
            - early_score
        )

        if delta >= 0.10:
            return "CONVERGING"

        if delta <= -0.10:
            return "DIVERGING"

        return "STABLE"

    # ============================================================
    # PATH BREAKDOWN
    # ============================================================

    def path_breakdown(
        self,
    ) -> Dict[str, object]:

        if not self.reflections:

            return {
                "model": {},
                "wisdom": {},
                "discernment": {},
                "reality": {},
            }

        analyzed = [
            self.analyze_reflection(
                reflection
            )
            for reflection in self.reflections
        ]

        def avg(key):

            values = [
                self._safe_float(
                    item.get(key),
                    0.0,
                )
                for item in analyzed
            ]

            return (
                statistics.fmean(values)
                if values
                else 0.0
            )

        return {
            "model": {
                "reality_alignment":
                    avg(
                        "model_reality_alignment"
                    ),

                "confidence":
                    avg(
                        "model_confidence"
                    ),

                "prediction_error":
                    avg(
                        "prediction_error"
                    ),
            },

            "wisdom": {
                "reality_alignment":
                    avg(
                        "wisdom_reality_alignment"
                    ),
            },

            "discernment": {
                "agreement":
                    avg(
                        "evidence_agreement"
                    ),

                "strength":
                    avg(
                        "evidence_strength"
                    ),
            },

            "reality": {
                "three_way_convergence":
                    avg(
                        "three_way_convergence"
                    ),

                "reflection_score":
                    avg(
                        "reflection_score"
                    ),
            },
        }

    # ============================================================
    # DISAGREEMENT ANALYSIS
    # ============================================================

    def disagreement_report(
        self,
    ) -> Dict[str, object]:

        if not self.reflections:

            return {
                "count": 0,
                "model_wisdom_conflicts": 0,
                "model_reality_conflicts": 0,
                "wisdom_reality_conflicts": 0,
                "three_way_failures": 0,
                "failure_classes": {},
            }

        model_wisdom_conflicts = 0
        model_reality_conflicts = 0
        wisdom_reality_conflicts = 0
        three_way_failures = 0

        failure_classes = {}

        for reflection in self.reflections:

            metrics = (
                self.analyze_reflection(
                    reflection
                )
            )

            if (
                metrics[
                    "model_wisdom_agreement"
                ] == 0.0
            ):
                model_wisdom_conflicts += 1

            if (
                metrics[
                    "model_reality_alignment"
                ] == 0.0
            ):
                model_reality_conflicts += 1

            if (
                metrics[
                    "wisdom_reality_alignment"
                ] == 0.0
            ):
                wisdom_reality_conflicts += 1

            if (
                metrics[
                    "three_way_convergence"
                ] == 0.0
            ):
                three_way_failures += 1

            failure_class = metrics[
                "failure_class"
            ]

            failure_classes[
                failure_class
            ] = (
                failure_classes.get(
                    failure_class,
                    0,
                )
                + 1
            )

        total = len(
            self.reflections
        )

        return {
            "count":
                total,

            "model_wisdom_conflicts":
                model_wisdom_conflicts,

            "model_reality_conflicts":
                model_reality_conflicts,

            "wisdom_reality_conflicts":
                wisdom_reality_conflicts,

            "three_way_failures":
                three_way_failures,

            "model_wisdom_conflict_rate":
                model_wisdom_conflicts / total,

            "model_reality_conflict_rate":
                model_reality_conflicts / total,

            "wisdom_reality_conflict_rate":
                wisdom_reality_conflicts / total,

            "three_way_failure_rate":
                three_way_failures / total,

            "failure_classes":
                failure_classes,
        }

    # ============================================================
    # PER-CASE DIAGNOSTICS
    # ============================================================

    def case_diagnostics(
        self,
    ) -> List[dict]:

        diagnostics = []

        for index, reflection in enumerate(
            self.reflections
        ):

            metrics = (
                self.analyze_reflection(
                    reflection
                )
            )

            case_id = (
                reflection.get("id")
                or reflection.get(
                    "case_id"
                )
                or reflection.get(
                    "event_id"
                )
                or f"reflection_{index + 1}"
            )

            diagnostics.append(
                {
                    "case_index":
                        index,

                    "case_id":
                        case_id,

                    "model_direction":
                        metrics[
                            "model_direction"
                        ],

                    "wisdom_direction":
                        metrics[
                            "wisdom_direction"
                        ],

                    "actual_outcome":
                        metrics[
                            "actual_outcome"
                        ],

                    "model_wisdom_agreement":
                        metrics[
                            "model_wisdom_agreement"
                        ],

                    "model_reality_alignment":
                        metrics[
                            "model_reality_alignment"
                        ],

                    "wisdom_reality_alignment":
                        metrics[
                            "wisdom_reality_alignment"
                        ],

                    "three_way_convergence":
                        metrics[
                            "three_way_convergence"
                        ],

                    "failure_paths":
                        metrics[
                            "failure_paths"
                        ],

                    "failure_class":
                        metrics[
                            "failure_class"
                        ],

                    "diagnostic":
                        metrics[
                            "diagnostic"
                        ],
                }
            )

        return diagnostics

    # ============================================================
    # FULL REPORT
    # ============================================================

    def report(
        self,
        window: Optional[int] = None,
    ) -> Dict[str, object]:

        return {
            "engine":
                "BIRTH_EDGE_RECONVERGENCE",

            "version":
                self.VERSION,

            "analysis":
                self.analyze(
                    window=window
                ),

            "paths":
                self.path_breakdown(),

            "disagreement":
                self.disagreement_report(),

            "case_diagnostics":
                self.case_diagnostics(),

            "data_integrity": {
                "reflections_available":
                    len(self.reflections),

                "memory_available":
                    len(self.memory),

                "model_available":
                    bool(self.model),
            },
        }


# ================================================================
# CLI
# ================================================================

def main():

    print("=" * 72)
    print("BIRTH_EDGE RECONVERGENCE V2")
    print("MODEL + WISDOM + DISCERNMENT + REALITY")
    print("=" * 72)

    engine = ReconvergenceEngine()

    report = engine.report()

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    analysis = report[
        "analysis"
    ]

    print()
    print("=" * 72)
    print("PER-CASE RECONVERGENCE DIAGNOSTICS")
    print("=" * 72)

    for case in report[
        "case_diagnostics"
    ]:

        print()
        print(
            f"CASE: {case['case_id']}"
        )

        print(
            "MODEL:",
            case[
                "model_direction"
            ],
        )

        print(
            "WISDOM:",
            case[
                "wisdom_direction"
            ],
        )

        print(
            "REALITY:",
            case[
                "actual_outcome"
            ],
        )

        print(
            "THREE-WAY:",
            case[
                "three_way_convergence"
            ],
        )

        print(
            "FAILURE CLASS:",
            case[
                "failure_class"
            ],
        )

        print(
            "FAILED PATHS:",
            case[
                "failure_paths"
            ],
        )

        print(
            "DIAGNOSTIC:",
            case[
                "diagnostic"
            ],
        )

    print()
    print("=" * 72)
    print("RECONVERGENCE VERDICT")
    print("=" * 72)

    print(
        "STATUS:",
        analysis[
            "status"
        ],
    )

    print(
        "SCORE:",
        round(
            analysis[
                "reconvergence_score"
            ],
            6,
        ),
    )

    print(
        "THREE-WAY:",
        round(
            analysis[
                "three_way_convergence"
            ],
            6,
        ),
    )

    print(
        "TREND:",
        analysis[
            "trend"
        ],
    )

    print(
        "REFLECTIONS:",
        analysis[
            "reflection_count"
        ],
    )

    print("=" * 72)


if __name__ == "__main__":
    main()
