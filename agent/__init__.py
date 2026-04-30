"""
agent — AfriPlan Electrical v6.1 dual-pipeline package.

Public sub-packages:
    agent.shared          types both pipelines emit
    agent.pdf_pipeline    vision-LLM PDF → BoQ
    agent.dxf_pipeline    deterministic DXF → BoQ
    agent.comparison      read-only cross-pipeline diff (consumed by UI only)

The independence rule: agent.pdf_pipeline and agent.dxf_pipeline must
never import each other, and neither may import agent.comparison.
See tests/architecture/test_independence.py.
"""

__version__ = "6.1.0"
