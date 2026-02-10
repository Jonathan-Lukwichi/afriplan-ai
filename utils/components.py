"""
AfriPlan Electrical - Premium UI Component Helpers
Reusable functions using Streamlit native components for reliability
"""

import streamlit as st


def hero_section(title: str, subtitle: str = "", badge_text: str = "", stats: list = None):
    """Create an animated hero section with title, subtitle, badge, and stats."""

    # Use container for structure
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0 3rem;">
        <div style="display: inline-block; padding: 8px 20px; border: 1px solid rgba(0,212,255,0.3);
                    border-radius: 50px; font-family: 'Rajdhani', sans-serif; font-size: 14px;
                    text-transform: uppercase; letter-spacing: 2px; color: #00D4FF;
                    background: rgba(0,212,255,0.05); margin-bottom: 1.5rem;">
            {badge_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Title using native st.markdown with styling
    st.markdown(f"""
    <h1 style="font-family: 'Orbitron', sans-serif; font-size: 3rem; font-weight: 900;
               text-align: center; line-height: 1.1; margin-bottom: 1rem;
               background: linear-gradient(135deg, #00D4FF 0%, #00FFFF 50%, #00D4FF 100%);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent;
               background-clip: text;">{title}</h1>
    """, unsafe_allow_html=True)

    if subtitle:
        st.markdown(f"""
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; color: #94a3b8;
                  text-transform: uppercase; letter-spacing: 3px; text-align: center;
                  margin-bottom: 2rem;">{subtitle}</p>
        """, unsafe_allow_html=True)

    # Stats row
    if stats:
        cols = st.columns(len(stats))
        for i, stat in enumerate(stats):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center;">
                    <div style="font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 800;
                                color: #06b6d4; text-shadow: 0 0 20px rgba(6,182,212,0.3);">
                        {stat['value']}
                    </div>
                    <div style="font-family: 'Rajdhani', sans-serif; font-size: 11px;
                                text-transform: uppercase; letter-spacing: 2px; color: #64748b;">
                        {stat['label']}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def section_header(title: str, subtitle: str = ""):
    """Create a styled section header using native components."""

    # Decorative line
    st.markdown("""
    <div style="width: 60px; height: 2px; margin: 2rem auto 1rem;
                background: linear-gradient(90deg, transparent, #00D4FF, transparent);"></div>
    """, unsafe_allow_html=True)

    # Title
    st.markdown(f"""
    <h2 style="font-family: 'Orbitron', sans-serif; font-size: 1.5rem; font-weight: 800;
               text-transform: uppercase; letter-spacing: 4px; text-align: center;
               color: #f1f5f9; margin-bottom: 0.5rem;">{title}</h2>
    """, unsafe_allow_html=True)

    if subtitle:
        st.markdown(f"""
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 14px; color: #64748b;
                  text-transform: uppercase; letter-spacing: 2px; text-align: center;">
            {subtitle}
        </p>
        """, unsafe_allow_html=True)


def glass_card(content: str):
    """Wrap content in a glassmorphism card."""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                backdrop-filter: blur(12px); border: 1px solid rgba(0,212,255,0.1);
                border-radius: 16px; padding: 1.5rem; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 10%; right: 10%; height: 2px;
                    background: linear-gradient(90deg, transparent, #00D4FF, transparent);"></div>
        {content}
    </div>
    """, unsafe_allow_html=True)


def tier_card(title: str, description: str, tags: list = None):
    """Create a project tier selection card."""

    tags_html = ""
    if tags:
        tags_html = '<div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 1rem;">'
        for tag in tags:
            tags_html += f'''<span style="padding: 4px 10px; font-family: 'Rajdhani', sans-serif;
                            font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
                            border: 1px solid rgba(6,182,212,0.3); border-radius: 4px;
                            color: #06b6d4; background: rgba(6,182,212,0.05);">{tag}</span>'''
        tags_html += '</div>'

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(15,23,42,0.7));
                backdrop-filter: blur(12px); border: 1px solid rgba(30,41,59,0.8);
                border-radius: 16px; padding: 1.5rem; min-height: 180px; position: relative;
                transition: all 0.3s ease;">
        <div style="position: absolute; top: 0; left: 20%; right: 20%; height: 2px;
                    background: linear-gradient(90deg, transparent, #00D4FF, transparent);"></div>
        <h3 style="font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700;
                   color: #00D4FF; margin-bottom: 0.8rem;">{title}</h3>
        <p style="font-family: 'Inter', sans-serif; color: #94a3b8; font-size: 14px;
                  line-height: 1.6;">{description}</p>
        {tags_html}
    </div>
    """, unsafe_allow_html=True)


def metric_card(value: str, label: str, color: str = "cyan"):
    """Create a styled metric/KPI card."""

    value_color = "#00D4FF" if color == "cyan" else "#00FFFF"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.8), rgba(15,23,42,0.6));
                border: 1px solid rgba(0,212,255,0.15); border-radius: 12px;
                padding: 1.2rem; text-align: center; position: relative;">
        <div style="position: absolute; top: 0; left: 30%; right: 30%; height: 2px;
                    background: linear-gradient(90deg, transparent, #06b6d4, transparent);"></div>
        <div style="font-family: 'Orbitron', sans-serif; font-size: 2rem; font-weight: 800;
                    color: {value_color}; text-shadow: 0 0 20px rgba(0,212,255,0.3);">
            {value}
        </div>
        <div style="font-family: 'Rajdhani', sans-serif; font-size: 12px; text-transform: uppercase;
                    letter-spacing: 2px; color: #64748b; margin-top: 0.3rem;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)


def timeline_steps(steps: list):
    """Create a horizontal timeline with steps."""

    cols = st.columns(len(steps))

    for i, step in enumerate(steps):
        with cols[i]:
            st.markdown(f"""
            <div style="text-align: center; position: relative;">
                <div style="width: 48px; height: 48px; border-radius: 50%; margin: 0 auto 0.8rem;
                            background: linear-gradient(135deg, #00D4FF, #0099FF);
                            display: flex; align-items: center; justify-content: center;
                            box-shadow: 0 0 20px rgba(0,212,255,0.3);">
                    <span style="font-family: 'Orbitron', sans-serif; font-weight: 800;
                                 font-size: 1rem; color: #0a0e1a;">{step['number']}</span>
                </div>
                <div style="font-family: 'Rajdhani', sans-serif; font-weight: 600; font-size: 13px;
                            text-transform: uppercase; letter-spacing: 1px; color: #f1f5f9;">
                    {step['title']}
                </div>
                <div style="font-family: 'Inter', sans-serif; font-size: 11px; color: #64748b;
                            margin-top: 4px;">
                    {step['description']}
                </div>
            </div>
            """, unsafe_allow_html=True)


def premium_footer():
    """Create the premium styled footer."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem; margin-top: 2rem;
                border-top: 1px solid rgba(30,41,59,0.5);">
        <p style="font-family: 'Orbitron', sans-serif; font-weight: 700; color: #00D4FF;
                  margin-bottom: 0.5rem;">AFRIPLAN ELECTRICAL</p>
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 12px; color: #475569;
                  letter-spacing: 1px;">
            Built for South Africa | SANS Compliant | Professional Quotations
        </p>
        <p style="font-family: 'Rajdhani', sans-serif; font-size: 12px; color: #475569;
                  margin-top: 0.5rem;">
            2025 | Powered by Streamlit
        </p>
    </div>
    """, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = ""):
    """Create a page header for inner pages."""

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(17,24,39,0.9), rgba(15,23,42,0.7));
                backdrop-filter: blur(12px); padding: 2rem; border-radius: 16px;
                border: 1px solid rgba(0,212,255,0.1); margin-bottom: 1.5rem;
                position: relative; overflow: hidden;">
        <div style="position: absolute; top: 0; left: 10%; right: 10%; height: 2px;
                    background: linear-gradient(90deg, transparent, #00D4FF, transparent);"></div>
        <h1 style="font-family: 'Orbitron', sans-serif; font-size: 1.8rem; font-weight: 800;
                   color: #00D4FF; margin: 0 0 0.5rem 0;">{title}</h1>
        <p style="font-family: 'Rajdhani', sans-serif; color: #64748b; font-size: 14px;
                  text-transform: uppercase; letter-spacing: 2px; margin: 0;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


def loading_animation():
    """Show a loading animation."""
    st.markdown("""
    <div style="display: flex; gap: 8px; justify-content: center; padding: 2rem;">
        <span style="width: 12px; height: 12px; border-radius: 50%; background: #00D4FF;
                     animation: pulse 1.4s ease-in-out infinite;"></span>
        <span style="width: 12px; height: 12px; border-radius: 50%; background: #00D4FF;
                     animation: pulse 1.4s ease-in-out infinite 0.2s;"></span>
        <span style="width: 12px; height: 12px; border-radius: 50%; background: #00D4FF;
                     animation: pulse 1.4s ease-in-out infinite 0.4s;"></span>
    </div>
    """, unsafe_allow_html=True)


def success_toast(message: str):
    """Show a styled success message."""
    st.success(message)
