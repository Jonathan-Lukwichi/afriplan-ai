"""
ml — data preparation for future learned components (ADR-0004).

No model is trained here. With one labelled project a neural network would
memorise Wedela, not learn electrical drawings. What we CAN do now is turn every
CAD drawing into correctly labelled training images for free — the CAD file
already knows where each symbol is — so a CNN symbol detector can be trained the
day 5–10 reference projects exist (see ml/DATASET_CARD.md).
"""
