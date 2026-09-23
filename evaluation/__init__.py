"""
evaluation — ground truth, item taxonomy, the layered BOQ network, and the
frozen scorer.

A READ-ONLY layer, like `scoring/` and `sourcing/`: it consumes
`agent.shared.BillOfQuantities` and reference data under `data/projects/`.
Neither pipeline may import it (tests/architecture enforces this).
"""
