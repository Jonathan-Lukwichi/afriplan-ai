"""
AfriPlan Electrical - Premium UI Component Helpers
Reusable functions for creating futuristic styled components
"""

import streamlit as st


def hero_section(title: str, subtitle: str = "", badge_text: str = "", stats: list = None):
    """
    Create an animated hero section with title, subtitle, badge, and stats.

    Args:
        title: Main title (will have shimmer effect)
        subtitle: Subtitle text
        badge_text: Text for the floating badge
        stats: List of dicts with 'value' and 'label' keys
    """
    stats_html = ""
    if stats:
        stats_items = "".join([
            f'''<div class="stat-item">
                <span class="stat-number">{s['value']}</span>
                <span class="stat-label">{s['label']}</span>
            </div>'''
            for s in stats
        ])
        stats_html = f'<div class="hero-stats">{stats_items}</div>'

    badge_html = f'<div class="hero-badge">{badge_text}</div>' if badge_text else ""
    subtitle_html = f'<p class="hero-subtitle">{subtitle}</p>' if subtitle else ""

    st.markdown(f"""
    <div class="hero-section">
        <div class="hero-content">
            {badge_html}
            <h1 class="hero-title">{title}</h1>
            {subtitle_html}
            {stats_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "", icon: str = ""):
    """
    Create a styled section header with decorative lines.

    Args:
        title: Section title
        subtitle: Optional subtitle
        icon: Optional emoji/icon
    """
    icon_html = f'<div class="section-icon">{icon}</div>' if icon else ""
    subtitle_html = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""

    st.markdown(f"""
    <div class="section-header">
        <div class="section-line"></div>
        {icon_html}
        <h2 class="section-title">{title}</h2>
        {subtitle_html}
    </div>
    """, unsafe_allow_html=True)


def glass_card(content: str, extra_class: str = ""):
    """
    Wrap content in a glassmorphism card.

    Args:
        content: HTML content for the card
        extra_class: Additional CSS classes
    """
    st.markdown(f"""
    <div class="glass-card {extra_class}">
        {content}
    </div>
    """, unsafe_allow_html=True)


def tier_card(title: str, description: str, icon: str = "", tags: list = None):
    """
    Create a project tier selection card.

    Args:
        title: Tier name (e.g., "Residential")
        description: Tier description
        icon: Emoji or icon
        tags: List of tag strings
    """
    icon_html = f'<div class="tier-icon">{icon}</div>' if icon else ""

    tags_html = ""
    if tags:
        tags_items = "".join([f'<span class="tag">{tag}</span>' for tag in tags])
        tags_html = f'<div class="tier-tags">{tags_items}</div>'

    st.markdown(f"""
    <div class="tier-card">
        {icon_html}
        <h3>{title}</h3>
        <p>{description}</p>
        {tags_html}
    </div>
    """, unsafe_allow_html=True)


def metric_card(value: str, label: str, color: str = "amber"):
    """
    Create a styled metric/KPI card.

    Args:
        value: The metric value
        label: The metric label
        color: Color theme ('amber' or 'cyan')
    """
    color_style = "color: #f59e0b;" if color == "amber" else "color: #06b6d4;"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="{color_style}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def timeline_steps(steps: list):
    """
    Create an animated horizontal timeline.

    Args:
        steps: List of dicts with 'number', 'title', and 'description' keys
    """
    steps_html = "".join([
        f'''<div class="timeline-step">
            <div class="step-number">{s['number']}</div>
            <div class="step-title">{s['title']}</div>
            <div class="step-desc">{s['description']}</div>
        </div>'''
        for s in steps
    ])

    st.markdown(f"""
    <div class="timeline">
        {steps_html}
    </div>
    """, unsafe_allow_html=True)


def premium_footer():
    """Create the premium styled footer."""
    st.markdown("""
    <div class="premium-footer">
        <p><span class="brand">AFRIPLAN ELECTRICAL</span></p>
        <p>Built for South Africa | SANS Compliant | Professional Quotations</p>
        <p>2025 | Powered by Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


def loading_animation():
    """Show a loading animation."""
    st.markdown("""
    <div class="loading-pulse">
        <span></span>
        <span></span>
        <span></span>
    </div>
    """, unsafe_allow_html=True)


def success_toast(message: str):
    """Show a styled success message."""
    st.markdown(f"""
    <div class="success-toast">
        <span style="font-size: 20px;">&#10003;</span>
        <span style="font-family: 'Rajdhani', sans-serif; font-weight: 600; color: #10b981;">
            {message}
        </span>
    </div>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = ""):
    """
    Create a page header (simplified hero for inner pages).

    Args:
        title: Page title
        subtitle: Page subtitle
        icon: Optional emoji
    """
    icon_html = f"{icon} " if icon else ""

    st.markdown(f"""
    <div class="main-header">
        <h1>{icon_html}{title}</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)
