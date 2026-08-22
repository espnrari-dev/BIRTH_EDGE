#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$HOME/BIRTH_EDGE"
MINER="$ROOT/aegis_rule_miner.py"
BACKUP="$ROOT/aegis_rule_miner.pre_compositional.$(date +%Y%m%d_%H%M%S).py"

cd "$ROOT"

if [ ! -f "$MINER" ]; then
    echo "ERROR: $MINER not found"
    exit 1
fi

cp "$MINER" "$BACKUP"

cat >> "$MINER" <<'PY'

# ============================================================================
# BIRTH_EDGE COMPOSITIONAL DISCOVERY UPGRADE
# ============================================================================
#
# Extends the existing architecture without removing its original API.
#
# New hypothesis language:
#
#   A
#   A AND B
#   A AND B AND C
#   A OR B
#   (A AND B) OR C
#   (A OR B) AND C
#   (A AND B) OR (C AND D)
#
# Existing Predicate / Rule objects remain valid.
# Existing extract_features / FEATURES remain valid.
# ============================================================================

from dataclasses import dataclass
from typing import Tuple, Sequence, List
import math


@dataclass(frozen=True)
class CompositeRule:
    """
    Boolean expression composed of primitive Rules / CompositeRules.

    op:
        AND -> every child must be true
        OR  -> at least one child must be true
    """
    op: str
    children: Tuple[object, ...]

    def evaluate(self, values):
        if self.op == "AND":
            return all(child.evaluate(values) for child in self.children)

        if self.op == "OR":
            return any(child.evaluate(values) for child in self.children)

        raise ValueError(f"Unknown composite operator: {self.op}")

    @property
    def complexity(self):
        total = 1
        for child in self.children:
            total += getattr(child, "complexity", 1)
        return total

    def to_string(self):
        joiner = f" {self.op} "
        rendered = []

        for child in self.children:
            s = child.to_string()
            if isinstance(child, CompositeRule):
                s = "(" + s + ")"
            rendered.append(s)

        return joiner.join(rendered)


def _primitive_rules(cols, active):
    """
    Generate the original single-feature predicate language.
    """
    out = []

    for f in active:
        values = cols[f]

        for t in _thresholds(values):
            for op in (">", "<"):
                pred = tuple(
                    x > t if op == ">" else x < t
                    for x in values
                )

                out.append(
                    (
                        Predicate(f, op, t),
                        pred
                    )
                )

    return out


def _expr_mask(expr, rows):
    """
    Evaluate an expression against rows.
    """
    masks = []

    for row in rows:
        values = extract_features(row)
        masks.append(bool(expr.evaluate(values)))

    return tuple(masks)


def _score_expression(expr, rows, labels):
    """
    Score a complete expression using the existing metric system.
    """
    pred = _expr_mask(expr, rows)

    acc, bal, prec = _metrics(pred, labels)

    support = _support(pred)

    complexity = getattr(expr, "complexity", 1)

    penalty = 0.012 * max(0, complexity - 1)

    if support < 0.05:
        penalty += (0.05 - support) * 2.0

    score = (
        0.45 * acc
        + 0.40 * bal
        + 0.15 * prec
        - penalty
    )

    return score, acc, bal, prec


def _canonical_expression_key(expr):
    return expr.to_string()


def _beam_expand(expressions, rows, labels, beam_width=32):
    """
    Expand the current beam with AND and OR compositions.

    This is deliberately bounded so the architecture gains expressive
    power without exploding combinatorially.
    """
    candidates = list(expressions)

    base = list(expressions)

    for i in range(len(base)):
        for j in range(i + 1, len(base)):
            a = base[i]
            b = base[j]

            if a.to_string() == b.to_string():
                continue

            # ---------------------------------------------------------------
            # AND composition
            # ---------------------------------------------------------------
            and_expr = CompositeRule(
                "AND",
                (a, b)
            )

            candidates.append(and_expr)

            # ---------------------------------------------------------------
            # OR composition
            # ---------------------------------------------------------------
            or_expr = CompositeRule(
                "OR",
                (a, b)
            )

            candidates.append(or_expr)

    scored = []

    seen = set()

    for expr in candidates:
        key = _canonical_expression_key(expr)

        if key in seen:
            continue

        seen.add(key)

        score, acc, bal, prec = _score_expression(
            expr,
            rows,
            labels
        )

        scored.append(
            (
                score,
                bal,
                acc,
                prec,
                getattr(expr, "complexity", 1),
                key,
                expr
            )
        )

    scored.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            -x[2],
            -x[3],
            x[4],
            x[5]
        )
    )

    return scored[:beam_width]


