#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"
OUT="$ROOT/logs/evidence/level9/CLAUDE_L9_EVIDENCE_PACKAGE_$(date +%Y%m%d_%H%M%S).txt"

LATEST_LOG="$(ls -t "$ROOT"/logs/evidence/level9/L9_RUN_*.log 2>/dev/null | head -1)"
LATEST_JSON="$(ls -t "$ROOT"/logs/evidence/level9/L9_MECHANISM_RECOVERY_*.json 2>/dev/null | head -1)"

if [ -z "${LATEST_LOG:-}" ]; then
    echo "ERROR: No L9 run log found."
    exit 1
fi

{
cat <<'HEADER'
==============================================================================
BIRTH_EDGE — L9 MECHANISM RECOVERY
INDEPENDENT ADVERSARIAL REVIEW PACKAGE
==============================================================================

PURPOSE

This package is provided for independent skeptical review.

The reviewer is explicitly asked to challenge the conclusions, identify
alternative explanations, detect methodological weaknesses, and distinguish
what the experiment demonstrates from claims that go beyond the evidence.

No appeal to reputation, credentials, popularity, or external accolades
should be used to evaluate the result.

The primary question tested was:

"Does repeated discovery recover a common underlying decision mechanism?"

==============================================================================

EXPERIMENT CONFIGURATION
==============================================================================

Miner              : UNMODIFIED
Definitive test    : UNMODIFIED
Discovery seeds    : 50
Train sizes        : [100, 200, 400, 800]
Common test N      : 5000
Shifted tests      : 3

==============================================================================

REVIEW INSTRUCTIONS
==============================================================================

Evaluate the evidence on its own merits.

Specifically attempt to determine:

1. Whether the discovery runs are genuinely independent.
2. Whether the common held-out population is genuinely held out.
3. Whether the 50 discoveries are meaningfully independent searches.
4. Whether 95.2599% mean pairwise agreement constitutes functional
   convergence under the stated methodology.
5. Whether the 39/50 dominant functional cluster is statistically or
   methodologically meaningful.
6. Whether feature convergence could arise from the data-generating process
   rather than discovery of a mechanism.
7. Whether the label-shuffle null is an adequate control.
8. Whether distribution-shift testing materially strengthens the conclusion.
9. Whether permutation disruption demonstrates feature dependence.
10. Whether any leakage, selection bias, implementation artifact, or hidden
    coupling could explain the result.
11. What claims are directly supported by the experiment.
12. What stronger claims are NOT established by this experiment.

Do not downgrade the experiment merely because it lacks tests that were never
part of the stated L9 objective. Identify those as limitations or extensions
rather than silently redefining the objective.

==============================================================================
PRIMARY L9 RESULT
==============================================================================

L9 VERDICT:

L9-FUNCTIONAL-CONVERGENCE-SUPPORTED

FINAL FORENSIC SUMMARY:

Successful discoveries : 50/50
Mean common accuracy   : 0.968484
Mean balanced accuracy : 0.885849
Pairwise mean agreement: 0.952599
Pairwise minimum       : 0.723800
Label-null mean        : 0.502954
Null separation        : 0.382895
Functional clusters    : 5

Dominant functional cluster:

39/50 discoveries

Agreement threshold:

0.95

==============================================================================
RAW L9 RUN LOG
==============================================================================

HEADER

cat "$LATEST_LOG"

if [ -n "${LATEST_JSON:-}" ] && [ -f "$LATEST_JSON" ]; then
    echo
    echo
    echo "=============================================================================="
    echo "MACHINE-READABLE L9 JSON REPORT"
    echo "=============================================================================="
    echo
    cat "$LATEST_JSON"
fi

cat <<'FOOTER'

==============================================================================
END OF PRIMARY EVIDENCE
==============================================================================

IMPORTANT:

The evidence supports the specific experimental finding that repeated
independent discovery runs in this experiment produced strongly convergent
functional behavior.

The experiment does NOT, by itself, establish:

- universal uniqueness of the recovered mechanism;
- that every possible discovery algorithm would reconverge;
- that the mechanism is causal in the real world;
- that the result automatically generalizes to unrelated datasets;
- that the methodology is universally superior to all existing approaches.

Those are separate claims requiring separate evidence.

The correct question for review is therefore not:

"Is this impressive?"

It is:

"Does the reported experiment actually support its stated L9 conclusion,
and if not, exactly where does the inference fail?"

==============================================================================
END
==============================================================================
FOOTER

} > "$OUT"

echo
echo "============================================================"
echo "CLAUDE EVIDENCE PACKAGE CREATED"
echo "============================================================"
echo
echo "FILE:"
echo "$OUT"
echo
echo "SIZE:"
du -h "$OUT" | awk '{print $1}'
echo
echo "SOURCE LOG:"
echo "$LATEST_LOG"
echo
[ -n "${LATEST_JSON:-}" ] && echo "SOURCE JSON:" && echo "$LATEST_JSON"
echo
echo "Copy the package with:"
echo
echo "termux-share \"$OUT\""
echo
