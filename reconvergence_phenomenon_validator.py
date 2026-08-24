#!/usr/bin/env python3
"""
BIRTH_EDGE RECONVERGENCE PHENOMENON VALIDATOR V1

Purpose
-------
Search persisted BIRTH_EDGE experience for recurring structure behind
MODEL / WISDOM / REALITY reconvergence.

This is a discovery/validation instrument.

It DOES NOT:
- modify historical records
- create synthetic observations
- modify the model
- trade
- alter outcomes

It DOES:
- build the complete path-state matrix
- measure path asymmetry
- identify first-break paths
- search for recurring precursors
- search for reconvergence
- search for counterexamples
- measure state persistence/transitions
- calculate effect sizes
- perform deterministic permutation/null tests when possible
- rank candidate underlying phenomena
"""

import json
import math
import os
import random
import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple


REFLECTION_FILE = "data/ml_reflection.json"

VERSION = 1
PERMUTATIONS = 5000
SEED = 731927


class PhenomenonValidator:

    def __init__(self, reflection_path: str = REFLECTION_FILE):
        self.reflection_path = os.path.abspath(reflection_path)
        self.reflections = self._load_reflections()

    # ============================================================
    # SAFE HELPERS
    # ============================================================

    @staticmethod
    def safe_float(value, default=0.0):
        try:
            if value is None:
                return default
            x = float(value)
            return x if math.isfinite(x) else default
        except (TypeError, ValueError, OverflowError):
            return default

    @staticmethod
    def clamp(x, lo=0.0, hi=1.0):
        return max(lo, min(hi, x))

    @staticmethod
    def mean(values):
        return statistics.fmean(values) if values else 0.0

    @staticmethod
    def median(values):
        return statistics.median(values) if values else 0.0

    # ============================================================
    # LOAD REAL HISTORY
    # ============================================================

    def _load_reflections(self):
        if not os.path.exists(self.reflection_path):
            return []

        try:
            with open(self.reflection_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            if isinstance(payload, dict):
                payload = payload.get("reflections", [])

            if not isinstance(payload, list):
                return []

            return [x for x in payload if isinstance(x, dict)]

        except (OSError, ValueError, json.JSONDecodeError):
            return []

    # ============================================================
    # CASE NORMALIZATION
    # ============================================================

    def analyze_case(self, reflection: dict, index: int) -> dict:

        probability = self.safe_float(
            reflection.get("probability"),
            0.5,
        )

        actual_raw = self.safe_float(
            reflection.get("actual_outcome"),
            0.0,
        )

        wisdom_score = self.clamp(
            self.safe_float(
                reflection.get("wisdom_score"),
                0.5,
            )
        )

        model = 1 if probability >= 0.5 else 0
        wisdom = 1 if wisdom_score >= 0.5 else 0
        reality = 1 if actual_raw >= 0.5 else 0

        model_reality = model == reality
        wisdom_reality = wisdom == reality
        model_wisdom = model == wisdom
        three_way = model == wisdom == reality

        broken = []

        if not model_reality:
            broken.append("MODEL")

        if not wisdom_reality:
            broken.append("WISDOM")

        state = self._state(model, wisdom, reality)

        confidence = self.clamp(
            self.safe_float(
                reflection.get("model_confidence"),
                0.0,
            )
        )

        agreement = self.clamp(
            self.safe_float(
                reflection.get("evidence_agreement"),
                0.0,
            )
        )

        strength = self.clamp(
            self.safe_float(
                reflection.get("evidence_strength"),
                0.0,
            )
        )

        prediction_error = self.clamp(
            self.safe_float(
                reflection.get("prediction_error"),
                abs(probability - reality),
            )
        )

        reflection_score = self.clamp(
            self.safe_float(
                reflection.get("reflection_score"),
                0.0,
            )
        )

        case_id = (
            reflection.get("id")
            or reflection.get("case_id")
            or reflection.get("event_id")
            or f"reflection_{index + 1}"
        )

        return {
            "index": index,
            "case_id": str(case_id),

            "MODEL": model,
            "WISDOM": wisdom,
            "REALITY": reality,

            "model_reality": model_reality,
            "wisdom_reality": wisdom_reality,
            "model_wisdom": model_wisdom,
            "three_way": three_way,

            "broken_paths": broken,
            "state": state,

            "confidence": confidence,
            "evidence_agreement": agreement,
            "evidence_strength": strength,
            "prediction_error": prediction_error,
            "reflection_score": reflection_score,
        }

    @staticmethod
    def _state(model, wisdom, reality):

        signature = f"M{model}W{wisdom}R{reality}"

        names = {
            "M1W1R1": "FULL_CONVERGENCE",
            "M1W0R1": "WISDOM_DIVERGENCE",
            "M0W1R1": "MODEL_DIVERGENCE",
            "M0W0R1": "DUAL_DIVERGENCE",

            "M1W1R0": "JOINT_FALSE_CONVERGENCE",
            "M1W0R0": "MODEL_REALITY_SPLIT",
            "M0W1R0": "WISDOM_REALITY_SPLIT",
            "M0W0R0": "FULL_NEGATIVE_CONSENSUS",
        }

        return names.get(signature, signature)

    # ============================================================
    # BASIC STRUCTURE
    # ============================================================

    def basic_structure(self, cases):

        n = len(cases)

        return {
            "test": "BASIC_STRUCTURE",
            "cases": n,
            "full_convergence_rate": self.mean(
                [c["three_way"] for c in cases]
            ),
            "model_reality_rate": self.mean(
                [c["model_reality"] for c in cases]
            ),
            "wisdom_reality_rate": self.mean(
                [c["wisdom_reality"] for c in cases]
            ),
            "model_wisdom_rate": self.mean(
                [c["model_wisdom"] for c in cases]
            ),
            "states": dict(
                Counter(c["state"] for c in cases)
            ),
        }

    # ============================================================
    # PATH SPECIALIZATION
    # ============================================================

    def path_specialization(self, cases):

        model_correct = [
            c for c in cases if c["model_reality"]
        ]

        wisdom_correct = [
            c for c in cases if c["wisdom_reality"]
        ]

        model_only = [
            c for c in cases
            if c["model_reality"] and not c["wisdom_reality"]
        ]

        wisdom_only = [
            c for c in cases
            if c["wisdom_reality"] and not c["model_reality"]
        ]

        both_correct = [
            c for c in cases
            if c["model_reality"] and c["wisdom_reality"]
        ]

        both_wrong = [
            c for c in cases
            if not c["model_reality"]
            and not c["wisdom_reality"]
        ]

        n = len(cases)

        return {
            "test": "PATH_SPECIALIZATION",
            "model_correct": len(model_correct),
            "wisdom_correct": len(wisdom_correct),
            "model_only": len(model_only),
            "wisdom_only": len(wisdom_only),
            "both_correct": len(both_correct),
            "both_wrong": len(both_wrong),

            "model_reality_rate":
                len(model_correct) / n if n else 0.0,

            "wisdom_reality_rate":
                len(wisdom_correct) / n if n else 0.0,

            "model_only_rate":
                len(model_only) / n if n else 0.0,

            "wisdom_only_rate":
                len(wisdom_only) / n if n else 0.0,

            "model_only_cases":
                [c["case_id"] for c in model_only],

            "wisdom_only_cases":
                [c["case_id"] for c in wisdom_only],
        }

    # ============================================================
    # FIRST BREAK
    # ============================================================

    def first_break(self, cases):

        counts = Counter()

        for c in cases:
            if not c["broken_paths"]:
                counts["NONE"] += 1
            else:
                # First break is determined by the ordered diagnostic
                # path hierarchy, not by numerical magnitude.
                counts[c["broken_paths"][0]] += 1

        failures = sum(
            v for k, v in counts.items()
            if k != "NONE"
        )

        dominant = None

        if failures:
            candidates = [
                (k, v)
                for k, v in counts.items()
                if k != "NONE"
            ]
            candidates.sort(
                key=lambda x: (-x[1], x[0])
            )
            dominant = candidates[0][0]

        return {
            "test": "FIRST_BREAK",
            "counts": dict(counts),
            "failure_cases": failures,
            "dominant_break_path": dominant,
        }

    # ============================================================
    # STATE TRANSITIONS
    # ============================================================

    def state_transitions(self, cases):

        transitions = Counter()

        for a, b in zip(cases, cases[1:]):
            transitions[
                f"{a['state']} -> {b['state']}"
            ] += 1

        return {
            "test": "STATE_TRANSITIONS",
            "transition_count": sum(
                transitions.values()
            ),
            "unique_transitions": len(transitions),
            "transitions": dict(transitions),
        }

    # ============================================================
    # PATH TRANSITIONS
    # ============================================================

    def path_transitions(self, cases):

        transitions = Counter()

        for a, b in zip(cases, cases[1:]):

            left = (
                f"M{a['MODEL']}"
                f"W{a['WISDOM']}"
                f"R{a['REALITY']}"
            )

            right = (
                f"M{b['MODEL']}"
                f"W{b['WISDOM']}"
                f"R{b['REALITY']}"
            )

            transitions[f"{left} -> {right}"] += 1

        return {
            "test": "PATH_TRANSITIONS",
            "transitions": dict(transitions),
        }

    # ============================================================
    # PRECURSOR ANALYSIS
    # ============================================================

    def precursor_analysis(self, cases):

        events = []

        for i in range(1, len(cases)):

            previous = cases[i - 1]
            current = cases[i]

            newly_diverged = (
                current["three_way"]
                is False
                and previous["three_way"] is True
            )

            if not newly_diverged:
                continue

            events.append({
                "from_case": previous["case_id"],
                "to_case": current["case_id"],

                "previous_state":
                    previous["state"],

                "current_state":
                    current["state"],

                "previous_confidence":
                    previous["confidence"],

                "current_confidence":
                    current["confidence"],

                "confidence_delta":
                    current["confidence"]
                    - previous["confidence"],

                "previous_evidence_agreement":
                    previous["evidence_agreement"],

                "current_evidence_agreement":
                    current["evidence_agreement"],

                "agreement_delta":
                    current["evidence_agreement"]
                    - previous["evidence_agreement"],

                "previous_evidence_strength":
                    previous["evidence_strength"],

                "current_evidence_strength":
                    current["evidence_strength"],

                "strength_delta":
                    current["evidence_strength"]
                    - previous["evidence_strength"],

                "broken_paths":
                    current["broken_paths"],
            })

        return {
            "test": "PRECURSOR_ANALYSIS",
            "new_divergence_events": len(events),
            "events": events,
        }

    # ============================================================
    # RECONVERGENCE
    # ============================================================

    def reconvergence_analysis(self, cases):

        events = []

        for i in range(1, len(cases)):

            previous = cases[i - 1]
            current = cases[i]

            if (
                not previous["three_way"]
                and current["three_way"]
            ):
                events.append({
                    "from_case":
                        previous["case_id"],
                    "to_case":
                        current["case_id"],
                    "from_state":
                        previous["state"],
                    "to_state":
                        current["state"],
                })

        return {
            "test": "RECONVERGENCE_EVENTS",
            "events": events,
            "event_count": len(events),
            "divergence_to_convergence":
                len(events),
        }

    # ============================================================
    # PERSISTENCE
    # ============================================================

    def persistence(self, cases):

        convergence_transitions = 0
        convergence_following = 0

        divergence_transitions = 0
        divergence_following = 0

        for a, b in zip(cases, cases[1:]):

            if a["three_way"]:
                convergence_transitions += 1
                if b["three_way"]:
                    convergence_following += 1

            else:
                divergence_transitions += 1
                if not b["three_way"]:
                    divergence_following += 1

        return {
            "test": "STATE_PERSISTENCE",

            "convergence_transition_count":
                convergence_transitions,

            "convergence_following_convergence":
                convergence_following,

            "convergence_persistence_rate":
                (
                    convergence_following
                    / convergence_transitions
                    if convergence_transitions
                    else 0.0
                ),

            "divergence_transition_count":
                divergence_transitions,

            "divergence_following_divergence":
                divergence_following,

            "divergence_persistence_rate":
                (
                    divergence_following
                    / divergence_transitions
                    if divergence_transitions
                    else 0.0
                ),
        }

    # ============================================================
    # CONDITIONING
    # ============================================================

    def conditioning(self, cases):

        if not cases:
            return {
                "test": "CONDITIONING",
                "cases": 0,
            }

        agreement_median = self.median(
            [c["evidence_agreement"] for c in cases]
        )

        strength_median = self.median(
            [c["evidence_strength"] for c in cases]
        )

        confidence_median = self.median(
            [c["confidence"] for c in cases]
        )

        def group_rate(group):
            return self.mean(
                [c["three_way"] for c in group]
            )

        high_agreement = [
            c for c in cases
            if c["evidence_agreement"] >= agreement_median
        ]

        low_agreement = [
            c for c in cases
            if c["evidence_agreement"] < agreement_median
        ]

        strong = [
            c for c in cases
            if c["evidence_strength"] >= strength_median
        ]

        weak = [
            c for c in cases
            if c["evidence_strength"] < strength_median
        ]

        high_confidence = [
            c for c in cases
            if c["confidence"] >= confidence_median
        ]

        low_confidence = [
            c for c in cases
            if c["confidence"] < confidence_median
        ]

        return {
            "test": "CONDITIONING",

            "agreement_median":
                agreement_median,

            "strength_median":
                strength_median,

            "confidence_median":
                confidence_median,

            "high_agreement_cases":
                len(high_agreement),

            "high_agreement_convergence":
                group_rate(high_agreement),

            "low_agreement_cases":
                len(low_agreement),

            "low_agreement_convergence":
                group_rate(low_agreement),

            "strong_evidence_cases":
                len(strong),

            "strong_evidence_convergence":
                group_rate(strong),

            "weak_evidence_cases":
                len(weak),

            "weak_evidence_convergence":
                group_rate(weak),

            "high_confidence_cases":
                len(high_confidence),

            "high_confidence_convergence":
                group_rate(high_confidence),

            "low_confidence_cases":
                len(low_confidence),

            "low_confidence_convergence":
                group_rate(low_confidence),
        }

    # ============================================================
    # COUNTEREXAMPLE SEARCH
    # ============================================================

    def counterexamples(self, cases):

        model_breaks = [
            c for c in cases
            if not c["model_reality"]
        ]

        wisdom_breaks = [
            c for c in cases
            if not c["wisdom_reality"]
        ]

        model_only = [
            c for c in cases
            if c["model_reality"]
            and not c["wisdom_reality"]
        ]

        wisdom_only = [
            c for c in cases
            if c["wisdom_reality"]
            and not c["model_reality"]
        ]

        return {
            "test": "COUNTEREXAMPLE_SEARCH",

            "model_reality_failures":
                len(model_breaks),

            "wisdom_reality_failures":
                len(wisdom_breaks),

            "model_only_reality_cases":
                [c["case_id"] for c in model_only],

            "wisdom_only_reality_cases":
                [c["case_id"] for c in wisdom_only],

            "model_counterexample_cases":
                [c["case_id"] for c in model_breaks],

            "wisdom_counterexample_cases":
                [c["case_id"] for c in wisdom_breaks],
        }

    # ============================================================
    # EFFECT SIZE
    # ============================================================

    def effect_sizes(self, cases):

        agreement = [
            c for c in cases
            if c["model_wisdom"]
        ]

        disagreement = [
            c for c in cases
            if not c["model_wisdom"]
        ]

        agreement_conv = self.mean(
            [c["three_way"] for c in agreement]
        )

        disagreement_conv = self.mean(
            [c["three_way"] for c in disagreement]
        )

        agreement_model = self.mean(
            [c["model_reality"] for c in agreement]
        )

        disagreement_model = self.mean(
            [c["model_reality"] for c in disagreement]
        )

        return {
            "test": "EFFECT_SIZES",

            "agreement_cases":
                len(agreement),

            "disagreement_cases":
                len(disagreement),

            "agreement_convergence":
                agreement_conv,

            "disagreement_convergence":
                disagreement_conv,

            "convergence_delta":
                disagreement_conv - agreement_conv,

            "agreement_model_reality":
                agreement_model,

            "disagreement_model_reality":
                disagreement_model,

            "model_reality_delta":
                disagreement_model - agreement_model,
        }

    # ============================================================
    # PERMUTATION / NULL TEST
    # ============================================================

    def permutation_test(self, cases):

        n = len(cases)

        if n < 4:
            return {
                "test": "PERMUTATION_NULL",
                "status": "INSUFFICIENT_SAMPLE",
                "n": n,
                "permutations": 0,
            }

        observed = sum(
            c["model_reality"]
            and not c["wisdom_reality"]
            for c in cases
        )

        # Keep REALITY fixed.
        # Shuffle MODEL/WISDOM labels independently.
        models = [c["MODEL"] for c in cases]
        wisdoms = [c["WISDOM"] for c in cases]
        realities = [c["REALITY"] for c in cases]

        rng = random.Random(SEED)

        null_values = []

        for _ in range(PERMUTATIONS):

            shuffled_models = models[:]
            shuffled_wisdoms = wisdoms[:]

            rng.shuffle(shuffled_models)
            rng.shuffle(shuffled_wisdoms)

            value = sum(
                m == r and w != r
                for m, w, r in zip(
                    shuffled_models,
                    shuffled_wisdoms,
                    realities,
                )
            )

            null_values.append(value)

        extreme = sum(
            x >= observed
            for x in null_values
        )

        p_value = (
            (extreme + 1)
            / (len(null_values) + 1)
        )

        return {
            "test": "PERMUTATION_NULL",
            "status": "COMPUTED",
            "seed": SEED,
            "permutations": PERMUTATIONS,
            "observed_model_only_cases":
                observed,
            "null_mean":
                self.mean(null_values),
            "null_median":
                self.median(null_values),
            "null_max":
                max(null_values),
            "empirical_p_value":
                p_value,
            "warning":
                "Exploratory null test; not a substitute for preregistered inference.",
        }

    # ============================================================
    # CANDIDATE PHENOMENA
    # ============================================================

    def candidate_phenomena(
        self,
        cases,
        basic,
        specialization,
        first_break,
        counter,
        conditioning,
    ):

        candidates = []

        n = len(cases)

        if n == 0:
            return {
                "test": "CANDIDATE_PHENOMENA",
                "classification": "NO_DATA",
                "candidates": [],
            }

        model_rate = basic["model_reality_rate"]
        wisdom_rate = basic["wisdom_reality_rate"]

        model_only_rate = specialization[
            "model_only_rate"
        ]

        wisdom_only_rate = specialization[
            "wisdom_only_rate"
        ]

        # --------------------------------------------------------
        # MODEL REALITY ANCHOR
        # --------------------------------------------------------

        if model_rate > wisdom_rate:

            candidates.append({
                "name":
                    "MODEL_REALITY_ANCHOR",
                "description":
                    "MODEL maintains greater reality alignment than WISDOM.",
                "support_cases":
                    sum(c["model_reality"] for c in cases),
                "rate":
                    model_rate,
                "effect":
                    model_rate - wisdom_rate,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # MODEL-ONLY SPECIALIZATION
        # --------------------------------------------------------

        if model_only_rate > 0:

            candidates.append({
                "name":
                    "MODEL_ONLY_REALITY_SPECIALIZATION",
                "description":
                    "MODEL matches REALITY in cases where WISDOM does not.",
                "support_cases":
                    specialization["model_only"],
                "rate":
                    model_only_rate,
                "effect":
                    model_only_rate
                    - wisdom_only_rate,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # WISDOM ANCHOR
        # --------------------------------------------------------

        if wisdom_rate > model_rate:

            candidates.append({
                "name":
                    "WISDOM_REALITY_ANCHOR",
                "description":
                    "WISDOM maintains greater reality alignment than MODEL.",
                "support_cases":
                    sum(c["wisdom_reality"] for c in cases),
                "rate":
                    wisdom_rate,
                "effect":
                    wisdom_rate - model_rate,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # FIRST-BREAK ASYMMETRY
        # --------------------------------------------------------

        dominant = first_break[
            "dominant_break_path"
        ]

        if dominant is not None:

            dominant_count = first_break[
                "counts"
            ].get(dominant, 0)

            candidates.append({
                "name":
                    "FIRST_BREAK_ASYMMETRY",
                "description":
                    f"{dominant} is the dominant observed first-break path.",
                "support_cases":
                    dominant_count,
                "rate":
                    dominant_count / n,
                "effect":
                    dominant_count / n,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # CONDITIONAL EVIDENCE EFFECT
        # --------------------------------------------------------

        high = conditioning[
            "high_agreement_convergence"
        ]

        low = conditioning[
            "low_agreement_convergence"
        ]

        if (
            conditioning["high_agreement_cases"] > 0
            and conditioning["low_agreement_cases"] > 0
            and abs(high - low) >= 0.20
        ):

            candidates.append({
                "name":
                    "EVIDENCE_CONDITIONED_CONVERGENCE",
                "description":
                    "Three-way convergence differs materially between high- and low-agreement cases.",
                "support_cases":
                    conditioning["high_agreement_cases"]
                    + conditioning["low_agreement_cases"],
                "rate":
                    high,
                "effect":
                    high - low,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # CONFIDENCE CONDITIONING
        # --------------------------------------------------------

        high_conf = conditioning[
            "high_confidence_convergence"
        ]

        low_conf = conditioning[
            "low_confidence_convergence"
        ]

        if (
            conditioning["high_confidence_cases"] > 0
            and conditioning["low_confidence_cases"] > 0
            and abs(high_conf - low_conf) >= 0.20
        ):

            candidates.append({
                "name":
                    "CONFIDENCE_CONDITIONED_CONVERGENCE",
                "description":
                    "Three-way convergence differs materially across confidence conditions.",
                "support_cases":
                    conditioning["high_confidence_cases"]
                    + conditioning["low_confidence_cases"],
                "rate":
                    high_conf,
                "effect":
                    high_conf - low_conf,
                "status":
                    "CANDIDATE",
            })

        # --------------------------------------------------------
        # RANK
        # --------------------------------------------------------

        candidates.sort(
            key=lambda x: (
                abs(self.safe_float(x["effect"])),
                self.safe_float(x["support_cases"]),
            ),
            reverse=True,
        )

        classification = (
            "NO_CANDIDATE_PATTERN"
            if not candidates
            else "CANDIDATE_PATTERNS"
        )

        return {
            "test": "CANDIDATE_PHENOMENA",
            "classification": classification,
            "candidates": candidates,
        }

    # ============================================================
    # PHENOMENON VERDICT
    # ============================================================

    def phenomenon_verdict(
        self,
        cases,
        candidates,
        permutation,
    ):

        n = len(cases)

        if n < 3:

            return {
                "classification":
                    "PHENOMENON_NOT_YET_IDENTIFIABLE",
                "confidence":
                    "LOW",
                "reason":
                    "Historical sample is below the minimum recurrence threshold.",
            }

        if not candidates["candidates"]:

            return {
                "classification":
                    "NO_RECURRING_CANDIDATE_FOUND",
                "confidence":
                    "LOW",
                "reason":
                    "No structured candidate survived the exploratory tests.",
            }

        strongest = candidates["candidates"][0]

        support = strongest["support_cases"]

        if n >= 10 and support >= 5:

            confidence = "MODERATE"

        elif n >= 5 and support >= 3:

            confidence = "LOW_TO_MODERATE"

        else:

            confidence = "LOW"

        return {
            "classification":
                "RECURRING_CANDIDATE_PHENOMENON",

            "confidence":
                confidence,

            "strongest_candidate":
                strongest["name"],

            "support_cases":
                support,

            "sample_size":
                n,

            "permutation_status":
                permutation.get("status"),

            "permutation_p_value":
                permutation.get(
                    "empirical_p_value"
                ),

            "warning":
                "Candidate phenomenon, not causal proof. Counterexamples and independent replication remain necessary.",
        }

    # ============================================================
    # CASE DIAGNOSTICS
    # ============================================================

    def case_diagnostics(self, cases):

        output = []

        for c in cases:

            if c["three_way"]:

                diagnostic = (
                    "FULL_CONVERGENCE"
                )

            elif (
                c["model_reality"]
                and not c["wisdom_reality"]
            ):

                diagnostic = (
                    "MODEL_CORRECT_WISDOM_WRONG"
                )

            elif (
                c["wisdom_reality"]
                and not c["model_reality"]
            ):

                diagnostic = (
                    "WISDOM_CORRECT_MODEL_WRONG"
                )

            else:

                diagnostic = (
                    "BOTH_PATHS_DIVERGE_FROM_REALITY"
                )

            output.append({
                "index": c["index"],
                "case_id": c["case_id"],
                "MODEL": c["MODEL"],
                "WISDOM": c["WISDOM"],
                "REALITY": c["REALITY"],
                "state": c["state"],
                "diagnostic": diagnostic,
                "broken_paths": c["broken_paths"],
                "three_way": c["three_way"],
            })

        return output

    # ============================================================
    # FULL REPORT
    # ============================================================

    def report(self):

        cases = [
            self.analyze_case(
                reflection,
                i,
            )
            for i, reflection
            in enumerate(self.reflections)
        ]

        basic = self.basic_structure(cases)
        specialization = self.path_specialization(cases)
        first_break = self.first_break(cases)
        transitions = self.state_transitions(cases)
        path_transitions = self.path_transitions(cases)
        precursor = self.precursor_analysis(cases)
        reconvergence = self.reconvergence_analysis(cases)
        persistence = self.persistence(cases)
        conditioning = self.conditioning(cases)
        counter = self.counterexamples(cases)
        effects = self.effect_sizes(cases)
        permutation = self.permutation_test(cases)

        candidates = self.candidate_phenomena(
            cases,
            basic,
            specialization,
            first_break,
            counter,
            conditioning,
        )

        verdict = self.phenomenon_verdict(
            cases,
            candidates,
            permutation,
        )

        return {
            "engine":
                "BIRTH_EDGE_RECONVERGENCE_PHENOMENON_VALIDATOR",

            "version":
                VERSION,

            "data_source":
                self.reflection_path,

            "basic_structure":
                basic,

            "path_specialization":
                specialization,

            "first_break":
                first_break,

            "state_transitions":
                transitions,

            "path_transitions":
                path_transitions,

            "precursor_analysis":
                precursor,

            "reconvergence":
                reconvergence,

            "persistence":
                persistence,

            "conditioning":
                conditioning,

            "counterexamples":
                counter,

            "effect_sizes":
                effects,

            "permutation_null":
                permutation,

            "candidate_phenomena":
                candidates,

            "phenomenon_verdict":
                verdict,

            "case_diagnostics":
                self.case_diagnostics(cases),

            "data_integrity": {
                "historical_records":
                    len(self.reflections),

                "analyzed_cases":
                    len(cases),

                "historical_data_modified":
                    False,

                "synthetic_data_used":
                    False,

                "model_modified":
                    False,

                "trading_performed":
                    False,
            },
        }


# ================================================================
# CLI
# ================================================================

def main():

    print("=" * 76)
    print("BIRTH_EDGE RECONVERGENCE PHENOMENON VALIDATOR V1")
    print("SEARCHING FOR RECURRING UNDERLYING STRUCTURE")
    print("=" * 76)

    engine = PhenomenonValidator()

    report = engine.report()

    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
    )

    verdict = report["phenomenon_verdict"]
    basic = report["basic_structure"]
    specialization = report["path_specialization"]
    first_break = report["first_break"]
    effects = report["effect_sizes"]
    permutation = report["permutation_null"]

    print()
    print("=" * 76)
    print("PHENOMENON VALIDATION VERDICT")
    print("=" * 76)

    print(
        "CLASSIFICATION:",
        verdict["classification"],
    )

    print(
        "CONFIDENCE:",
        verdict["confidence"],
    )

    if "strongest_candidate" in verdict:
        print(
            "STRONGEST CANDIDATE:",
            verdict["strongest_candidate"],
        )

    print(
        "SAMPLE SIZE:",
        basic["cases"],
    )

    print()
    print("=" * 76)
    print("PATH REALITY ALIGNMENT")
    print("=" * 76)

    print(
        "MODEL → REALITY:",
        round(
            basic["model_reality_rate"],
            6,
        ),
    )

    print(
        "WISDOM → REALITY:",
        round(
            basic["wisdom_reality_rate"],
            6,
        ),
    )

    print(
        "MODEL-ONLY:",
        specialization["model_only"],
    )

    print(
        "WISDOM-ONLY:",
        specialization["wisdom_only"],
    )

    print()
    print("=" * 76)
    print("FIRST-BREAK ANALYSIS")
    print("=" * 76)

    print(
        "DOMINANT BREAK:",
        first_break["dominant_break_path"],
    )

    print(
        "COUNTS:",
        first_break["counts"],
    )

    print()
    print("=" * 76)
    print("DISAGREEMENT EFFECT")
    print("=" * 76)

    print(
        "AGREEMENT CONVERGENCE:",
        round(
            effects["agreement_convergence"],
            6,
        ),
    )

    print(
        "DISAGREEMENT CONVERGENCE:",
        round(
            effects["disagreement_convergence"],
            6,
        ),
    )

    print(
        "CONVERGENCE DELTA:",
        round(
            effects["convergence_delta"],
            6,
        ),
    )

    print()
    print("=" * 76)
    print("NULL / PERMUTATION TEST")
    print("=" * 76)

    print(
        "STATUS:",
        permutation["status"],
    )

    if permutation["status"] == "COMPUTED":

        print(
            "OBSERVED MODEL-ONLY:",
            permutation[
                "observed_model_only_cases"
            ],
        )

        print(
            "NULL MEAN:",
            round(
                permutation["null_mean"],
                6,
            ),
        )

        print(
            "EMPIRICAL P-VALUE:",
            round(
                permutation["empirical_p_value"],
                6,
            ),
        )

    print()
    print("=" * 76)
    print("CANDIDATE PHENOMENA")
    print("=" * 76)

    for candidate in report[
        "candidate_phenomena"
    ]["candidates"]:

        print()
        print(
            candidate["name"]
        )

        print(
            "  DESCRIPTION:",
            candidate["description"],
        )

        print(
            "  SUPPORT:",
            candidate["support_cases"],
        )

        print(
            "  RATE:",
            round(
                candidate["rate"],
                6,
            ),
        )

        print(
            "  EFFECT:",
            round(
                candidate["effect"],
                6,
            ),
        )

    print()
    print("=" * 76)
    print("PRECURSOR EVENTS")
    print("=" * 76)

    events = report[
        "precursor_analysis"
    ]["events"]

    if not events:
        print("NONE OBSERVED")
    else:
        for event in events:
            print()
            print(
                f"{event['from_case']} -> "
                f"{event['to_case']}"
            )
            print(
                "  CONFIDENCE DELTA:",
                round(
                    event["confidence_delta"],
                    6,
                ),
            )
            print(
                "  AGREEMENT DELTA:",
                round(
                    event["agreement_delta"],
                    6,
                ),
            )
            print(
                "  STRENGTH DELTA:",
                round(
                    event["strength_delta"],
                    6,
                ),
            )
            print(
                "  BROKEN PATHS:",
                event["broken_paths"],
            )

    print()
    print("=" * 76)
    print("RECONVERGENCE EVENTS")
    print("=" * 76)

    recon = report[
        "reconvergence"
    ]

    print(
        "EVENTS:",
        recon["event_count"],
    )

    for event in recon["events"]:
        print(
            f"{event['from_case']} -> "
            f"{event['to_case']}: "
            f"{event['from_state']} -> "
            f"{event['to_state']}"
        )

    print()
    print("=" * 76)
    print("COUNTEREXAMPLE SEARCH")
    print("=" * 76)

    counter = report["counterexamples"]

    print(
        "MODEL REALITY FAILURES:",
        counter["model_reality_failures"],
    )

    print(
        "WISDOM REALITY FAILURES:",
        counter["wisdom_reality_failures"],
    )

    print(
        "MODEL-ONLY CASES:",
        counter["model_only_reality_cases"],
    )

    print(
        "WISDOM-ONLY CASES:",
        counter["wisdom_only_reality_cases"],
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
            case["MODEL"],
            "WISDOM:",
            case["WISDOM"],
            "REALITY:",
            case["REALITY"],
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

    integrity = report["data_integrity"]

    print(
        "HISTORICAL RECORDS:",
        integrity["historical_records"],
    )

    print(
        "ANALYZED CASES:",
        integrity["analyzed_cases"],
    )

    print(
        "HISTORICAL DATA MODIFIED:",
        integrity["historical_data_modified"],
    )

    print(
        "SYNTHETIC DATA USED:",
        integrity["synthetic_data_used"],
    )

    print(
        "MODEL MODIFIED:",
        integrity["model_modified"],
    )

    print(
        "TRADING PERFORMED:",
        integrity["trading_performed"],
    )

    print()
    print("=" * 76)
    print("VALIDATOR COMPLETE")
    print("=" * 76)


if __name__ == "__main__":
    main()