def _discover_compositional(rows, seed=None):
    """
    Compositional structural discovery.

    Unlike the original _discover(), this searches beyond the hard-coded
    two-predicate AND ceiling.
    """
    data = list(rows)

    if len(data) < 20 or not FEATURES:
        return None, 0.0

    names, cols, labels = _matrix(data)

    active = [
        f
        for f in names
        if len(set(cols[f])) >= 2
    ]

    if not active:
        return None, 0.0

    primitive = _primitive_rules(cols, active)

    if not primitive:
        return None, 0.0

    initial = []

    for pred_obj, pred in primitive:
        acc, bal, prec = _metrics(pred, labels)

        support = _support(pred)

        penalty = 0.0

        if support < 0.05:
            penalty += (0.05 - support) * 2.0

        score = (
            0.45 * acc
            + 0.40 * bal
            + 0.15 * prec
            - penalty
        )

        initial.append(
            (
                score,
                bal,
                acc,
                prec,
                1,
                pred_obj.to_string(),
                Rule((pred_obj,))
            )
        )

    initial.sort(
        key=lambda x: (
            -x[0],
            -x[1],
            -x[2],
            -x[3],
            x[5]
        )
    )

    # Start from a wider primitive beam than the original top-24 cutoff.
    beam = [
        x[-1]
        for x in initial[:48]
    ]

    best = None
    best_tuple = None

    # ------------------------------------------------------------------------
    # Search depth 1..4.
    #
    # This allows up to four primitive conditions in useful compositions,
    # including OR branches.
    # ------------------------------------------------------------------------
    for depth in range(1, 5):

        scored = []

        for expr in beam:
            score, acc, bal, prec = _score_expression(
                expr,
                data,
                labels
            )

            scored.append(
                (
                    score,
                    bal,
                    acc,
                    prec,
                    getattr(expr, "complexity", 1),
                    expr.to_string(),
                    expr
                )
            )

        scored.sort(
            key=lambda x: (
                -x[0],
                -x[1],
                -x[2],
                -x[3],
                x[4],
                x[5]
            )
        )

        if scored:
            candidate = scored[0]

            if (
                best_tuple is None
                or candidate[:5] > best_tuple[:5]
            ):
                best_tuple = candidate

        if depth == 4:
            break

        expanded = _beam_expand(
            beam,
            data,
            labels,
            beam_width=32
        )

        beam = [
            item[-1]
            for item in expanded
        ]

    if best_tuple is None:
        return None, 0.0

    score, bal, acc, prec, complexity, text, best = best_tuple

    # Preserve the original anti-majority-class gate.
    if bal < 0.55:
        return None, bal

    return best, acc


def evolve_rule(
    rows,
    generations=60,
    population_size=100,
    max_depth=5
):
    """
    Compatibility-preserving public entry point.

    The old parameters are retained because external callers may depend
    on them, but structural search is now performed by the compositional
    beam search.
    """
    del generations, population_size

    data = list(rows)

    state = random.getstate()

    try:
        seed = state[1][0]
    except Exception:
        seed = 0

    return _discover_compositional(data, seed)


def _discover(rows, seed):
    """
    Replace the old depth-2 discovery implementation.
    """
    return _discover_compositional(rows, seed)


def evaluate_rule(expr, rows):
    """
    Evaluate both primitive Rule and CompositeRule expressions.
    """
    labels = [
        bool(r["pumped"])
        for r in rows
    ]

    pred = [
        bool(
            expr.evaluate(
                extract_features(r)
            )
        )
        for r in rows
    ]

    acc, bal, precision = _metrics(
        pred,
        labels
    )

    return {
        "accuracy": acc,
        "balanced_accuracy": bal,
        "positive_precision": precision,
    }


def rule_features(expr):
    """
    Recursively recover all features used by an expression.
    """
    if isinstance(expr, Rule):
        return sorted({
            p.feature
            for p in expr.predicates
        })

    if isinstance(expr, CompositeRule):
        found = set()

        for child in expr.children:
            found.update(
                rule_features(child)
            )

        return sorted(found)

    return []


# ============================================================================
# END COMPOSITIONAL DISCOVERY UPGRADE
# ============================================================================

PY

python -m py_compile "$MINER"

echo
echo "================================================================"
echo "BIRTH_EDGE COMPOSITIONAL DISCOVERY INSTALLED"
echo "================================================================"
echo "Miner : $MINER"
echo "Backup: $BACKUP"
echo
echo "New capabilities:"
echo "  * arbitrary multi-condition AND"
echo "  * OR discovery"
echo "  * nested AND/OR compositions"
echo "  * recursive rule_features()"
echo "  * existing API preserved"
echo "================================================================"
