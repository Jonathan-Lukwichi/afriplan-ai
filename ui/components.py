"""
Reusable UI primitives for v6.1's blueprint-architectural pages.
Pure HTML + the CSS classes defined in ui/styles.py.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import streamlit as st


# ─── Page header (for inner pages) ────────────────────────────────────

def page_header(*, step: str, title: str, subtitle: str = "") -> None:
    """A two-line page header with a step eyebrow and optional subtitle."""
    sub_html = f"<p>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="afp-page-header">
          <div class="afp-step">{step}</div>
          <h1>{title}</h1>
          {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Hero (welcome page only) ─────────────────────────────────────────

def hero(*, eyebrow: str, title_html: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="afp-hero">
          <div class="afp-hero-inner">
            <div class="afp-hero-eyebrow">{eyebrow}</div>
            <h1>{title_html}</h1>
            <p>{subtitle}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Value card ───────────────────────────────────────────────────────

def value_cards(cards: Iterable[Tuple[str, str, str]]) -> None:
    """
    Render a row of value cards.

    Each card is (icon, title, body). icon is a short emoji or unicode glyph.
    """
    cards_list = list(cards)
    cols = st.columns(len(cards_list))
    for col, (icon, title, body) in zip(cols, cards_list):
        with col:
            st.markdown(
                f"""
                <div class="afp-card">
                  <div class="afp-card-icon">{icon}</div>
                  <h3>{title}</h3>
                  <p>{body}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ─── Step strip (How it works) ────────────────────────────────────────

def step_strip(steps: Iterable[Tuple[str, str, str]]) -> None:
    """
    Each step is (number, title, body). Renders a 4-cell horizontal strip.
    """
    cells = "".join(
        f"""
        <div class="afp-step-cell">
          <span class="afp-step-num">STEP {num}</span>
          <h4>{title}</h4>
          <p>{body}</p>
        </div>
        """
        for num, title, body in steps
    )
    st.markdown(f'<div class="afp-step-strip">{cells}</div>', unsafe_allow_html=True)


# ─── Section divider ──────────────────────────────────────────────────

def rule(*, strong: bool = False) -> None:
    cls = "afp-rule-strong" if strong else "afp-rule"
    st.markdown(f"<hr class='{cls}'/>", unsafe_allow_html=True)


# ─── Footer ───────────────────────────────────────────────────────────

def footer() -> None:
    st.markdown(
        """
        <div class="afp-footer">
          AFRIPLAN ELECTRICAL · v6.1 · DUAL-PIPELINE · SANS 10142-1:2017
        </div>
        """,
        unsafe_allow_html=True,
    )


# ─── Inline metric ────────────────────────────────────────────────────

def metric(label: str, value: str) -> str:
    """Returns the HTML for a metric — caller renders inside a container."""
    return (
        '<div class="afp-metric">'
        f'<span class="afp-metric-label">{label}</span>'
        f'<span class="afp-metric-value">{value}</span>'
        "</div>"
    )


# ─── Eyebrow text ─────────────────────────────────────────────────────

def eyebrow(text: str) -> None:
    st.markdown(f'<div class="afp-eyebrow">{text}</div>', unsafe_allow_html=True)
