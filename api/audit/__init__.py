"""
audit — commercial audit features over any Bill of Quantities.

    boq_rules    arithmetic / missing rates / duplicates / roll-ups / companions
    sufficiency  which drawings give a complete vs partial BOQ, what to request
    completer    add fitted derived items (boxes, chasing, conduit, wire…) that
                 pipelines never calculate — tagged INFERRED, never silent

READ-ONLY layer: imports agent.shared, core and evaluation; no pipeline imports
it (tests/architecture enforces this).
"""
