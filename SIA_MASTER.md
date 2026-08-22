# SYSTEMS INTELLIGENCE ARCHITECTURE (SIA)
## An Evidence-Driven Practical Curriculum for Building Adaptive Autonomous Systems
### Origin Case Study: BIRTH_EDGE / SHOGUN / T-PRAO / AEGIS lineage - Royriquez Gates

**Dual Purpose - Locked:**
- For others: SIA teaches people how to build, interrogate, and extend adaptive autonomous systems
- For you: SIA becomes formalization of body of work already produced and framework for next generation architecture

**Core Rule:** Study concepts because they explain systems you have built. Reverse conventional learn theory → eventually build into: build → encounter problem → learn theory → reconstruct → integrate → test → discover.

**Three Loops - Spine of Curriculum:**

Core educational loop: THEORY → RECONSTRUCTION → INTEGRATION → DISCOVERY
Core engineering loop: PERCEPTION → STATE → MEMORY → LEARNING → REASONING → DECISION → ACTION → FEEDBACK → ADAPTATION
Core evidence loop: INPUT → VERSION → CONFIGURATION → EXECUTION → OUTPUT → HASH → INTERPRETATION

Educational = how you learn, Engineering = what you build, Evidence = how you prove.

---

## KNOWN GAPS - Pedagogical Feature (Not Weakness)

This works. This works under these conditions. This has not been established yet. This is a known limitation. This is the next engineering target.

1. EVM holder analysis placeholder: filters.py:74 variance = (int(liq) % 7000) / 1000.0 → holder_score = 15.0 + variance (random)
2. EVM tax analysis placeholder: filters.py:88 return 12 + (liq % 3000)/1000.0 (random)
3. Duplicated wisdom_rules: 105 dupes → 9 after dedup (idempotency lesson)
4. run_learning_cycle() not wired into live loop in main.py - dual() only calls birth_filtered_loop + ipo_loop, learning only manual
5. Autonomous trading not yet integrated - execution.py exists but not connected

Functioning system simultaneously operational and unfinished = evidence-driven engineering.

---

## Controlled Causal Test — V3 (Renamed from irrefutable v3)

Teach distinction:

TEST INVALID = experiment did not execute (V2 TypeError: the JSON object must be str, bytes or bytearray, not dict - worker received list[dict] but did json.loads(x) on already dict, both arms crashed before prediction, parent printed verdict on empty output)

BEHAVIOR NOT DEMONSTRATED = experiment executed correctly and found no effect

V2 failure is required case study, not hidden.

Four separate pieces of evidence:
1. Immediate adaptation: same clone prediction BEFORE training → train H_A → prediction AFTER, if changes training affects state
2. Opposite-history effect: Clone A → H_A, Clone B → H_B, same future inputs, A prediction ≠ B prediction (strongest behavioral evidence)
3. Persistence: train → save/commit → destroy process → fresh Python process → load model → same future input, survives process boundary = persistent adaptation not in-memory mutation
4. Decision-path causality: changed learned state reaches operational decision (decision_engine.py) not disconnected artifact

---

## Educational Progression - Coder → Architect

LEVEL 0 Learn to build.
LEVEL 1 Learn to architect.
LEVEL 2 Learn to make systems adapt.
LEVEL 3 Learn to make them operate autonomously.
LEVEL 4 Learn to make them persistent and self-monitoring.
LEVEL 5 Learn to experimentally determine whether claimed behavior actually exists.
LEVEL 6 Learn to invent architectures.
LEVEL 7 Learn to conduct independent research.
LEVEL 8 Become an architect capable of producing an original, reproducible system.

---

## Capstone: THE GATES AUTONOMOUS INTELLIGENCE PLATFORM

Not chatbot. Must contain and prove interaction of:

PERCEPTION
↓
STATE
↓
MEMORY
↓
LEARNING
↓
REASONING
↓
DECISION
↓
ACTION
↓
FEEDBACK
↓
ADAPTATION

BIRTH_EDGE = market-intelligence implementation
AEGIS = scientific-discovery implementation
SHOGUN = autonomous/cybernetic implementation
T-PRAO = persistent-organism implementation
VERITY/AETHER = conversational/cognitive interface

Turns curriculum from "Here are some programming courses" into "Here is a methodology for building and experimentally validating intelligent systems."

AEGIS → SHOGUN → T-PRAO → BIRTH_EDGE lineage demonstrates evolution through successive approximation, not perfect first design.
