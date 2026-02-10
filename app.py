"""
AfriPlan AI — African Architecture AI Platform (Prototype)
A Maket.ai-style floorplan generator adapted for African housing context.
Built with Streamlit by JLWanalytics.
"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import random
import io
import json
from datetime import datetime
import plotly.graph_objects as go
import io

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AfriPlan AI — Architecture Intelligence",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
    
    .stApp { background-color: #0B1120; }
    
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 24px 30px;
        border-radius: 12px;
        border-left: 4px solid #F59E0B;
        margin-bottom: 24px;
    }
    .main-header h1 {
        color: #F59E0B;
        font-size: 28px;
        font-weight: 800;
        margin: 0;
    }
    .main-header p {
        color: #94A3B8;
        font-size: 14px;
        margin: 4px 0 0;
    }
    
    .metric-card {
        background: #1E293B;
        border-radius: 10px;
        padding: 16px;
        border-top: 3px solid #F59E0B;
        text-align: center;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 800;
        color: #F59E0B;
    }
    .metric-label {
        font-size: 12px;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .bq-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .bq-table th {
        background: #1E293B;
        color: #F59E0B;
        padding: 10px;
        text-align: left;
        font-weight: 700;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .bq-table td {
        padding: 8px 10px;
        border-bottom: 1px solid #1E293B;
        color: #CBD5E1;
    }
    .bq-table tr:hover td {
        background: #1E293B44;
    }
    
    .section-title {
        color: #F59E0B;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1E293B;
    }
    
    div[data-testid="stSidebar"] {
        background: #0F172A;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #F59E0B, #D97706) !important;
        color: #0B1120 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-size: 14px !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #D97706, #B45309) !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SOUTH AFRICAN MATERIAL DATABASE (in ZAR)
# ─────────────────────────────────────────────
SA_MATERIALS = {
    "Cement (50kg bag)": {"unit": "bag", "price_zar": 100.0},
    "Concrete Block (15cm)": {"unit": "block", "price_zar": 15.0},
    "Concrete Block (20cm)": {"unit": "block", "price_zar": 20.0},
    "Rebar (12mm, 12m)": {"unit": "bar", "price_zar": 300.0},
    "Rebar (8mm, 12m)": {"unit": "bar", "price_zar": 160.0},
    "Roof Sheeting (3m)": {"unit": "sheet", "price_zar": 250.0},
    "Sand (7m³ truck)": {"unit": "truck", "price_zar": 1750.0},
    "Stone/Gravel (7m³ truck)": {"unit": "truck", "price_zar": 2300.0},
    "Floor Tiles (m²)": {"unit": "m²", "price_zar": 150.0},
    "Paint (20L bucket)": {"unit": "bucket", "price_zar": 500.0},
    "Structural Timber (6m)": {"unit": "piece", "price_zar": 200.0},
    "Interior Door": {"unit": "set", "price_zar": 800.0},
    "Exterior Door (Steel)": {"unit": "set", "price_zar": 2500.0},
    "Aluminium Window (1.2x1.0m)": {"unit": "set", "price_zar": 1500.0},
    "Plumbing (Basic Bathroom Set)": {"unit": "set", "price_zar": 4500.0},
    "Electrical (per point)": {"unit": "point", "price_zar": 250.0},
    "General Labour (per day)": {"unit": "day", "price_zar": 250.0},
}

# ─────────────────────────────────────────────
# ELECTRICAL MATERIAL DATABASE - SA 2024/2025
# ─────────────────────────────────────────────

# 1.1 Electrical Cables
ELECTRICAL_CABLES = {
    "surfix_1.5mm_100m": {"desc": "SURFIX 1.5mm 3-core (lighting)", "unit": "roll", "price": 1850, "amps": 14},
    "surfix_2.5mm_100m": {"desc": "SURFIX 2.5mm 3-core (power)", "unit": "roll", "price": 2950, "amps": 20},
    "surfix_4mm_100m": {"desc": "SURFIX 4mm 3-core", "unit": "roll", "price": 4500, "amps": 27},
    "surfix_6mm_100m": {"desc": "SURFIX 6mm 3-core (stove)", "unit": "roll", "price": 6800, "amps": 35},
    "earth_wire_10mm": {"desc": "Earth wire 10mm green/yellow", "unit": "roll", "price": 1200, "amps": 0},
}

# 1.2 DB Boards and Protection
ELECTRICAL_DB = {
    "db_8_way": {"desc": "DB Board 8-way flush", "unit": "each", "price": 750},
    "db_12_way": {"desc": "DB Board 12-way flush", "unit": "each", "price": 1100},
    "db_16_way": {"desc": "DB Board 16-way flush", "unit": "each", "price": 1500},
    "db_24_way": {"desc": "DB Board 24-way flush", "unit": "each", "price": 2200},
    "main_switch_40a": {"desc": "Main switch 40A DP", "unit": "each", "price": 280},
    "main_switch_60a": {"desc": "Main switch 60A DP", "unit": "each", "price": 350},
    "main_switch_80a": {"desc": "Main switch 80A DP", "unit": "each", "price": 450},
    "cb_10a": {"desc": "Circuit breaker 10A SP", "unit": "each", "price": 65},
    "cb_16a": {"desc": "Circuit breaker 16A SP", "unit": "each", "price": 65},
    "cb_20a": {"desc": "Circuit breaker 20A SP", "unit": "each", "price": 70},
    "cb_32a": {"desc": "Circuit breaker 32A SP", "unit": "each", "price": 85},
    "elcb_63a": {"desc": "Earth leakage 63A 30mA", "unit": "each", "price": 950},
    "surge_arrester": {"desc": "Surge arrester Type 2", "unit": "each", "price": 1800},
}

# 1.3 Switches and Sockets
ELECTRICAL_ACCESSORIES = {
    "switch_1_lever": {"desc": "Light switch 1-lever", "unit": "each", "price": 45},
    "switch_2_lever": {"desc": "Light switch 2-lever", "unit": "each", "price": 65},
    "switch_3_lever": {"desc": "Light switch 3-lever", "unit": "each", "price": 85},
    "switch_4_lever": {"desc": "Light switch 4-lever", "unit": "each", "price": 105},
    "switch_2_way": {"desc": "2-way switch", "unit": "each", "price": 55},
    "switch_dimmer": {"desc": "Dimmer switch", "unit": "each", "price": 180},
    "socket_single": {"desc": "Socket outlet single", "unit": "each", "price": 55},
    "socket_double": {"desc": "Socket outlet double", "unit": "each", "price": 75},
    "socket_double_switched": {"desc": "Socket double switched", "unit": "each", "price": 95},
    "socket_usb": {"desc": "Socket with USB ports", "unit": "each", "price": 250},
    "isolator_stove": {"desc": "Stove isolator 45A", "unit": "each", "price": 250},
    "isolator_geyser": {"desc": "Geyser isolator 20A", "unit": "each", "price": 120},
    "isolator_aircon": {"desc": "Aircon isolator 20A", "unit": "each", "price": 150},
}

# 1.4 Light Fittings
ELECTRICAL_LIGHTS = {
    "downlight_led_9w": {"desc": "LED downlight 9W", "unit": "each", "price": 85, "lumens": 800},
    "downlight_led_12w": {"desc": "LED downlight 12W", "unit": "each", "price": 120, "lumens": 1000},
    "downlight_led_15w": {"desc": "LED downlight 15W", "unit": "each", "price": 150, "lumens": 1200},
    "batten_led_18w": {"desc": "LED batten 18W 600mm", "unit": "each", "price": 180, "lumens": 1800},
    "batten_led_36w": {"desc": "LED batten 36W 1200mm", "unit": "each", "price": 280, "lumens": 3600},
    "bulkhead_ip65": {"desc": "LED bulkhead IP65", "unit": "each", "price": 250},
    "floodlight_20w": {"desc": "LED floodlight 20W", "unit": "each", "price": 350},
    "floodlight_50w": {"desc": "LED floodlight 50W", "unit": "each", "price": 550},
    "sensor_pir": {"desc": "PIR motion sensor", "unit": "each", "price": 180},
}

# 1.5 Conduits and Sundries
ELECTRICAL_CONDUIT = {
    "conduit_20mm": {"desc": "PVC conduit 20mm x 4m", "unit": "length", "price": 35},
    "conduit_25mm": {"desc": "PVC conduit 25mm x 4m", "unit": "length", "price": 55},
    "conduit_32mm": {"desc": "PVC conduit 32mm x 4m", "unit": "length", "price": 75},
    "flexi_20mm": {"desc": "Flexible conduit 20mm", "unit": "meter", "price": 25},
    "junction_box": {"desc": "Junction box", "unit": "each", "price": 15},
    "junction_box_ip65": {"desc": "Junction box IP65", "unit": "each", "price": 45},
    "saddle_20mm": {"desc": "Saddle clip 20mm", "unit": "each", "price": 2},
    "saddle_25mm": {"desc": "Saddle clip 25mm", "unit": "each", "price": 3},
    "wall_box": {"desc": "Flush wall box", "unit": "each", "price": 18},
    "ceiling_rose": {"desc": "Ceiling rose DCL", "unit": "each", "price": 35},
    "earth_spike": {"desc": "Earth spike 1.5m copper", "unit": "each", "price": 180},
    "earth_bar": {"desc": "Earth bar 12-way", "unit": "each", "price": 95},
    "cable_tie_100": {"desc": "Cable ties 100mm (100)", "unit": "pack", "price": 25},
    "tape_insulation": {"desc": "Insulation tape", "unit": "roll", "price": 15},
}

# 1.6 Labour Rates (SA 2024/2025)
ELECTRICAL_LABOUR = {
    "light_point": {"desc": "Light point complete", "unit": "point", "price": 280},
    "power_point": {"desc": "Power point complete", "unit": "point", "price": 320},
    "stove_circuit": {"desc": "Stove circuit complete", "unit": "each", "price": 1800},
    "geyser_circuit": {"desc": "Geyser circuit complete", "unit": "each", "price": 1500},
    "aircon_circuit": {"desc": "Aircon circuit complete", "unit": "each", "price": 1200},
    "db_installation": {"desc": "DB board installation", "unit": "each", "price": 1500},
    "earth_installation": {"desc": "Earth system installation", "unit": "each", "price": 800},
    "coc_inspection": {"desc": "COC inspection & certificate", "unit": "each", "price": 2200},
    "fault_finding": {"desc": "Fault finding per hour", "unit": "hour", "price": 450},
    "electrical_rate": {"desc": "Electrician hourly rate", "unit": "hour", "price": 380},
}

# 1.7 Room Electrical Requirements (SANS 10142 Based)
ROOM_ELECTRICAL_REQUIREMENTS = {
    "Living Room": {"lights": 3, "plugs": 6, "special": []},
    "Bedroom": {"lights": 2, "plugs": 4, "special": ["2-way switch"]},
    "Main Bedroom": {"lights": 3, "plugs": 6, "special": ["2-way switch", "aircon prep"]},
    "Kitchen": {"lights": 4, "plugs": 8, "special": ["stove", "extractor"]},
    "Bathroom": {"lights": 2, "plugs": 1, "special": ["extractor", "shaver socket"]},
    "Toilet": {"lights": 1, "plugs": 0, "special": []},
    "Garage": {"lights": 2, "plugs": 4, "special": ["garage door motor"]},
    "Study": {"lights": 2, "plugs": 6, "special": []},
    "Dining Room": {"lights": 2, "plugs": 4, "special": []},
    "Passage": {"lights": 2, "plugs": 1, "special": ["2-way switch"]},
    "Patio": {"lights": 2, "plugs": 2, "special": ["weatherproof", "sensor"]},
    "Laundry": {"lights": 1, "plugs": 3, "special": ["washing machine"]},
    "Store Room": {"lights": 1, "plugs": 1, "special": []},
    "Pool Area": {"lights": 2, "plugs": 1, "special": ["pool pump", "weatherproof"]},
}

# ─────────────────────────────────────────────
# ROOM TYPES — South African residential context
# ─────────────────────────────────────────────
ROOM_PRESETS = {
    "Living Room": {"min_area": 16, "max_area": 30, "color": "#3B82F6", "label": "Living", "windows": 2, "doors": 1},
    "Bedroom": {"min_area": 10, "max_area": 16, "color": "#10B981", "label": "Bed", "windows": 1, "doors": 1},
    "Kitchen": {"min_area": 8, "max_area": 14, "color": "#F59E0B", "label": "Kitchen", "windows": 1, "doors": 1},
    "Bathroom": {"min_area": 4, "max_area": 8, "color": "#06B6D4", "label": "Bath", "windows": 1, "doors": 1},
    "Toilet": {"min_area": 2, "max_area": 4, "color": "#8B5CF6", "label": "WC", "windows": 0, "doors": 1},
    "Passage": {"min_area": 4, "max_area": 10, "color": "#64748B", "label": "Passage", "windows": 0, "doors": 0},
    "Patio": {"min_area": 6, "max_area": 15, "color": "#F97316", "label": "Patio", "windows": 0, "doors": 1},
    "Dining Room": {"min_area": 10, "max_area": 18, "color": "#EC4899", "label": "Dining", "windows": 1, "doors": 1},
    "Study": {"min_area": 8, "max_area": 14, "color": "#14B8A6", "label": "Study", "windows": 1, "doors": 1},
    "Garage": {"min_area": 15, "max_area": 25, "color": "#78716C", "label": "Garage", "windows": 0, "doors": 1},
}

# ─────────────────────────────────────────────
# FLOORPLAN GENERATION ALGORITHM
# ─────────────────────────────────────────────
class FloorplanGenerator:
    """
    Constraint-based floorplan generator using recursive space partitioning.
    This is the algorithmic approach — in production, this would be replaced/augmented
    by a trained GAN or diffusion model.
    """
    
    def __init__(self, plot_width, plot_length, rooms, seed=None):
        self.plot_width = plot_width
        self.plot_length = plot_length
        self.rooms = rooms  # list of {"name": ..., "type": ..., "target_area": ...}
        self.placed_rooms = []
        self.rng = random.Random(seed)
        
        # Building footprint (with setbacks)
        self.setback = 1.5  # meters from plot boundary
        self.build_width = plot_width - 2 * self.setback
        self.build_length = plot_length - 2 * self.setback
        
        # Wall thickness
        self.wall = 0.20  # 20cm parpaing walls
    
    def generate(self):
        """Generate a floorplan using recursive subdivision."""
        self.placed_rooms = []
        
        # Available building area
        available = {
            "x": self.setback,
            "y": self.setback,
            "w": self.build_width,
            "h": self.build_length,
        }
        
        # Sort rooms: largest first for better packing
        sorted_rooms = sorted(self.rooms, key=lambda r: r["target_area"], reverse=True)
        
        # Use treemap-style subdivision
        self._subdivide(available, sorted_rooms)
        
        return self.placed_rooms
    
    def _subdivide(self, space, rooms):
        """Recursively subdivide space to place rooms."""
        if not rooms:
            return
        
        if len(rooms) == 1:
            room = rooms[0]
            preset = ROOM_PRESETS.get(room["type"], ROOM_PRESETS["Living Room"])
            self.placed_rooms.append({
                "name": room["name"],
                "type": room["type"],
                "x": space["x"] + self.wall,
                "y": space["y"] + self.wall,
                "w": space["w"] - 2 * self.wall,
                "h": space["h"] - 2 * self.wall,
                "color": preset["color"],
                "label": room["name"],
                "windows": preset["windows"],
                "doors": preset["doors"],
                "area": (space["w"] - 2 * self.wall) * (space["h"] - 2 * self.wall),
            })
            return
        
        # Calculate total area of remaining rooms
        total_area = sum(r["target_area"] for r in rooms)
        
        # Split rooms into two groups
        mid = len(rooms) // 2
        # Add some randomness to the split point
        if len(rooms) > 3:
            mid = self.rng.randint(max(1, mid - 1), min(len(rooms) - 1, mid + 1))
        
        group1 = rooms[:mid]
        group2 = rooms[mid:]
        
        area1 = sum(r["target_area"] for r in group1)
        ratio = area1 / total_area if total_area > 0 else 0.5
        
        # Add slight randomness to ratio for variety
        ratio = max(0.25, min(0.75, ratio + self.rng.uniform(-0.05, 0.05)))
        
        # Decide split direction based on space aspect ratio
        if space["w"] >= space["h"]:
            # Split horizontally (left/right)
            split = space["x"] + space["w"] * ratio
            space1 = {"x": space["x"], "y": space["y"], "w": split - space["x"], "h": space["h"]}
            space2 = {"x": split, "y": space["y"], "w": space["x"] + space["w"] - split, "h": space["h"]}
        else:
            # Split vertically (top/bottom)
            split = space["y"] + space["h"] * ratio
            space1 = {"x": space["x"], "y": space["y"], "w": space["w"], "h": split - space["y"]}
            space2 = {"x": space["x"], "y": split, "w": space["w"], "h": space["y"] + space["h"] - split}
        
        self._subdivide(space1, group1)
        self._subdivide(space2, group2)
    
    def generate_variations(self, n=4):
        """Generate multiple layout variations."""
        variations = []
        for i in range(n):
            self.rng = random.Random(i * 42 + self.rng.randint(0, 10000))
            # Shuffle room order for different layouts
            shuffled = self.rooms.copy()
            self.rng.shuffle(shuffled)
            self.rooms = shuffled
            plan = self.generate()
            variations.append(plan.copy())
        return variations


# ─────────────────────────────────────────────
# VISUALIZATION
# ─────────────────────────────────────────────
def draw_floorplan(rooms, plot_w, plot_l, title="Plan", setback=1.5, show_dimensions=True):
    """Draw a 2D floorplan using matplotlib."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8 * plot_l / plot_w))
    fig.patch.set_facecolor('#0B1120')
    ax.set_facecolor('#0F172A')
    
    # Draw plot boundary
    plot_rect = patches.Rectangle(
        (0, 0), plot_w, plot_l,
        linewidth=2, edgecolor='#334155', facecolor='#0F172A', linestyle='--'
    )
    ax.add_patch(plot_rect)
    
    # Draw building footprint
    build_rect = patches.Rectangle(
        (setback, setback), plot_w - 2*setback, plot_l - 2*setback,
        linewidth=2.5, edgecolor='#E2E8F0', facecolor='#1E293B'
    )
    ax.add_patch(build_rect)
    
    # Draw rooms
    for room in rooms:
        # Room fill
        room_rect = patches.Rectangle(
            (room["x"], room["y"]), room["w"], room["h"],
            linewidth=1.5, edgecolor='#E2E8F0',
            facecolor=room["color"] + "33",  # transparent fill
        )
        ax.add_patch(room_rect)
        
        # Room label
        cx = room["x"] + room["w"] / 2
        cy = room["y"] + room["h"] / 2
        area = room["w"] * room["h"]
        
        # Room name
        ax.text(cx, cy + 0.3, room["label"],
                ha='center', va='center', fontsize=9, fontweight='bold',
                color=room["color"])
        
        # Area
        ax.text(cx, cy - 0.4, f'{area:.1f} m²',
                ha='center', va='center', fontsize=7, color='#94A3B8')
        
        # Dimensions
        if show_dimensions:
            ax.text(cx, room["y"] + 0.15, f'{room["w"]:.1f}m',
                    ha='center', va='bottom', fontsize=6, color='#475569')
            ax.text(room["x"] + 0.1, cy, f'{room["h"]:.1f}m',
                    ha='left', va='center', fontsize=6, color='#475569', rotation=90)
        
        # Draw door indicator (small arc)
        if room.get("doors", 0) > 0:
            door_x = room["x"] + room["w"] * 0.4
            door_y = room["y"]
            door_arc = patches.Arc(
                (door_x, door_y), 0.8, 0.8,
                angle=0, theta1=0, theta2=90,
                linewidth=1.5, edgecolor='#F59E0B'
            )
            ax.add_patch(door_arc)
        
        # Draw window indicator (blue line on exterior wall)
        if room.get("windows", 0) > 0:
            # Place window on the top wall
            win_x = room["x"] + room["w"] * 0.3
            win_y = room["y"] + room["h"]
            ax.plot([win_x, win_x + 1.0], [win_y, win_y],
                    linewidth=3, color='#3B82F6', solid_capstyle='round')
    
    # Title
    ax.set_title(title, color='#F59E0B', fontsize=14, fontweight='bold', pad=15)
    
    # Plot dimensions annotation
    ax.text(plot_w / 2, -0.5, f'{plot_w:.1f}m', ha='center', va='top',
            fontsize=10, color='#64748B', fontweight='bold')
    ax.text(-0.5, plot_l / 2, f'{plot_l:.1f}m', ha='right', va='center',
            fontsize=10, color='#64748B', fontweight='bold', rotation=90)
    
    # North arrow
    ax.annotate('N', xy=(plot_w - 0.5, plot_l - 0.5),
                fontsize=12, fontweight='bold', color='#F59E0B',
                ha='center', va='center')
    ax.annotate('', xy=(plot_w - 0.5, plot_l - 0.2),
                xytext=(plot_w - 0.5, plot_l - 0.8),
                arrowprops=dict(arrowstyle='->', color='#F59E0B', lw=2))
    
    ax.set_xlim(-1, plot_w + 1)
    ax.set_ylim(-1, plot_l + 1)
    ax.set_aspect('equal')
    ax.axis('off')
    
    plt.tight_layout()
    return fig


def draw_3d_floorplan(rooms, wall_height=3.0):
    """Draw a 3D floorplan using Plotly."""
    fig_data = []
    annotations = []

    for room in rooms:
        x, y, w, h = room['x'], room['y'], room['w'], room['h']
        
        # Define the 8 vertices of the room box
        vertices = {
            'x': [x, x, x+w, x+w, x, x, x+w, x+w],
            'y': [y, y+h, y+h, y, y, y+h, y+h, y],
            'z': [0, 0, 0, 0, wall_height, wall_height, wall_height, wall_height]
        }

        # Create a Mesh3d trace for the room
        mesh = go.Mesh3d(
            x=vertices['x'], y=vertices['y'], z=vertices['z'],
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            color=room['color'],
            opacity=0.6,
            hoverinfo='name',
            name=room['name']
        )
        fig_data.append(mesh)

        # Add room label annotation
        annotations.append(
            dict(
                showarrow=False,
                x=x + w / 2,
                y=y + h / 2,
                z=wall_height + 0.5,
                text=f"<b>{room['name']}</b>",
                xanchor="center",
                yanchor="middle",
                font=dict(color="white", size=12)
            )
        )

    # Create layout
    layout = go.Layout(
        title=dict(text="3D Plan View", x=0.5, font=dict(color='#F59E0B')),
        scene=dict(
            xaxis=dict(title='Width (m)', backgroundcolor="#0B1120", gridcolor="#1E293B", showbackground=True, zerolinecolor="#1E293B"),
            yaxis=dict(title='Length (m)', backgroundcolor="#0B1120", gridcolor="#1E293B", showbackground=True, zerolinecolor="#1E293B"),
            zaxis=dict(title='Height (m)', backgroundcolor="#0B1120", gridcolor="#1E293B", showbackground=True, zerolinecolor="#1E293B", range=[0, wall_height + 1]),
            annotations=annotations,
            camera_eye=dict(x=1.5, y=1.5, z=1.5)
        ),
        paper_bgcolor='#0B1120',
        plot_bgcolor='#0B1120',
        margin=dict(l=0, r=0, b=0, t=40)
    )

    fig = go.Figure(data=fig_data, layout=layout)
    return fig


# ─────────────────────────────────────────────
# BILL OF QUANTITIES CALCULATOR
# ─────────────────────────────────────────────
def calculate_bq(rooms, wall_height=3.0):
    """Calculate bill of quantities based on room dimensions."""
    bq = {}
    
    total_floor_area = sum(r["w"] * r["h"] for r in rooms)
    total_wall_perimeter = sum(2 * (r["w"] + r["h"]) for r in rooms)
    total_wall_area = total_wall_perimeter * wall_height
    
    num_doors = sum(r.get("doors", 1) for r in rooms)
    num_windows = sum(r.get("windows", 1) for r in rooms)
    num_rooms = len(rooms)
    
    # Blocks: ~12.5 blocks per m² of wall (20cm blocks)
    num_blocks = int(total_wall_area * 12.5)
    bq["Concrete Block (20cm)"] = {"qty": num_blocks, "unit": "block"}
    
    # Cement: ~0.5 bag per m² of wall (for mortar + plaster)
    num_cement_walls = int(total_wall_area * 0.5)
    # Cement for foundation/slab: ~0.8 bag per m² of floor
    num_cement_floor = int(total_floor_area * 0.8)
    bq["Cement (50kg bag)"] = {"qty": num_cement_walls + num_cement_floor, "unit": "bag"}
    
    # Sand: ~0.15 truckload per 10m² of wall
    num_sand_trucks = max(1, int(total_wall_area / 70))
    bq["Sand (7m³ truck)"] = {"qty": num_sand_trucks, "unit": "truck"}
    
    # Stone/Gravel: for foundation and slab
    num_gravel_trucks = max(1, int(total_floor_area / 50))
    bq["Stone/Gravel (7m³ truck)"] = {"qty": num_gravel_trucks, "unit": "truck"}
    
    # Rebar 12mm: for columns and beams (~1 bar per 3m² floor)
    num_rebar_12mm = max(4, int(total_floor_area / 3))
    bq["Rebar (12mm, 12m)"] = {"qty": num_rebar_12mm, "unit": "bar"}
    
    # Rebar 8mm: for stirrups (~1 bar per 5m² floor)
    num_rebar_8mm = max(4, int(total_floor_area / 5))
    bq["Rebar (8mm, 12m)"] = {"qty": num_rebar_8mm, "unit": "bar"}
    
    # Roof Sheeting: roof area ≈ floor area * 1.15, each sheet covers ~2.4m²
    roof_area = total_floor_area * 1.15
    num_roof_sheets = int(roof_area / 2.4)
    bq["Roof Sheeting (3m)"] = {"qty": num_roof_sheets, "unit": "sheet"}
    
    # Structural Timber: for roof structure (~1 per 2m² of roof)
    num_timber_pieces = int(roof_area / 2)
    bq["Structural Timber (6m)"] = {"qty": num_timber_pieces, "unit": "piece"}
    
    # Floor Tiles
    bq["Floor Tiles (m²)"] = {"qty": int(total_floor_area * 1.1), "unit": "m²"}  # 10% waste
    
    # Paint: ~1 bucket per 40m² of wall (2 coats)
    num_paint_buckets = max(1, int(total_wall_area * 2 / 40))
    bq["Paint (20L bucket)"] = {"qty": num_paint_buckets, "unit": "bucket"}
    
    # Doors
    bq["Interior Door"] = {"qty": max(0, num_doors - 1), "unit": "set"}
    bq["Exterior Door (Steel)"] = {"qty": 1, "unit": "set"}
    
    # Windows
    bq["Aluminium Window (1.2x1.0m)"] = {"qty": num_windows, "unit": "set"}
    
    # Plumbing (1 per wet room)
    wet_rooms = sum(1 for r in rooms if r["type"] in ["Bathroom", "Toilet", "Kitchen"])
    bq["Plumbing (Basic Bathroom Set)"] = {"qty": wet_rooms, "unit": "set"}
    
    # Electrical: ~2 points per room
    bq["Electrical (per point)"] = {"qty": num_rooms * 2, "unit": "point"}
    
    # Labour: ~2 days per m² of built area
    bq["General Labour (per day)"] = {"qty": int(total_floor_area * 2), "unit": "day"}
    
    return bq


def calculate_cost(bq):
    """Calculate total cost from BQ using SA prices in ZAR."""
    items = []
    total_zar = 0
    
    for material, data in bq.items():
        if material in SA_MATERIALS:
            mat_info = SA_MATERIALS[material]
            cost_zar = data["qty"] * mat_info["price_zar"]
            total_zar += cost_zar
            items.append({
                "material": material,
                "qty": data["qty"],
                "unit": data["unit"],
                "unit_price_zar": mat_info["price_zar"],
                "total_zar": cost_zar,
            })
    
    return items, total_zar


# ─────────────────────────────────────────────
# GENERATE PDF REPORT
# ─────────────────────────────────────────────
def generate_pdf(rooms, bq_items, total_zar, plot_w, plot_l, fig):
    """Generate a professional PDF quote."""
    from fpdf import FPDF
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 18)
            self.set_text_color(245, 158, 11)
            self.cell(0, 10, 'AfriPlan AI', new_x="LMARGIN", new_y="NEXT", align='L')
            self.set_font('Helvetica', '', 9)
            self.set_text_color(100, 116, 139)
            self.cell(0, 5, "Cost Estimate - Intelligent Architecture for South Africa", new_x="LMARGIN", new_y="NEXT")
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(8)
        
        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128)
            self.cell(0, 10, f'AfriPlan AI - Page {self.page_no()}', align='C')
    
    pdf = PDF()
    pdf.add_page()
    
    # Project Info
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, 'PROJECT INFORMATION', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, f'Plot Dimensions: {plot_w}m x {plot_l}m ({plot_w * plot_l:.0f} m2)', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f'Built Area: {sum(r["w"] * r["h"] for r in rooms):.1f} m2', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f'Number of Rooms: {len(rooms)}', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Rooms list
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'ROOM SCHEDULE', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    for r in rooms:
        pdf.cell(0, 6, f'  - {r["name"]}: {r["w"]:.1f}m x {r["h"]:.1f}m = {r["w"]*r["h"]:.1f} m2', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    # Floorplan image
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='#FFFFFF', edgecolor='none')
    img_buf.seek(0)
    pdf.image(img_buf, x=10, w=190)
    
    # BQ Table
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, 'BILL OF QUANTITIES & COST ESTIMATE', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Table header
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(30, 41, 59)
    pdf.set_text_color(245, 158, 11)
    col_widths = [80, 25, 25, 30, 30]
    headers = ['Material', 'Qty', 'Unit', 'Rate (ZAR)', 'Total (ZAR)']
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, fill=True, align='C')
    pdf.ln()
    
    # Table rows
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    for item in bq_items:
        pdf.cell(col_widths[0], 6, item["material"][:45], border=1)
        pdf.cell(col_widths[1], 6, str(item["qty"]), border=1, align='C')
        pdf.cell(col_widths[2], 6, item["unit"], border=1, align='C')
        pdf.cell(col_widths[3], 6, f'R {item["unit_price_zar"]:.2f}', border=1, align='R')
        pdf.cell(col_widths[4], 6, f'R {item["total_zar"]:,.0f}', border=1, align='R')
        pdf.ln()
    
    # Total
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(11, 17, 32)
    pdf.cell(sum(col_widths[:4]), 8, 'ESTIMATED TOTAL', border=1, fill=True, align='R')
    pdf.cell(col_widths[4], 8, f'R {total_zar:,.0f}', border=1, fill=True, align='R')
    pdf.ln(10)
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 5, 'Note: Prices are indicative and based on average market rates in Johannesburg.', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, 'A variance of +/- 15% is possible depending on material availability and supplier.', new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())


# ─────────────────────────────────────────────
# GENERATE DXF REPORT
# ─────────────────────────────────────────────
def generate_dxf(rooms, plot_w, plot_l):
    """Generate a DXF file from the floorplan."""
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    # Create a new DXF document
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Add layers
    doc.layers.add(name="Walls", color=1)  # Blue for walls
    doc.layers.add(name="Doors", color=3)  # Green for doors
    doc.layers.add(name="Windows", color=5) # Magenta for windows
    doc.layers.add(name="Text", color=7)    # White/Black for text

    # Draw plot boundary
    msp.add_lwpolyline(
        [(0, 0), (plot_w, 0), (plot_w, plot_l), (0, plot_l)],
        close=True,
        dxfattribs={"layer": "0"}
    )

    for room in rooms:
        x, y, w, h = room['x'], room['y'], room['w'], room['h']
        
        # Draw walls
        msp.add_lwpolyline(
            [(x, y), (x + w, y), (x + w, y + h), (x, y + h)],
            close=True,
            dxfattribs={"layer": "Walls"}
        )

        # Add room label
        cx = x + w / 2
        cy = y + h / 2
        area = w * h
        
        msp.add_text(
            room["name"],
            dxfattribs={
                'layer': 'Text',
                'height': 0.25,
                'style': 'OpenSans'
            }
        ).set_placement((cx, cy + 0.3), align=TextEntityAlignment.CENTER)

        msp.add_text(
            f"{area:.1f} m²",
            dxfattribs={
                'layer': 'Text',
                'height': 0.15,
                'style': 'OpenSans'
            }
        ).set_placement((cx, cy - 0.4), align=TextEntityAlignment.CENTER)

    # Prepare the DXF content as a string
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()


# ─────────────────────────────────────────────
# ELECTRICAL CALCULATION FUNCTIONS (SANS 10142)
# ─────────────────────────────────────────────

def calculate_electrical_requirements(rooms: list) -> dict:
    """
    Calculate electrical requirements from room list.
    Uses SANS 10142 standards for SA compliance.
    """
    import math

    total_lights = 0
    total_plugs = 0
    room_details = []
    dedicated_circuits = []

    for room in rooms:
        room_type = room.get("type", "Living Room")
        room_area = room.get("w", 4) * room.get("h", 4)

        # Get base requirements
        req = ROOM_ELECTRICAL_REQUIREMENTS.get(room_type, {"lights": 2, "plugs": 4, "special": []})

        # Scale for larger rooms (1 extra light per 20m², 2 extra plugs per 20m²)
        area_factor = max(1, room_area / 20)
        lights = max(req["lights"], int(req["lights"] * area_factor))
        plugs = max(req["plugs"], int(req["plugs"] * area_factor))

        total_lights += lights
        total_plugs += plugs

        room_details.append({
            "name": room.get("name", room_type),
            "type": room_type,
            "area": round(room_area, 1),
            "lights": lights,
            "plugs": plugs,
            "special": req["special"],
        })

        # Track dedicated circuits
        if "stove" in req["special"]:
            dedicated_circuits.append("stove")
        if "aircon prep" in req["special"]:
            dedicated_circuits.append("aircon")
        if "pool pump" in req["special"]:
            dedicated_circuits.append("pool_pump")

    # Always add geyser for residential
    dedicated_circuits.append("geyser")

    return {
        "total_lights": total_lights,
        "total_plugs": total_plugs,
        "room_details": room_details,
        "dedicated_circuits": list(set(dedicated_circuits)),
    }


def calculate_load_and_circuits(elec_req: dict) -> dict:
    """
    Calculate load, circuits, and DB sizing per SANS 10142.
    """
    import math

    # Load calculation (SANS 10142 diversity factors)
    light_load = elec_req["total_lights"] * 100  # 100W per point
    plug_load = elec_req["total_plugs"] * 250    # 250W per point

    # Apply diversity (50% for residential per SANS)
    diversified_load = (light_load + plug_load) * 0.5

    # Add dedicated loads (full load, no diversity)
    dedicated_load = 0
    if "stove" in elec_req["dedicated_circuits"]:
        dedicated_load += 8000  # 8kW stove
    if "geyser" in elec_req["dedicated_circuits"]:
        dedicated_load += 3000  # 3kW geyser
    if "aircon" in elec_req["dedicated_circuits"]:
        dedicated_load += 2000  # 2kW aircon
    if "pool_pump" in elec_req["dedicated_circuits"]:
        dedicated_load += 1500  # 1.5kW pool pump

    total_load_w = diversified_load + dedicated_load
    total_load_kva = total_load_w / 1000 / 0.85  # Power factor 0.85

    # Circuit calculation (SANS 10142: max 10 points per circuit)
    lighting_circuits = math.ceil(elec_req["total_lights"] / 10)
    power_circuits = math.ceil(elec_req["total_plugs"] / 10)
    dedicated_count = len(elec_req["dedicated_circuits"])

    # Total circuits = lighting + power + dedicated + main + ELCB
    total_circuits = lighting_circuits + power_circuits + dedicated_count + 2

    # DB sizing (allow 20% spare capacity)
    if total_circuits <= 6:
        db_size = "8_way"
        db_price = 750
    elif total_circuits <= 10:
        db_size = "12_way"
        db_price = 1100
    elif total_circuits <= 14:
        db_size = "16_way"
        db_price = 1500
    else:
        db_size = "24_way"
        db_price = 2200

    # Main breaker sizing
    main_current = (total_load_kva * 1000) / 230
    if main_current <= 35:
        main_size = "40A"
        main_price = 280
    elif main_current <= 55:
        main_size = "60A"
        main_price = 350
    else:
        main_size = "80A"
        main_price = 450

    return {
        "total_load_w": round(total_load_w, 0),
        "total_load_kva": round(total_load_kva, 1),
        "lighting_circuits": lighting_circuits,
        "power_circuits": power_circuits,
        "dedicated_circuits": dedicated_count,
        "total_circuits": total_circuits,
        "db_size": db_size,
        "db_price": db_price,
        "main_size": main_size,
        "main_price": main_price,
    }


def calculate_electrical_bq(elec_req: dict, circuit_info: dict) -> list:
    """
    Generate complete electrical Bill of Quantities.
    """
    bq = []

    # 1. DB Board and Protection
    bq.append({"category": "DB Board & Protection", "item": f"DB Board {circuit_info['db_size'].replace('_', ' ')}",
               "qty": 1, "unit": "each", "rate": circuit_info['db_price'],
               "total": circuit_info['db_price']})
    bq.append({"category": "DB Board & Protection", "item": f"Main Switch {circuit_info['main_size']}",
               "qty": 1, "unit": "each", "rate": circuit_info['main_price'],
               "total": circuit_info['main_price']})
    bq.append({"category": "DB Board & Protection", "item": "Earth Leakage 63A 30mA",
               "qty": 1, "unit": "each", "rate": 950, "total": 950})
    bq.append({"category": "DB Board & Protection", "item": "Surge Arrester Type 2",
               "qty": 1, "unit": "each", "rate": 1800, "total": 1800})

    # Circuit breakers
    bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 10A (lighting)",
               "qty": circuit_info['lighting_circuits'], "unit": "each", "rate": 65,
               "total": circuit_info['lighting_circuits'] * 65})
    bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 16A (power)",
               "qty": circuit_info['power_circuits'], "unit": "each", "rate": 65,
               "total": circuit_info['power_circuits'] * 65})

    # Dedicated circuit breakers
    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 32A (stove)",
                   "qty": 1, "unit": "each", "rate": 85, "total": 85})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 20A (geyser)",
                   "qty": 1, "unit": "each", "rate": 70, "total": 70})
    if "aircon" in elec_req["dedicated_circuits"]:
        bq.append({"category": "DB Board & Protection", "item": "Circuit Breaker 20A (aircon)",
                   "qty": 1, "unit": "each", "rate": 70, "total": 70})

    # 2. Cables (estimate 8m per point average)
    lighting_cable_m = elec_req["total_lights"] * 8
    power_cable_m = elec_req["total_plugs"] * 8

    lighting_rolls = max(1, int(lighting_cable_m / 100) + 1)
    power_rolls = max(1, int(power_cable_m / 100) + 1)

    bq.append({"category": "Cables", "item": "SURFIX 1.5mm 3-core (lighting)",
               "qty": lighting_rolls, "unit": "roll 100m", "rate": 1850,
               "total": lighting_rolls * 1850})
    bq.append({"category": "Cables", "item": "SURFIX 2.5mm 3-core (power)",
               "qty": power_rolls, "unit": "roll 100m", "rate": 2950,
               "total": power_rolls * 2950})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Cables", "item": "SURFIX 6mm 3-core (stove)",
                   "qty": 1, "unit": "roll 100m", "rate": 6800, "total": 6800})

    bq.append({"category": "Cables", "item": "Earth wire 10mm green/yellow",
               "qty": 1, "unit": "roll", "rate": 1200, "total": 1200})

    # 3. Conduit and Sundries
    total_points = elec_req["total_lights"] + elec_req["total_plugs"]
    conduit_lengths = total_points * 2  # 2 x 4m lengths per point

    bq.append({"category": "Conduit & Sundries", "item": "PVC Conduit 20mm x 4m",
               "qty": conduit_lengths, "unit": "length", "rate": 35,
               "total": conduit_lengths * 35})
    bq.append({"category": "Conduit & Sundries", "item": "Junction Boxes",
               "qty": total_points, "unit": "each", "rate": 15,
               "total": total_points * 15})
    bq.append({"category": "Conduit & Sundries", "item": "Saddle Clips 20mm",
               "qty": conduit_lengths * 4, "unit": "each", "rate": 2,
               "total": conduit_lengths * 4 * 2})
    bq.append({"category": "Conduit & Sundries", "item": "Earth Spike 1.5m copper",
               "qty": 1, "unit": "each", "rate": 180, "total": 180})
    bq.append({"category": "Conduit & Sundries", "item": "Earth Bar 12-way",
               "qty": 1, "unit": "each", "rate": 95, "total": 95})

    # 4. Switches and Sockets
    bq.append({"category": "Switches & Sockets", "item": "Light Switch (mixed levers)",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 55,
               "total": elec_req["total_lights"] * 55})
    bq.append({"category": "Switches & Sockets", "item": "Socket Outlet Double Switched",
               "qty": elec_req["total_plugs"], "unit": "each", "rate": 95,
               "total": elec_req["total_plugs"] * 95})
    bq.append({"category": "Switches & Sockets", "item": "Flush Wall Boxes",
               "qty": total_points, "unit": "each", "rate": 18,
               "total": total_points * 18})
    bq.append({"category": "Switches & Sockets", "item": "Ceiling Roses DCL",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 35,
               "total": elec_req["total_lights"] * 35})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Switches & Sockets", "item": "Stove Isolator 45A + Socket",
                   "qty": 1, "unit": "each", "rate": 400, "total": 400})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Switches & Sockets", "item": "Geyser Isolator 20A",
                   "qty": 1, "unit": "each", "rate": 120, "total": 120})

    # 5. Light Fittings
    bq.append({"category": "Light Fittings", "item": "LED Downlight 12W (incl)",
               "qty": elec_req["total_lights"], "unit": "each", "rate": 120,
               "total": elec_req["total_lights"] * 120})

    # 6. Labour
    bq.append({"category": "Labour", "item": "Light Points Installation",
               "qty": elec_req["total_lights"], "unit": "point", "rate": 280,
               "total": elec_req["total_lights"] * 280})
    bq.append({"category": "Labour", "item": "Power Points Installation",
               "qty": elec_req["total_plugs"], "unit": "point", "rate": 320,
               "total": elec_req["total_plugs"] * 320})
    bq.append({"category": "Labour", "item": "DB Board Installation",
               "qty": 1, "unit": "each", "rate": 1500, "total": 1500})
    bq.append({"category": "Labour", "item": "Earth System Installation",
               "qty": 1, "unit": "each", "rate": 800, "total": 800})

    if "stove" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Labour", "item": "Stove Circuit Installation",
                   "qty": 1, "unit": "each", "rate": 1800, "total": 1800})
    if "geyser" in elec_req["dedicated_circuits"]:
        bq.append({"category": "Labour", "item": "Geyser Circuit Installation",
                   "qty": 1, "unit": "each", "rate": 1500, "total": 1500})

    # 7. Compliance
    bq.append({"category": "Compliance", "item": "COC Inspection & Certificate",
               "qty": 1, "unit": "each", "rate": 2200, "total": 2200})

    return bq


def generate_electrical_pdf(elec_req: dict, circuit_info: dict, bq_items: list):
    """Generate professional electrical quotation PDF."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 15, 'ELECTRICAL INSTALLATION QUOTATION', new_x="LMARGIN", new_y="NEXT", align='C')

    # Project Info
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Quote Ref: EQ-{datetime.now().strftime('%Y%m%d%H%M')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # Summary Section
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(245, 158, 11)  # Amber
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  PROJECT SUMMARY', fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(30, 41, 59)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(95, 6, f"  Total Light Points: {elec_req['total_lights']}", new_x="RIGHT")
    pdf.cell(95, 6, f"Total Plug Points: {elec_req['total_plugs']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"  Total Load: {circuit_info['total_load_kva']} kVA", new_x="RIGHT")
    pdf.cell(95, 6, f"Main Breaker: {circuit_info['main_size']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(95, 6, f"  DB Board: {circuit_info['db_size'].replace('_', ' ')}", new_x="RIGHT")
    pdf.cell(95, 6, f"Total Circuits: {circuit_info['total_circuits']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # BQ Table Header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  BILL OF QUANTITIES', fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.cell(70, 7, ' Item', border=1, fill=True, align='L')
    pdf.cell(25, 7, 'Qty', border=1, fill=True, align='C')
    pdf.cell(25, 7, 'Unit', border=1, fill=True, align='C')
    pdf.cell(35, 7, 'Rate (R)', border=1, fill=True, align='R')
    pdf.cell(35, 7, 'Total (R)', border=1, fill=True, align='R')
    pdf.ln()

    # Table rows
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    current_category = ""

    for item in bq_items:
        if item["category"] != current_category:
            current_category = item["category"]
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 6, f" {current_category}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 8)

        pdf.cell(70, 6, f" {item['item'][:38]}", border=1, align='L')
        pdf.cell(25, 6, str(item["qty"]), border=1, align='C')
        pdf.cell(25, 6, item["unit"], border=1, align='C')
        pdf.cell(35, 6, f"{item['rate']:,.0f}", border=1, align='R')
        pdf.cell(35, 6, f"{item['total']:,.0f}", border=1, align='R')
        pdf.ln()

    # Totals
    pdf.ln(3)
    subtotal = sum(item["total"] for item in bq_items)
    vat = subtotal * 0.15
    total = subtotal + vat

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(155, 7, 'Subtotal (excl VAT):', align='R')
    pdf.cell(35, 7, f'R {subtotal:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 7, 'VAT (15%):', align='R')
    pdf.cell(35, 7, f'R {vat:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 8, 'TOTAL (incl VAT):', fill=True, align='R')
    pdf.cell(35, 8, f'R {total:,.0f}', fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # Notes
    pdf.ln(5)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.multi_cell(0, 4,
        "Notes:\n"
        "- Quote valid for 30 days from date of issue\n"
        "- Prices based on current SA market rates\n"
        "- COC Certificate included upon completion\n"
        "- Excludes builders work (chasing, making good)\n"
        "- SANS 10142 compliant installation\n"
        "- 50% deposit required to commence work"
    )

    # Footer
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 6, 'Generated by AfriPlan Electrical - www.afriplan.co.za', new_x="LMARGIN", new_y="NEXT", align='C')

    return bytes(pdf.output())


def generate_generic_electrical_pdf(bq_items: list, summary: dict, tier: str, subtype: str):
    """Generate generic electrical quotation PDF for all project types."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Header
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(30, 41, 59)
    tier_names = {"residential": "RESIDENTIAL", "commercial": "COMMERCIAL", "industrial": "INDUSTRIAL", "infrastructure": "INFRASTRUCTURE"}
    pdf.cell(0, 15, f'{tier_names.get(tier, "ELECTRICAL")} QUOTATION', new_x="LMARGIN", new_y="NEXT", align='C')

    # Project Info
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, f"Project Type: {subtype.replace('_', ' ').title()}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Date: {datetime.now().strftime('%d %B %Y')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.cell(0, 6, f"Quote Ref: {tier[:3].upper()}-{datetime.now().strftime('%Y%m%d%H%M')}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(5)

    # Summary Section
    if summary:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(245, 158, 11)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, '  PROJECT SUMMARY', fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 10)
        for key, value in summary.items():
            pdf.cell(95, 6, f"  {key}: {value}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

    # BQ Table Header
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, '  BILL OF QUANTITIES', fill=True, new_x="LMARGIN", new_y="NEXT")

    # Table header
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_fill_color(30, 41, 59)
    pdf.cell(70, 7, ' Item', border=1, fill=True, align='L')
    pdf.cell(25, 7, 'Qty', border=1, fill=True, align='C')
    pdf.cell(25, 7, 'Unit', border=1, fill=True, align='C')
    pdf.cell(35, 7, 'Rate (R)', border=1, fill=True, align='R')
    pdf.cell(35, 7, 'Total (R)', border=1, fill=True, align='R')
    pdf.ln()

    # Table rows
    pdf.set_font('Helvetica', '', 8)
    pdf.set_text_color(30, 41, 59)
    current_category = ""

    for item in bq_items:
        if item["category"] != current_category:
            current_category = item["category"]
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(190, 6, f" {current_category}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font('Helvetica', '', 8)

        pdf.cell(70, 6, f" {item['item'][:38]}", border=1, align='L')
        pdf.cell(25, 6, str(item["qty"]), border=1, align='C')
        pdf.cell(25, 6, item["unit"], border=1, align='C')
        pdf.cell(35, 6, f"{item['rate']:,.0f}", border=1, align='R')
        pdf.cell(35, 6, f"{item['total']:,.0f}", border=1, align='R')
        pdf.ln()

    # Totals
    pdf.ln(3)
    subtotal = sum(item["total"] for item in bq_items)
    vat = subtotal * 0.15
    total = subtotal + vat

    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(155, 7, 'Subtotal (excl VAT):', align='R')
    pdf.cell(35, 7, f'R {subtotal:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(155, 7, 'VAT (15%):', align='R')
    pdf.cell(35, 7, f'R {vat:,.0f}', align='R', new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(245, 158, 11)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(155, 8, 'TOTAL (incl VAT):', fill=True, align='R')
    pdf.cell(35, 8, f'R {total:,.0f}', fill=True, align='R', new_x="LMARGIN", new_y="NEXT")

    # Notes based on tier
    pdf.ln(5)
    pdf.set_text_color(100, 116, 139)
    pdf.set_font('Helvetica', 'I', 8)

    notes = {
        "residential": "Notes:\n- Quote valid for 30 days\n- SANS 10142 compliant\n- COC Certificate included\n- 50% deposit required",
        "commercial": "Notes:\n- Quote valid for 30 days\n- SANS 10142 & SANS 10400 compliant\n- COC Certificate included\n- Fire detection per SANS 10139\n- Payment terms: 30% deposit, progress payments",
        "industrial": "Notes:\n- Quote valid for 30 days\n- MHSA / SANS 10108 compliant (where applicable)\n- FAT & SAT included\n- Payment terms per contract\n- Excludes civil works unless specified",
        "infrastructure": "Notes:\n- Quote valid for 60 days\n- NRS 034 / Eskom DSD compliant\n- Per-stand costing based on typical layouts\n- Subject to site survey\n- Payment per milestone",
    }

    pdf.multi_cell(0, 4, notes.get(tier, notes["residential"]))

    # Footer
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(0, 6, 'Generated by AfriPlan Electrical - www.afriplan.co.za', new_x="LMARGIN", new_y="NEXT", align='C')

    return bytes(pdf.output())


# ─────────────────────────────────────────────
# PHASE 5: SMART COST OPTIMIZER
# ─────────────────────────────────────────────

# Supplier price variations (simulated multi-supplier database)
SUPPLIER_PRICES = {
    "budget": {
        "name": "Budget Electrical",
        "markup": 0.0,  # Base price
        "quality": 3,
        "lead_time": 7,
    },
    "standard": {
        "name": "ACDC Dynamics",
        "markup": 0.10,  # 10% higher
        "quality": 4,
        "lead_time": 3,
    },
    "premium": {
        "name": "Schneider Electric",
        "markup": 0.25,  # 25% higher
        "quality": 5,
        "lead_time": 5,
    }
}

def generate_quotation_options(bq_items: list, elec_req: dict, circuit_info: dict) -> list:
    """
    Generate 4 quotation options with different cost/quality strategies.
    Phase 5: Smart Cost Optimizer
    """
    base_material_cost = sum(item["total"] for item in bq_items if item["category"] != "Labour")
    base_labour_cost = sum(item["total"] for item in bq_items if item["category"] == "Labour")
    base_total = base_material_cost + base_labour_cost

    options = []

    # Option A: Budget - Cheapest suppliers, minimum markup
    budget_material = base_material_cost * 0.90  # 10% cheaper materials
    budget_labour = base_labour_cost * 0.95  # Slightly cheaper labour
    budget_cost = budget_material + budget_labour
    budget_markup = 0.12
    budget_selling = budget_cost * (1 + budget_markup)
    budget_profit = budget_selling - budget_cost
    options.append({
        "name": "A: Budget Friendly",
        "strategy": "Cheapest suppliers, basic quality",
        "material_cost": budget_material,
        "labour_cost": budget_labour,
        "base_cost": budget_cost,
        "markup_percent": budget_markup * 100,
        "selling_price": budget_selling,
        "profit": budget_profit,
        "profit_margin": (budget_profit / budget_selling * 100) if budget_selling > 0 else 0,
        "quality_score": 3,
        "lead_time": 7,
        "recommended": False,
        "color": "#3B82F6",  # Blue
    })

    # Option B: Best Value - Balanced cost/quality (RECOMMENDED)
    value_material = base_material_cost * 1.0  # Standard price
    value_labour = base_labour_cost * 1.0
    value_cost = value_material + value_labour
    value_markup = 0.18
    value_selling = value_cost * (1 + value_markup)
    value_profit = value_selling - value_cost
    options.append({
        "name": "B: Best Value",
        "strategy": "Balanced cost and quality",
        "material_cost": value_material,
        "labour_cost": value_labour,
        "base_cost": value_cost,
        "markup_percent": value_markup * 100,
        "selling_price": value_selling,
        "profit": value_profit,
        "profit_margin": (value_profit / value_selling * 100) if value_selling > 0 else 0,
        "quality_score": 4,
        "lead_time": 3,
        "recommended": True,
        "color": "#22C55E",  # Green
    })

    # Option C: Premium - Top quality brands
    premium_material = base_material_cost * 1.25  # 25% premium materials
    premium_labour = base_labour_cost * 1.15  # Experienced contractors
    premium_cost = premium_material + premium_labour
    premium_markup = 0.22
    premium_selling = premium_cost * (1 + premium_markup)
    premium_profit = premium_selling - premium_cost
    options.append({
        "name": "C: Premium Quality",
        "strategy": "Top-tier brands, master electricians",
        "material_cost": premium_material,
        "labour_cost": premium_labour,
        "base_cost": premium_cost,
        "markup_percent": premium_markup * 100,
        "selling_price": premium_selling,
        "profit": premium_profit,
        "profit_margin": (premium_profit / premium_selling * 100) if premium_selling > 0 else 0,
        "quality_score": 5,
        "lead_time": 5,
        "recommended": False,
        "color": "#A855F7",  # Purple
    })

    # Option D: Competitive - Lowest total to win job
    competitive_material = base_material_cost * 0.92
    competitive_labour = base_labour_cost * 0.90
    competitive_cost = competitive_material + competitive_labour
    competitive_markup = 0.10  # Lower margin
    competitive_selling = competitive_cost * (1 + competitive_markup)
    competitive_profit = competitive_selling - competitive_cost
    options.append({
        "name": "D: Competitive Bid",
        "strategy": "Win the job, volume pricing",
        "material_cost": competitive_material,
        "labour_cost": competitive_labour,
        "base_cost": competitive_cost,
        "markup_percent": competitive_markup * 100,
        "selling_price": competitive_selling,
        "profit": competitive_profit,
        "profit_margin": (competitive_profit / competitive_selling * 100) if competitive_selling > 0 else 0,
        "quality_score": 3.5,
        "lead_time": 5,
        "recommended": False,
        "color": "#F59E0B",  # Amber
    })

    return options


# ─────────────────────────────────────────────
# PHASE 6: OPERATIONS RESEARCH OPTIMIZATION
# ─────────────────────────────────────────────

def optimize_quotation_or(bq_items: list, constraints: dict = None) -> dict:
    """
    Operations Research optimization using PuLP Integer Linear Programming.
    Finds mathematically optimal supplier selection.
    """
    from pulp import LpProblem, LpMinimize, LpMaximize, LpVariable, lpSum, LpStatus, value, PULP_CBC_CMD

    constraints = constraints or {}
    min_quality = constraints.get("min_quality", 3)
    max_budget = constraints.get("max_budget", float('inf'))

    # Simulated supplier data for each item category
    suppliers = ["budget", "standard", "premium"]
    categories = list(set(item["category"] for item in bq_items))

    # Price multipliers per supplier
    price_mult = {"budget": 0.90, "standard": 1.0, "premium": 1.25}
    quality_scores = {"budget": 3, "standard": 4, "premium": 5}

    # Create optimization problem
    prob = LpProblem("Quotation_Optimizer", LpMinimize)

    # Decision variables: select supplier j for category i
    x = LpVariable.dicts("select",
                         ((cat, sup) for cat in categories for sup in suppliers),
                         cat='Binary')

    # Calculate base costs per category
    category_costs = {}
    for item in bq_items:
        cat = item["category"]
        if cat not in category_costs:
            category_costs[cat] = 0
        category_costs[cat] += item["total"]

    # Objective: Minimize total cost
    prob += lpSum(
        category_costs.get(cat, 0) * price_mult[sup] * x[cat, sup]
        for cat in categories for sup in suppliers
    ), "Total_Cost"

    # Constraint 1: One supplier per category
    for cat in categories:
        prob += lpSum(x[cat, sup] for sup in suppliers) == 1, f"One_Supplier_{cat}"

    # Constraint 2: Minimum quality score
    total_items = len(categories)
    prob += lpSum(
        quality_scores[sup] * x[cat, sup]
        for cat in categories for sup in suppliers
    ) >= min_quality * total_items, "Min_Quality"

    # Constraint 3: Budget limit (if specified)
    if max_budget < float('inf'):
        prob += lpSum(
            category_costs.get(cat, 0) * price_mult[sup] * x[cat, sup]
            for cat in categories for sup in suppliers
        ) <= max_budget, "Budget_Limit"

    # Solve
    prob.solve(PULP_CBC_CMD(msg=0))

    # Extract solution
    if LpStatus[prob.status] == "Optimal":
        selection = {}
        total_cost = 0
        total_quality = 0

        for cat in categories:
            for sup in suppliers:
                if value(x[cat, sup]) == 1:
                    selection[cat] = {
                        "supplier": sup,
                        "supplier_name": SUPPLIER_PRICES[sup]["name"],
                        "cost": category_costs.get(cat, 0) * price_mult[sup],
                        "quality": quality_scores[sup]
                    }
                    total_cost += selection[cat]["cost"]
                    total_quality += quality_scores[sup]

        return {
            "status": "optimal",
            "selection": selection,
            "total_cost": total_cost,
            "average_quality": total_quality / len(categories) if categories else 0,
            "solver_status": LpStatus[prob.status],
            "variables": len(x),
            "constraints": len(prob.constraints)
        }
    else:
        return {
            "status": "infeasible",
            "message": "No optimal solution found with given constraints",
            "solver_status": LpStatus[prob.status]
        }


# ─────────────────────────────────────────────
# PROJECT TYPE DEFINITIONS (Multi-Tier)
# ─────────────────────────────────────────────

PROJECT_TYPES = {
    "residential": {
        "name": "Residential",
        "icon": "🏠",
        "subtypes": [
            {"code": "new_house", "name": "New House Construction", "icon": "🏗️", "standards": ["SANS 10142"]},
            {"code": "renovation", "name": "Renovation & Additions", "icon": "🔧", "standards": ["SANS 10142"]},
            {"code": "solar_backup", "name": "Solar & Backup Power", "icon": "☀️", "standards": ["SANS 10142", "NRS 097"]},
            {"code": "coc_compliance", "name": "COC Compliance", "icon": "📋", "standards": ["SANS 10142"]},
            {"code": "smart_home", "name": "Smart Home", "icon": "🏠", "standards": ["SANS 10142"]},
            {"code": "security", "name": "Security Systems", "icon": "🔒", "standards": ["SANS 10142", "PSIRA"]},
            {"code": "ev_charging", "name": "EV Charging", "icon": "🚗", "standards": ["SANS 10142", "IEC 61851"]},
        ]
    },
    "commercial": {
        "name": "Commercial",
        "icon": "🏢",
        "subtypes": [
            {"code": "office", "name": "Office Buildings", "icon": "🏢", "standards": ["SANS 10142", "SANS 10400-XA"]},
            {"code": "retail", "name": "Retail & Shopping", "icon": "🏪", "standards": ["SANS 10142", "SANS 10400"]},
            {"code": "hospitality", "name": "Hotels & Restaurants", "icon": "🏨", "standards": ["SANS 10142", "SANS 10400"]},
            {"code": "healthcare", "name": "Healthcare Facilities", "icon": "🏥", "standards": ["SANS 10142", "SANS 10049"]},
            {"code": "education", "name": "Schools & Educational", "icon": "🏫", "standards": ["SANS 10142", "SANS 10400"]},
        ]
    },
    "industrial": {
        "name": "Industrial",
        "icon": "🏭",
        "subtypes": [
            {"code": "mining_surface", "name": "Mining - Surface", "icon": "⛏️", "standards": ["MHSA", "SANS 10142", "SANS 10108"]},
            {"code": "mining_underground", "name": "Mining - Underground", "icon": "⛏️", "standards": ["MHSA", "SANS 10108", "DMR"]},
            {"code": "manufacturing", "name": "Factory & Manufacturing", "icon": "🏭", "standards": ["SANS 10142", "OHS Act"]},
            {"code": "warehouse", "name": "Warehouse & Distribution", "icon": "📦", "standards": ["SANS 10142"]},
            {"code": "agricultural", "name": "Agricultural & Farms", "icon": "🌾", "standards": ["SANS 10142"]},
            {"code": "substation", "name": "Substations & HV", "icon": "⚡", "standards": ["NRS 034", "Eskom DSS"]},
        ]
    },
    "infrastructure": {
        "name": "Infrastructure",
        "icon": "🌍",
        "subtypes": [
            {"code": "township", "name": "Township Electrification", "icon": "🏘️", "standards": ["NRS 034", "Eskom DSD"]},
            {"code": "rural", "name": "Rural Electrification", "icon": "🌍", "standards": ["NRS 034", "INEP"]},
            {"code": "street_lighting", "name": "Street Lighting", "icon": "🛣️", "standards": ["SANS 10098", "SANS 10089"]},
            {"code": "minigrid", "name": "Mini-Grid & Microgrid", "icon": "📡", "standards": ["NERSA", "NRS 097"]},
            {"code": "utility_solar", "name": "Utility-Scale Solar", "icon": "🔋", "standards": ["NERSA", "Grid Code"]},
        ]
    }
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE PROJECT PARAMETERS - ALL 4 TIERS
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────
# TIER 1: RESIDENTIAL SPECIFICATIONS
# ─────────────────────────────────────────────

RESIDENTIAL_SOLAR_SYSTEMS = {
    "essential": {
        "name": "Essential Backup (3kVA)",
        "inverter_kva": 3,
        "battery_kwh": 5.12,
        "panels_kw": 2.4,
        "circuits_covered": ["lights", "tv", "wifi", "fridge"],
        "autonomy_hours": 4,
        "components": {
            "inverter": {"item": "Hybrid Inverter 3kVA 24V", "qty": 1, "price": 12500},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 1, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 6, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (6 panels)", "qty": 1, "price": 4500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 1, "price": 850},
            "ac_isolator": {"item": "AC Isolator 40A", "qty": 2, "price": 350},
            "surge_dc": {"item": "DC Surge Protector", "qty": 1, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 1, "price": 2800},
            "changeover": {"item": "Automatic Changeover 40A", "qty": 1, "price": 3500},
        },
        "labour": {"installation": 8500, "commissioning": 1500, "coc": 2200},
    },
    "standard": {
        "name": "Home Backup (5kVA)",
        "inverter_kva": 5,
        "battery_kwh": 10.24,
        "panels_kw": 4.0,
        "circuits_covered": ["lights", "plugs", "tv", "wifi", "fridge", "microwave"],
        "autonomy_hours": 6,
        "components": {
            "inverter": {"item": "Hybrid Inverter 5kVA 48V", "qty": 1, "price": 18500},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 2, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 10, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (10 panels)", "qty": 1, "price": 6500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 2, "price": 850},
            "ac_isolator": {"item": "AC Isolator 63A", "qty": 2, "price": 450},
            "surge_dc": {"item": "DC Surge Protector", "qty": 2, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 2, "price": 2800},
            "changeover": {"item": "Automatic Changeover 63A", "qty": 1, "price": 4500},
            "db_solar": {"item": "Solar DB 8-way", "qty": 1, "price": 1200},
        },
        "labour": {"installation": 12000, "commissioning": 2000, "coc": 2200},
    },
    "premium": {
        "name": "Full Home (8kVA)",
        "inverter_kva": 8,
        "battery_kwh": 20.48,
        "panels_kw": 6.4,
        "circuits_covered": ["all_circuits", "stove", "geyser_timer"],
        "autonomy_hours": 8,
        "components": {
            "inverter": {"item": "Hybrid Inverter 8kVA 48V", "qty": 1, "price": 32000},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 4, "price": 28000},
            "panels": {"item": "Solar Panel 400W Mono", "qty": 16, "price": 1800},
            "mounting": {"item": "Roof Mount Kit (16 panels)", "qty": 1, "price": 9500},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 3, "price": 850},
            "ac_isolator": {"item": "AC Isolator 80A", "qty": 2, "price": 550},
            "surge_dc": {"item": "DC Surge Protector", "qty": 3, "price": 1200},
            "cables": {"item": "Solar Cable 6mm 100m", "qty": 3, "price": 2800},
            "changeover": {"item": "Automatic Changeover 80A", "qty": 1, "price": 5500},
            "db_solar": {"item": "Solar DB 12-way", "qty": 1, "price": 1800},
            "smart_meter": {"item": "Smart Energy Meter WiFi", "qty": 1, "price": 2500},
        },
        "labour": {"installation": 18000, "commissioning": 3000, "coc": 2200},
    },
    "offgrid": {
        "name": "Off-Grid (10kVA)",
        "inverter_kva": 10,
        "battery_kwh": 30.72,
        "panels_kw": 10.0,
        "circuits_covered": ["complete_home"],
        "autonomy_hours": 24,
        "components": {
            "inverter": {"item": "Off-Grid Inverter 10kVA 48V", "qty": 1, "price": 45000},
            "battery": {"item": "Lithium Battery 5.12kWh 48V", "qty": 6, "price": 28000},
            "panels": {"item": "Solar Panel 500W Mono", "qty": 20, "price": 2200},
            "mounting": {"item": "Ground Mount Structure (20 panels)", "qty": 1, "price": 18000},
            "dc_isolator": {"item": "DC Isolator 600V 32A", "qty": 4, "price": 850},
            "ac_isolator": {"item": "AC Isolator 100A", "qty": 2, "price": 650},
            "surge_dc": {"item": "DC Surge Protector", "qty": 4, "price": 1200},
            "cables": {"item": "Solar Cable 10mm 100m", "qty": 4, "price": 4200},
            "combiner": {"item": "PV Combiner Box 6-string", "qty": 1, "price": 3500},
            "db_solar": {"item": "Solar DB 16-way", "qty": 1, "price": 2200},
            "smart_meter": {"item": "Smart Energy Meter WiFi", "qty": 1, "price": 2500},
            "generator_ready": {"item": "Generator Input Panel", "qty": 1, "price": 4500},
        },
        "labour": {"installation": 25000, "commissioning": 5000, "coc": 2200},
    },
}

RESIDENTIAL_SECURITY_SYSTEMS = {
    "basic": {
        "name": "Basic Security",
        "components": {
            "alarm_panel": {"item": "Alarm Panel 8-zone", "qty": 1, "price": 2500},
            "keypad": {"item": "LCD Keypad", "qty": 1, "price": 850},
            "pir_indoor": {"item": "PIR Motion Sensor Indoor", "qty": 4, "price": 350},
            "door_contact": {"item": "Magnetic Door Contact", "qty": 3, "price": 120},
            "siren_indoor": {"item": "Indoor Siren", "qty": 1, "price": 450},
            "siren_outdoor": {"item": "Outdoor Siren Strobe", "qty": 1, "price": 850},
            "battery_backup": {"item": "Backup Battery 7Ah", "qty": 1, "price": 350},
            "cable_alarm": {"item": "Alarm Cable 4-core 100m", "qty": 1, "price": 450},
        },
        "labour": {"installation": 3500, "programming": 500},
    },
    "standard": {
        "name": "Standard Security + CCTV",
        "components": {
            "alarm_panel": {"item": "Alarm Panel 16-zone GSM", "qty": 1, "price": 4500},
            "keypad": {"item": "LCD Keypad", "qty": 2, "price": 850},
            "pir_indoor": {"item": "PIR Motion Sensor Indoor", "qty": 6, "price": 350},
            "pir_outdoor": {"item": "PIR Outdoor Dual-tech", "qty": 2, "price": 850},
            "door_contact": {"item": "Magnetic Door Contact", "qty": 5, "price": 120},
            "siren_indoor": {"item": "Indoor Siren", "qty": 1, "price": 450},
            "siren_outdoor": {"item": "Outdoor Siren Strobe", "qty": 1, "price": 850},
            "battery_backup": {"item": "Backup Battery 18Ah", "qty": 1, "price": 650},
            "nvr": {"item": "NVR 8-Channel 2TB", "qty": 1, "price": 4500},
            "camera_bullet": {"item": "IP Camera Bullet 4MP", "qty": 4, "price": 1800},
            "camera_dome": {"item": "IP Camera Dome 4MP", "qty": 2, "price": 1600},
            "poe_switch": {"item": "PoE Switch 8-port", "qty": 1, "price": 1800},
            "cable_cat6": {"item": "CAT6 Cable 305m", "qty": 1, "price": 2200},
            "monitor": {"item": "Monitor 22-inch", "qty": 1, "price": 2500},
        },
        "labour": {"installation": 8500, "programming": 1500, "cctv_setup": 2500},
    },
    "premium": {
        "name": "Premium Security + Electric Fence",
        "components": {
            "alarm_panel": {"item": "Alarm Panel 32-zone WiFi", "qty": 1, "price": 8500},
            "keypad": {"item": "Touch Keypad", "qty": 3, "price": 1500},
            "pir_indoor": {"item": "PIR Motion Sensor Indoor", "qty": 8, "price": 350},
            "pir_outdoor": {"item": "PIR Outdoor Dual-tech", "qty": 4, "price": 850},
            "door_contact": {"item": "Magnetic Door Contact", "qty": 8, "price": 120},
            "glass_break": {"item": "Glass Break Sensor", "qty": 4, "price": 550},
            "siren_indoor": {"item": "Indoor Siren", "qty": 2, "price": 450},
            "siren_outdoor": {"item": "Outdoor Siren Strobe", "qty": 2, "price": 850},
            "battery_backup": {"item": "Backup Battery 18Ah", "qty": 2, "price": 650},
            "nvr": {"item": "NVR 16-Channel 4TB", "qty": 1, "price": 7500},
            "camera_bullet": {"item": "IP Camera Bullet 8MP", "qty": 6, "price": 3200},
            "camera_dome": {"item": "IP Camera Dome 8MP", "qty": 4, "price": 2800},
            "camera_ptz": {"item": "PTZ Camera 4MP", "qty": 1, "price": 8500},
            "poe_switch": {"item": "PoE Switch 16-port", "qty": 1, "price": 3500},
            "fence_energizer": {"item": "Electric Fence Energizer 8J", "qty": 1, "price": 6500},
            "fence_wire": {"item": "Fence Wire 2.5mm 500m", "qty": 2, "price": 1200},
            "fence_insulators": {"item": "Fence Insulators (100)", "qty": 3, "price": 450},
            "fence_poles": {"item": "Fence Brackets (set)", "qty": 1, "price": 3500},
            "gate_motor": {"item": "Gate Motor Sliding", "qty": 1, "price": 8500},
            "intercom": {"item": "Video Intercom System", "qty": 1, "price": 5500},
        },
        "labour": {"installation": 18000, "programming": 3000, "cctv_setup": 4500, "fence": 8500},
    },
}

RESIDENTIAL_EV_CHARGING = {
    "level1": {
        "name": "Level 1 - Basic (3.7kW)",
        "power_kw": 3.7,
        "voltage": 230,
        "current_a": 16,
        "charge_time_typical": "12-18 hours",
        "components": {
            "charger": {"item": "EV Charger 3.7kW Type 2", "qty": 1, "price": 8500},
            "cable_6mm": {"item": "Cable 6mm 3-core 20m", "qty": 1, "price": 1800},
            "isolator": {"item": "Isolator 20A IP65", "qty": 1, "price": 350},
            "rcbo": {"item": "RCBO Type B 20A 30mA", "qty": 1, "price": 1200},
            "conduit": {"item": "Conduit 25mm + fittings", "qty": 1, "price": 650},
        },
        "labour": {"installation": 3500, "coc": 2200},
    },
    "level2": {
        "name": "Level 2 - Standard (7.4kW)",
        "power_kw": 7.4,
        "voltage": 230,
        "current_a": 32,
        "charge_time_typical": "6-9 hours",
        "components": {
            "charger": {"item": "EV Charger 7.4kW Smart", "qty": 1, "price": 14500},
            "cable_10mm": {"item": "Cable 10mm 3-core 20m", "qty": 1, "price": 3200},
            "isolator": {"item": "Isolator 40A IP65", "qty": 1, "price": 450},
            "rcbo": {"item": "RCBO Type B 32A 30mA", "qty": 1, "price": 1500},
            "conduit": {"item": "Conduit 32mm + fittings", "qty": 1, "price": 850},
            "db_upgrade": {"item": "DB Space (if needed)", "qty": 1, "price": 1200},
        },
        "labour": {"installation": 5500, "coc": 2200},
    },
    "level2_fast": {
        "name": "Level 2 - Fast (22kW 3-Phase)",
        "power_kw": 22,
        "voltage": 400,
        "current_a": 32,
        "charge_time_typical": "2-3 hours",
        "components": {
            "charger": {"item": "EV Charger 22kW 3-Phase Smart", "qty": 1, "price": 28500},
            "cable_6mm_4core": {"item": "Cable 6mm 5-core 25m", "qty": 1, "price": 4500},
            "isolator_3p": {"item": "Isolator 40A 3-Phase IP65", "qty": 1, "price": 850},
            "rcbo_3p": {"item": "RCBO Type B 32A 3P+N 30mA", "qty": 1, "price": 3500},
            "conduit": {"item": "Conduit 40mm + fittings", "qty": 1, "price": 1200},
            "db_3phase": {"item": "3-Phase DB Board 12-way", "qty": 1, "price": 3500},
        },
        "labour": {"installation": 8500, "3phase_connection": 5500, "coc": 2200},
    },
}

# ─────────────────────────────────────────────
# TIER 2: COMMERCIAL SPECIFICATIONS
# ─────────────────────────────────────────────

COMMERCIAL_LOAD_FACTORS = {
    # W/m² load densities (SANS 10142 / IEC guidelines)
    "office": {
        "general_lighting": 12,      # W/m²
        "task_lighting": 5,          # W/m²
        "small_power": 25,           # W/m² (computers, equipment)
        "hvac": 80,                  # W/m² (air conditioning)
        "diversity_factor": 0.7,
        "power_factor": 0.9,
    },
    "retail": {
        "general_lighting": 20,      # W/m² (higher for display)
        "accent_lighting": 10,       # W/m²
        "small_power": 15,           # W/m²
        "hvac": 100,                 # W/m²
        "refrigeration": 50,         # W/m² (if applicable)
        "diversity_factor": 0.8,
        "power_factor": 0.85,
    },
    "hospitality": {
        "general_lighting": 15,      # W/m²
        "decorative_lighting": 10,   # W/m²
        "small_power": 20,           # W/m²
        "hvac": 120,                 # W/m²
        "kitchen": 200,              # W/m² (commercial kitchen areas)
        "diversity_factor": 0.65,
        "power_factor": 0.85,
    },
    "healthcare": {
        "general_lighting": 15,      # W/m²
        "medical_equipment": 50,     # W/m²
        "small_power": 30,           # W/m²
        "hvac": 150,                 # W/m² (critical areas)
        "diversity_factor": 0.75,
        "power_factor": 0.9,
        "emergency_percent": 30,     # % requiring backup
    },
    "education": {
        "general_lighting": 12,      # W/m²
        "small_power": 15,           # W/m²
        "hvac": 60,                  # W/m²
        "computer_lab": 40,          # W/m² (labs)
        "diversity_factor": 0.6,
        "power_factor": 0.85,
    },
}

COMMERCIAL_DISTRIBUTION = {
    # DB Board and distribution specifications by building size
    "small": {  # < 500m²
        "main_switch": {"size": "100A", "price": 2500},
        "db_board": {"ways": 24, "price": 4500},
        "submains_cable": "25mm² 4-core",
        "earth_system": "TN-S",
        "metering": "single_tariff",
    },
    "medium": {  # 500-2000m²
        "main_switch": {"size": "250A", "price": 8500},
        "db_board": {"ways": 48, "price": 12000},
        "submains_cable": "70mm² 4-core",
        "earth_system": "TN-S",
        "metering": "tou_tariff",  # Time of use
        "sub_dbs": 4,
    },
    "large": {  # > 2000m²
        "main_switch": {"size": "630A", "price": 25000},
        "msb": {"type": "Main Switchboard", "price": 85000},
        "submains_cable": "185mm² 4-core",
        "earth_system": "TN-S with isolated earth",
        "metering": "max_demand",
        "sub_dbs": 8,
        "transformer": True,
    },
}

COMMERCIAL_EMERGENCY_POWER = {
    "ups_small": {
        "name": "UPS System 10kVA",
        "capacity_kva": 10,
        "runtime_min": 15,
        "components": {
            "ups": {"item": "Online UPS 10kVA", "qty": 1, "price": 45000},
            "battery_bank": {"item": "Battery Bank 192V", "qty": 1, "price": 35000},
            "bypass_switch": {"item": "Manual Bypass Switch", "qty": 1, "price": 8500},
            "db_critical": {"item": "Critical Load DB", "qty": 1, "price": 5500},
        },
        "labour": 12000,
    },
    "ups_medium": {
        "name": "UPS System 30kVA",
        "capacity_kva": 30,
        "runtime_min": 30,
        "components": {
            "ups": {"item": "Online UPS 30kVA 3-Phase", "qty": 1, "price": 125000},
            "battery_cabinet": {"item": "Battery Cabinet", "qty": 2, "price": 55000},
            "bypass_switch": {"item": "Auto Bypass Switch", "qty": 1, "price": 18500},
            "db_critical": {"item": "Critical Load DB 48-way", "qty": 1, "price": 15000},
        },
        "labour": 25000,
    },
    "generator_small": {
        "name": "Generator 30kVA",
        "capacity_kva": 30,
        "fuel": "diesel",
        "components": {
            "generator": {"item": "Diesel Generator 30kVA Canopy", "qty": 1, "price": 185000},
            "ats": {"item": "Automatic Transfer Switch 100A", "qty": 1, "price": 35000},
            "fuel_tank": {"item": "Fuel Tank 200L", "qty": 1, "price": 8500},
            "exhaust": {"item": "Exhaust System", "qty": 1, "price": 15000},
            "cables": {"item": "Power Cables 35mm²", "qty": 1, "price": 12000},
        },
        "labour": 35000,
        "civil": 25000,  # Concrete plinth, ventilation
    },
    "generator_large": {
        "name": "Generator 250kVA",
        "capacity_kva": 250,
        "fuel": "diesel",
        "components": {
            "generator": {"item": "Diesel Generator 250kVA Container", "qty": 1, "price": 850000},
            "ats": {"item": "Automatic Transfer Switch 400A", "qty": 1, "price": 85000},
            "fuel_tank": {"item": "Fuel Tank 1000L Bunded", "qty": 1, "price": 45000},
            "exhaust": {"item": "Industrial Exhaust System", "qty": 1, "price": 45000},
            "cables": {"item": "Power Cables 185mm²", "qty": 1, "price": 55000},
            "sync_panel": {"item": "Synchronizing Panel", "qty": 1, "price": 125000},
        },
        "labour": 85000,
        "civil": 75000,
    },
}

COMMERCIAL_FIRE_DETECTION = {
    "conventional": {
        "name": "Conventional Fire Alarm",
        "price_per_zone": 8500,
        "max_zones": 16,
        "components": {
            "panel": {"item": "Conventional Fire Panel 8-zone", "qty": 1, "price": 12000},
            "smoke_detector": {"item": "Smoke Detector Conventional", "qty_per_100m2": 4, "price": 450},
            "heat_detector": {"item": "Heat Detector", "qty_per_100m2": 2, "price": 350},
            "manual_call": {"item": "Manual Call Point", "qty_per_floor": 2, "price": 550},
            "sounder": {"item": "Fire Sounder", "qty_per_floor": 4, "price": 650},
            "beacon": {"item": "Beacon Strobe", "qty_per_floor": 2, "price": 850},
        },
        "labour_per_device": 250,
    },
    "addressable": {
        "name": "Addressable Fire Alarm",
        "components": {
            "panel": {"item": "Addressable Fire Panel 2-Loop", "qty": 1, "price": 45000},
            "smoke_detector": {"item": "Addressable Smoke Detector", "qty_per_100m2": 4, "price": 850},
            "heat_detector": {"item": "Addressable Heat Detector", "qty_per_100m2": 2, "price": 750},
            "multi_sensor": {"item": "Multi-Sensor Detector", "qty_per_100m2": 1, "price": 1200},
            "manual_call": {"item": "Addressable Call Point", "qty_per_floor": 2, "price": 950},
            "sounder_beacon": {"item": "Addressable Sounder/Beacon", "qty_per_floor": 4, "price": 1500},
            "loop_isolator": {"item": "Loop Isolator Module", "qty_per_zone": 1, "price": 1200},
        },
        "labour_per_device": 350,
    },
}

# ─────────────────────────────────────────────
# TIER 3: INDUSTRIAL SPECIFICATIONS
# ─────────────────────────────────────────────

INDUSTRIAL_MOTOR_LOADS = {
    # Standard motor sizes and typical applications
    "small": {
        "range_kw": "0.75-7.5kW",
        "voltage": "400V 3-Phase",
        "starter": "DOL",
        "applications": ["Pumps", "Fans", "Conveyors"],
        "typical_motors": [
            {"kw": 0.75, "price": 3500, "starter_price": 2500, "cable": "2.5mm²"},
            {"kw": 1.5, "price": 4200, "starter_price": 2800, "cable": "2.5mm²"},
            {"kw": 2.2, "price": 5100, "starter_price": 3200, "cable": "4mm²"},
            {"kw": 4.0, "price": 7500, "starter_price": 4500, "cable": "6mm²"},
            {"kw": 5.5, "price": 9200, "starter_price": 5500, "cable": "10mm²"},
            {"kw": 7.5, "price": 11500, "starter_price": 6800, "cable": "10mm²"},
        ],
    },
    "medium": {
        "range_kw": "11-45kW",
        "voltage": "400V 3-Phase",
        "starter": "Star-Delta / Soft Starter",
        "applications": ["Compressors", "Large Pumps", "Crushers"],
        "typical_motors": [
            {"kw": 11, "price": 18500, "starter_price": 12000, "cable": "16mm²"},
            {"kw": 15, "price": 24000, "starter_price": 15000, "cable": "25mm²"},
            {"kw": 22, "price": 35000, "starter_price": 22000, "cable": "35mm²"},
            {"kw": 30, "price": 45000, "starter_price": 28000, "cable": "50mm²"},
            {"kw": 37, "price": 55000, "starter_price": 35000, "cable": "70mm²"},
            {"kw": 45, "price": 68000, "starter_price": 42000, "cable": "95mm²"},
        ],
    },
    "large": {
        "range_kw": "55-200kW",
        "voltage": "400V / 3.3kV / 6.6kV",
        "starter": "VSD / Soft Starter",
        "applications": ["Mills", "Large Compressors", "Winders"],
        "typical_motors": [
            {"kw": 55, "price": 85000, "vsd_price": 65000, "cable": "120mm²"},
            {"kw": 75, "price": 115000, "vsd_price": 85000, "cable": "150mm²"},
            {"kw": 90, "price": 145000, "vsd_price": 105000, "cable": "185mm²"},
            {"kw": 110, "price": 185000, "vsd_price": 135000, "cable": "240mm²"},
            {"kw": 132, "price": 225000, "vsd_price": 165000, "cable": "2x150mm²"},
            {"kw": 160, "price": 285000, "vsd_price": 195000, "cable": "2x185mm²"},
            {"kw": 200, "price": 365000, "vsd_price": 245000, "cable": "2x240mm²"},
        ],
    },
}

INDUSTRIAL_MCC = {
    # Motor Control Centre specifications
    "standard_mcc": {
        "name": "Standard MCC Panel",
        "construction": "Form 3b",
        "ip_rating": "IP42",
        "components": {
            "incomer": {"item": "ACB Incomer 1600A", "price": 125000},
            "bus_bar": {"item": "Copper Busbar per meter", "price": 8500},
            "dol_bucket": {"item": "DOL Starter Bucket (avg)", "price": 12500},
            "sd_bucket": {"item": "Star-Delta Bucket (avg)", "price": 25000},
            "vsd_bucket": {"item": "VSD Bucket (avg)", "price": 85000},
            "pfc": {"item": "PFC Section per 50kVAr", "price": 45000},
        },
        "labour_per_bucket": 3500,
        "testing_commissioning": 25000,
    },
    "mining_mcc": {
        "name": "Mining MCC Panel (Flameproof)",
        "construction": "Form 4b",
        "ip_rating": "IP65",
        "certification": ["SANS 10108", "ATEX"],
        "components": {
            "incomer": {"item": "Flameproof ACB 1000A", "price": 285000},
            "bus_bar": {"item": "Flameproof Busbar per meter", "price": 18500},
            "fp_starter": {"item": "Flameproof DOL Starter (avg)", "price": 85000},
            "fp_vsd": {"item": "Flameproof VSD (avg)", "price": 225000},
            "is_barrier": {"item": "IS Barrier Module", "price": 15000},
        },
        "labour_per_bucket": 8500,
        "testing_commissioning": 65000,
    },
}

INDUSTRIAL_MV_EQUIPMENT = {
    # Medium Voltage Equipment (11kV / 22kV)
    "switchgear_11kv": {
        "name": "11kV Switchgear",
        "components": {
            "vcb_panel": {"item": "11kV VCB Panel", "price": 385000},
            "rmu": {"item": "11kV Ring Main Unit 3-way", "price": 225000},
            "metering_panel": {"item": "11kV Metering Panel", "price": 165000},
            "protection_relay": {"item": "Numerical Protection Relay", "price": 85000},
            "surge_arrester": {"item": "11kV Surge Arrester (set)", "price": 25000},
            "cable_11kv": {"item": "11kV XLPE Cable per meter", "price": 1850},
            "termination": {"item": "11kV Cable Termination (set)", "price": 45000},
        },
    },
    "transformer": {
        "name": "Distribution Transformer",
        "options": [
            {"kva": 100, "type": "11kV/400V", "price": 125000, "losses": "low"},
            {"kva": 200, "type": "11kV/400V", "price": 185000, "losses": "low"},
            {"kva": 315, "type": "11kV/400V", "price": 245000, "losses": "low"},
            {"kva": 500, "type": "11kV/400V", "price": 325000, "losses": "low"},
            {"kva": 630, "type": "11kV/400V", "price": 385000, "losses": "low"},
            {"kva": 800, "type": "11kV/400V", "price": 465000, "losses": "low"},
            {"kva": 1000, "type": "11kV/400V", "price": 545000, "losses": "low"},
            {"kva": 1600, "type": "11kV/400V", "price": 785000, "losses": "low"},
            {"kva": 2000, "type": "11kV/400V", "price": 985000, "losses": "low"},
        ],
        "accessories": {
            "oil": {"item": "Transformer Oil per liter", "price": 45},
            "buchholz": {"item": "Buchholz Relay", "price": 18500},
            "wti": {"item": "Winding Temp Indicator", "price": 12500},
            "oti": {"item": "Oil Temp Indicator", "price": 8500},
            "marshalling_box": {"item": "Marshalling Box", "price": 15000},
        },
    },
    "substation_civil": {
        "mini_sub": {"item": "Mini-Substation (prefab)", "price": 285000},
        "outdoor_yard": {"item": "Outdoor Switchyard Civil", "price": 485000},
        "cable_trench": {"item": "Cable Trench per meter", "price": 2500},
        "earth_mat": {"item": "Earth Mat per m²", "price": 850},
    },
}

MINING_SPECIFIC = {
    # Mining-specific equipment (MHSA compliant)
    "underground": {
        "flameproof_db": {"item": "Flameproof DB 12-way", "price": 125000},
        "fp_isolator": {"item": "Flameproof Isolator 200A", "price": 45000},
        "trailing_cable": {"item": "Trailing Cable per meter", "price": 450},
        "caplamp_system": {"item": "Caplamp Charging System", "price": 185000},
        "is_telephone": {"item": "IS Telephone System", "price": 85000},
        "methane_monitor": {"item": "Methane Monitor", "price": 65000},
        "emergency_refuge": {"item": "Refuge Bay Electrical", "price": 125000},
    },
    "surface": {
        "dust_proof_db": {"item": "Dust-proof DB IP65", "price": 35000},
        "weatherproof_socket": {"item": "Weatherproof Socket 125A", "price": 8500},
        "mobile_substation": {"item": "Mobile Substation 500kVA", "price": 1250000},
        "dragline_supply": {"item": "Dragline Power Supply", "price": 2500000},
    },
    "safety_systems": {
        "leaky_feeder": {"item": "Leaky Feeder per 100m", "price": 25000},
        "tracking_system": {"item": "Personnel Tracking per tag", "price": 2500},
        "emergency_lighting": {"item": "Emergency Lighting System", "price": 45000},
        "ventilation_control": {"item": "Ventilation Control Panel", "price": 185000},
    },
}

# ─────────────────────────────────────────────
# TIER 4: INFRASTRUCTURE SPECIFICATIONS
# ─────────────────────────────────────────────

TOWNSHIP_ELECTRIFICATION = {
    # Per-stand allowances (Eskom/NRS 034 based)
    "20A_service": {
        "name": "20A Prepaid Service",
        "connection_size": "20A",
        "admd": 1.5,  # After Diversity Maximum Demand (kVA)
        "per_stand_cost": {
            "bulk_supply": 2500,          # HV infrastructure contribution
            "mv_reticulation": 4500,      # 11kV/22kV lines
            "transformer": 3000,          # Transformer share
            "lv_reticulation": 5500,      # LV lines to stands
            "service_connection": 2800,   # Pole to house
            "metering": 3200,             # Prepaid meter + ready board
            "earthing": 800,              # Earth electrode
            "street_lighting": 1500,      # Street light contribution
        },
        "total_per_stand": 23800,
    },
    "40A_service": {
        "name": "40A Prepaid Service",
        "connection_size": "40A",
        "admd": 3.5,
        "per_stand_cost": {
            "bulk_supply": 3500,
            "mv_reticulation": 5500,
            "transformer": 4000,
            "lv_reticulation": 6500,
            "service_connection": 3500,
            "metering": 3500,
            "earthing": 1000,
            "street_lighting": 1800,
        },
        "total_per_stand": 29300,
    },
    "60A_service": {
        "name": "60A Conventional Service",
        "connection_size": "60A",
        "admd": 5.0,
        "per_stand_cost": {
            "bulk_supply": 4500,
            "mv_reticulation": 6500,
            "transformer": 5000,
            "lv_reticulation": 7500,
            "service_connection": 4200,
            "metering": 4500,
            "earthing": 1200,
            "street_lighting": 2200,
        },
        "total_per_stand": 35600,
    },
}

RURAL_ELECTRIFICATION = {
    # Grid extension costs
    "grid_extension": {
        "mv_line_overhead": {
            "11kV_single": {"item": "11kV Single Phase Line per km", "price": 185000},
            "11kV_three": {"item": "11kV Three Phase Line per km", "price": 285000},
            "22kV_three": {"item": "22kV Three Phase Line per km", "price": 325000},
        },
        "mv_poles": {
            "wood_11m": {"item": "Wood Pole 11m treated", "price": 4500},
            "concrete_11m": {"item": "Concrete Pole 11m", "price": 8500},
            "steel_lattice": {"item": "Steel Lattice Structure", "price": 45000},
        },
        "transformer_pole_mount": {
            "16kva": {"item": "Pole-mount Transformer 16kVA", "price": 45000},
            "25kva": {"item": "Pole-mount Transformer 25kVA", "price": 55000},
            "50kva": {"item": "Pole-mount Transformer 50kVA", "price": 75000},
            "100kva": {"item": "Pole-mount Transformer 100kVA", "price": 115000},
        },
    },
    # Solar home systems (off-grid)
    "solar_home_system": {
        "basic": {
            "name": "Basic Solar Home (80Wp)",
            "capacity_wp": 80,
            "components": {
                "panel": {"item": "Solar Panel 80W", "qty": 1, "price": 1200},
                "battery": {"item": "Battery 50Ah", "qty": 1, "price": 1500},
                "controller": {"item": "PWM Controller 10A", "qty": 1, "price": 450},
                "lights": {"item": "LED Lights 5W", "qty": 4, "price": 150},
                "phone_charger": {"item": "USB Phone Charger", "qty": 1, "price": 120},
                "wiring_kit": {"item": "Wiring Kit", "qty": 1, "price": 350},
            },
            "labour": 800,
            "total": 5020,
        },
        "standard": {
            "name": "Standard Solar Home (200Wp)",
            "capacity_wp": 200,
            "components": {
                "panel": {"item": "Solar Panel 200W", "qty": 1, "price": 2200},
                "battery": {"item": "Battery 100Ah", "qty": 1, "price": 2800},
                "controller": {"item": "MPPT Controller 20A", "qty": 1, "price": 1500},
                "inverter": {"item": "Modified Sine Inverter 500W", "qty": 1, "price": 1200},
                "lights": {"item": "LED Lights 9W", "qty": 6, "price": 200},
                "tv_radio": {"item": "DC TV 19-inch", "qty": 1, "price": 2500},
                "wiring_kit": {"item": "Wiring Kit Complete", "qty": 1, "price": 650},
            },
            "labour": 1200,
            "total": 13650,
        },
    },
    # Mini-grid specifications
    "minigrid": {
        "50kw": {
            "name": "Mini-Grid 50kW (50 households)",
            "capacity_kw": 50,
            "households_served": 50,
            "components": {
                "solar_array": {"item": "Solar Array 60kWp", "qty": 1, "price": 850000},
                "battery_bank": {"item": "Battery Bank 200kWh", "qty": 1, "price": 1850000},
                "inverter": {"item": "Hybrid Inverter 50kW", "qty": 1, "price": 285000},
                "distribution": {"item": "LV Distribution System", "qty": 1, "price": 350000},
                "metering": {"item": "Prepaid Meters (50)", "qty": 50, "price": 2500},
                "control_room": {"item": "Control Room Container", "qty": 1, "price": 185000},
            },
            "civil": 250000,
            "commissioning": 85000,
        },
    },
}

STREET_LIGHTING = {
    # SANS 10098 compliant street lighting
    "luminaires": {
        "led_30w": {"item": "LED Street Light 30W", "price": 2500, "lumens": 3600, "application": "Residential roads"},
        "led_60w": {"item": "LED Street Light 60W", "price": 3800, "lumens": 7200, "application": "Collector roads"},
        "led_90w": {"item": "LED Street Light 90W", "price": 5200, "lumens": 10800, "application": "Arterial roads"},
        "led_120w": {"item": "LED Street Light 120W", "price": 6500, "lumens": 14400, "application": "Major roads"},
        "led_150w": {"item": "LED Street Light 150W", "price": 8200, "lumens": 18000, "application": "Highways"},
        "highbay_200w": {"item": "High Mast 200W", "price": 12500, "lumens": 24000, "application": "Intersections"},
    },
    "poles": {
        "galvanized_6m": {"item": "Galvanized Steel Pole 6m", "price": 4500},
        "galvanized_8m": {"item": "Galvanized Steel Pole 8m", "price": 6500},
        "galvanized_10m": {"item": "Galvanized Steel Pole 10m", "price": 8500},
        "galvanized_12m": {"item": "Galvanized Steel Pole 12m", "price": 12000},
        "high_mast_18m": {"item": "High Mast Pole 18m", "price": 85000},
        "high_mast_25m": {"item": "High Mast Pole 25m", "price": 125000},
    },
    "installation_per_pole": {
        "excavation": 1500,
        "foundation": 2500,
        "erection": 1800,
        "wiring": 850,
        "testing": 500,
    },
    "control": {
        "photocell": {"item": "Photocell Controller", "price": 450},
        "timer": {"item": "Digital Timer", "price": 850},
        "smart_controller": {"item": "Smart Lighting Controller", "price": 15000},
        "energy_meter": {"item": "Energy Meter per circuit", "price": 2500},
    },
    "spacing_guidelines": {
        # SANS 10098 recommended spacing (meters)
        "residential": {"pole_height": 6, "spacing": 35, "lumens_required": 3600},
        "collector": {"pole_height": 8, "spacing": 40, "lumens_required": 7200},
        "arterial": {"pole_height": 10, "spacing": 45, "lumens_required": 10800},
        "highway": {"pole_height": 12, "spacing": 50, "lumens_required": 18000},
        "intersection": {"pole_height": 18, "spacing": 0, "lumens_required": 24000},
    },
}

UTILITY_SOLAR = {
    # Utility-scale solar specifications
    "ground_mount": {
        "1mw": {
            "name": "1MW Ground Mount Solar",
            "capacity_mw": 1,
            "land_required_ha": 2,
            "components": {
                "panels": {"item": "Solar Panels 550W (1820 units)", "price": 4550000},
                "inverters": {"item": "String Inverters 100kW (10)", "price": 1850000},
                "mounting": {"item": "Ground Mount Structure", "price": 1250000},
                "dc_cables": {"item": "DC Cabling System", "price": 450000},
                "combiner": {"item": "Combiner Boxes (20)", "price": 350000},
                "transformer": {"item": "Step-up Transformer 1MVA", "price": 650000},
                "switchgear": {"item": "MV Switchgear", "price": 485000},
                "scada": {"item": "SCADA & Monitoring", "price": 285000},
            },
            "civil": 850000,
            "grid_connection": 1250000,
            "epc_margin": 0.12,  # 12% EPC margin
        },
        "5mw": {
            "name": "5MW Ground Mount Solar",
            "capacity_mw": 5,
            "land_required_ha": 10,
            "components": {
                "panels": {"item": "Solar Panels 550W (9100 units)", "price": 18200000},
                "inverters": {"item": "Central Inverter 1MW (5)", "price": 8500000},
                "mounting": {"item": "Ground Mount Structure", "price": 5500000},
                "dc_cables": {"item": "DC Cabling System", "price": 1850000},
                "mv_cables": {"item": "MV Cabling System", "price": 1250000},
                "transformer": {"item": "Step-up Transformer 5MVA", "price": 2850000},
                "switchgear": {"item": "MV Switchgear Complete", "price": 1650000},
                "scada": {"item": "SCADA & Monitoring", "price": 485000},
                "security": {"item": "Perimeter Security", "price": 650000},
            },
            "civil": 3500000,
            "grid_connection": 4500000,
            "epc_margin": 0.10,
        },
    },
    "bess": {
        # Battery Energy Storage System
        "1mwh": {
            "name": "1MWh Battery Storage",
            "capacity_mwh": 1,
            "power_mw": 0.5,
            "components": {
                "battery_containers": {"item": "Battery Container 500kWh (2)", "price": 8500000},
                "pcs": {"item": "Power Conversion System 500kW", "price": 1850000},
                "transformer": {"item": "Transformer 630kVA", "price": 485000},
                "bms": {"item": "Battery Management System", "price": 650000},
                "hvac": {"item": "Container HVAC", "price": 350000},
                "fire_suppression": {"item": "Fire Suppression System", "price": 285000},
            },
            "civil": 450000,
            "integration": 850000,
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULATION FUNCTIONS FOR ALL TIERS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_commercial_electrical(area_m2: float, building_type: str, floors: int = 1,
                                     emergency_power: bool = False, fire_alarm: bool = True) -> dict:
    """
    Calculate commercial electrical requirements based on area and building type.
    Uses SANS 10142 / IEC load densities.
    """
    import math

    load_factors = COMMERCIAL_LOAD_FACTORS.get(building_type, COMMERCIAL_LOAD_FACTORS["office"])

    # Calculate connected loads
    lighting_load = area_m2 * (load_factors.get("general_lighting", 12) + load_factors.get("task_lighting", 0))
    power_load = area_m2 * load_factors.get("small_power", 25)
    hvac_load = area_m2 * load_factors.get("hvac", 80)

    # Special loads
    special_load = 0
    if building_type == "retail":
        special_load = area_m2 * load_factors.get("refrigeration", 0) * 0.3  # 30% of area
    elif building_type == "hospitality":
        special_load = area_m2 * load_factors.get("kitchen", 0) * 0.1  # 10% kitchen area
    elif building_type == "healthcare":
        special_load = area_m2 * load_factors.get("medical_equipment", 0)

    total_connected_load = lighting_load + power_load + hvac_load + special_load

    # Apply diversity
    diversified_load = total_connected_load * load_factors.get("diversity_factor", 0.7)

    # Calculate kVA
    power_factor = load_factors.get("power_factor", 0.9)
    total_kva = diversified_load / 1000 / power_factor

    # Determine distribution requirements
    if area_m2 < 500:
        dist = COMMERCIAL_DISTRIBUTION["small"]
        building_size = "small"
    elif area_m2 < 2000:
        dist = COMMERCIAL_DISTRIBUTION["medium"]
        building_size = "medium"
    else:
        dist = COMMERCIAL_DISTRIBUTION["large"]
        building_size = "large"

    # Circuit calculations
    lighting_circuits = math.ceil((lighting_load / 1000) / 2)  # 2kW per circuit max
    power_circuits = math.ceil((power_load / 1000) / 3.5)  # 3.5kW per circuit max
    hvac_circuits = math.ceil(hvac_load / 1000 / 5)  # 5kW per HVAC circuit

    # BQ Items
    bq_items = []

    # Main distribution
    bq_items.append({
        "category": "Main Distribution",
        "item": f"Main Switch {dist['main_switch']['size']}",
        "qty": 1, "unit": "each",
        "rate": dist['main_switch']['price'],
        "total": dist['main_switch']['price']
    })

    if building_size == "large" and "msb" in dist:
        bq_items.append({
            "category": "Main Distribution",
            "item": dist['msb']['type'],
            "qty": 1, "unit": "each",
            "rate": dist['msb']['price'],
            "total": dist['msb']['price']
        })
    else:
        bq_items.append({
            "category": "Main Distribution",
            "item": f"DB Board {dist['db_board']['ways']}-way",
            "qty": floors, "unit": "each",
            "rate": dist['db_board']['price'],
            "total": dist['db_board']['price'] * floors
        })

    # Sub-DBs
    if "sub_dbs" in dist:
        sub_db_price = 8500 if building_size == "medium" else 15000
        bq_items.append({
            "category": "Distribution",
            "item": "Sub-Distribution Board 24-way",
            "qty": dist["sub_dbs"], "unit": "each",
            "rate": sub_db_price,
            "total": sub_db_price * dist["sub_dbs"]
        })

    # Cables
    cable_runs = area_m2 * 0.15  # Estimate 0.15m cable per m² floor area
    bq_items.append({
        "category": "Cables",
        "item": f"Submains Cable {dist['submains_cable']}",
        "qty": int(cable_runs * 0.1), "unit": "meters",
        "rate": 450,
        "total": int(cable_runs * 0.1) * 450
    })
    bq_items.append({
        "category": "Cables",
        "item": "Lighting Circuit Cable 2.5mm²",
        "qty": int(cable_runs * 0.4), "unit": "meters",
        "rate": 25,
        "total": int(cable_runs * 0.4) * 25
    })
    bq_items.append({
        "category": "Cables",
        "item": "Power Circuit Cable 4mm²",
        "qty": int(cable_runs * 0.3), "unit": "meters",
        "rate": 45,
        "total": int(cable_runs * 0.3) * 45
    })

    # Lighting
    light_points = int(area_m2 / 6)  # 1 light per 6m²
    bq_items.append({
        "category": "Lighting",
        "item": "LED Panel Light 40W",
        "qty": light_points, "unit": "each",
        "rate": 650,
        "total": light_points * 650
    })
    bq_items.append({
        "category": "Lighting",
        "item": "Emergency Light 3-hour",
        "qty": max(4, int(light_points * 0.1)), "unit": "each",
        "rate": 850,
        "total": max(4, int(light_points * 0.1)) * 850
    })

    # Power outlets
    power_points = int(area_m2 / 8)  # 1 outlet per 8m²
    bq_items.append({
        "category": "Power",
        "item": "Socket Outlet Double",
        "qty": power_points, "unit": "each",
        "rate": 120,
        "total": power_points * 120
    })

    # Fire alarm
    if fire_alarm:
        fire_system = COMMERCIAL_FIRE_DETECTION["addressable" if area_m2 > 500 else "conventional"]
        detectors = int(area_m2 / 100) * fire_system["components"]["smoke_detector"]["qty_per_100m2"]
        bq_items.append({
            "category": "Fire Detection",
            "item": fire_system["components"]["panel"]["item"],
            "qty": 1, "unit": "each",
            "rate": fire_system["components"]["panel"]["price"],
            "total": fire_system["components"]["panel"]["price"]
        })
        bq_items.append({
            "category": "Fire Detection",
            "item": fire_system["components"]["smoke_detector"]["item"],
            "qty": detectors, "unit": "each",
            "rate": fire_system["components"]["smoke_detector"]["price"],
            "total": detectors * fire_system["components"]["smoke_detector"]["price"]
        })

    # Emergency power
    emergency_system = None
    if emergency_power:
        if total_kva < 50:
            emergency_system = COMMERCIAL_EMERGENCY_POWER["ups_small"]
        elif total_kva < 150:
            emergency_system = COMMERCIAL_EMERGENCY_POWER["generator_small"]
        else:
            emergency_system = COMMERCIAL_EMERGENCY_POWER["generator_large"]

        for comp_key, comp in emergency_system["components"].items():
            bq_items.append({
                "category": "Emergency Power",
                "item": comp["item"],
                "qty": comp.get("qty", 1), "unit": "each",
                "rate": comp["price"],
                "total": comp["price"] * comp.get("qty", 1)
            })

    # Labour
    labour_rate = 450  # per hour
    installation_hours = area_m2 * 0.5  # 0.5 hours per m²
    bq_items.append({
        "category": "Labour",
        "item": "Electrical Installation",
        "qty": int(installation_hours), "unit": "hours",
        "rate": labour_rate,
        "total": int(installation_hours) * labour_rate
    })
    bq_items.append({
        "category": "Labour",
        "item": "Testing & Commissioning",
        "qty": 1, "unit": "sum",
        "rate": area_m2 * 15,
        "total": area_m2 * 15
    })
    bq_items.append({
        "category": "Compliance",
        "item": "COC Certificate",
        "qty": 1, "unit": "each",
        "rate": 3500,
        "total": 3500
    })

    return {
        "building_type": building_type,
        "area_m2": area_m2,
        "floors": floors,
        "total_connected_kw": round(total_connected_load / 1000, 1),
        "diversified_kw": round(diversified_load / 1000, 1),
        "total_kva": round(total_kva, 1),
        "main_switch": dist['main_switch']['size'],
        "lighting_circuits": lighting_circuits,
        "power_circuits": power_circuits,
        "hvac_circuits": hvac_circuits,
        "light_points": light_points,
        "power_points": power_points,
        "emergency_system": emergency_system["name"] if emergency_system else "None",
        "bq_items": bq_items,
        "total_cost": sum(item["total"] for item in bq_items),
    }


def calculate_industrial_electrical(motors: list, has_mcc: bool = True, has_pfc: bool = True,
                                     mv_supply: bool = False, mining_type: str = None) -> dict:
    """
    Calculate industrial electrical requirements based on motor loads.

    Args:
        motors: List of {"kw": float, "qty": int, "type": "dol|sd|vsd"}
        has_mcc: Include MCC panel
        has_pfc: Include power factor correction
        mv_supply: Requires MV (11kV) supply
        mining_type: "surface" or "underground" for mining-specific requirements
    """
    import math

    bq_items = []
    total_motor_kw = 0
    motor_details = []

    # Process motors
    for motor in motors:
        kw = motor.get("kw", 11)
        qty = motor.get("qty", 1)
        starter_type = motor.get("type", "dol")

        total_motor_kw += kw * qty

        # Find motor specifications
        motor_spec = None
        for category in ["small", "medium", "large"]:
            for spec in INDUSTRIAL_MOTOR_LOADS[category]["typical_motors"]:
                if spec["kw"] == kw:
                    motor_spec = spec
                    break
            if motor_spec:
                break

        if not motor_spec:
            # Default pricing for unlisted sizes
            motor_spec = {"kw": kw, "price": kw * 1500, "starter_price": kw * 800, "cable": "16mm²"}

        motor_details.append({
            "kw": kw,
            "qty": qty,
            "starter": starter_type,
            "motor_price": motor_spec["price"],
            "starter_price": motor_spec.get("vsd_price", motor_spec["starter_price"]) if starter_type == "vsd" else motor_spec["starter_price"],
            "cable": motor_spec["cable"],
        })

        # Add motor to BQ
        bq_items.append({
            "category": "Motors",
            "item": f"Motor {kw}kW IE3",
            "qty": qty, "unit": "each",
            "rate": motor_spec["price"],
            "total": motor_spec["price"] * qty
        })

        # Add starter
        if starter_type == "vsd":
            bq_items.append({
                "category": "Motor Control",
                "item": f"VSD {kw}kW",
                "qty": qty, "unit": "each",
                "rate": motor_spec.get("vsd_price", motor_spec["starter_price"] * 2.5),
                "total": motor_spec.get("vsd_price", motor_spec["starter_price"] * 2.5) * qty
            })
        else:
            starter_name = "DOL Starter" if starter_type == "dol" else "Star-Delta Starter"
            bq_items.append({
                "category": "Motor Control",
                "item": f"{starter_name} {kw}kW",
                "qty": qty, "unit": "each",
                "rate": motor_spec["starter_price"],
                "total": motor_spec["starter_price"] * qty
            })

    # Calculate total load
    diversity_factor = 0.7 if len(motors) > 5 else 0.8
    total_kva = total_motor_kw / 0.85 * diversity_factor  # Assume 0.85 PF for motors

    # MCC
    if has_mcc:
        mcc_spec = INDUSTRIAL_MCC["mining_mcc" if mining_type else "standard_mcc"]
        num_buckets = len(motors)

        bq_items.append({
            "category": "MCC",
            "item": mcc_spec["name"],
            "qty": 1, "unit": "each",
            "rate": mcc_spec["components"]["incomer"]["price"],
            "total": mcc_spec["components"]["incomer"]["price"]
        })
        bq_items.append({
            "category": "MCC",
            "item": "MCC Buckets (complete)",
            "qty": num_buckets, "unit": "each",
            "rate": 15000,
            "total": 15000 * num_buckets
        })
        bq_items.append({
            "category": "MCC",
            "item": "Testing & Commissioning",
            "qty": 1, "unit": "sum",
            "rate": mcc_spec["testing_commissioning"],
            "total": mcc_spec["testing_commissioning"]
        })

    # Power Factor Correction
    if has_pfc:
        pfc_kvar = total_motor_kw * 0.4  # Typical 40% of motor load
        pfc_price = (pfc_kvar / 50) * INDUSTRIAL_MCC["standard_mcc"]["components"]["pfc"]["price"]
        bq_items.append({
            "category": "Power Factor Correction",
            "item": f"PFC Bank {int(pfc_kvar)}kVAr",
            "qty": 1, "unit": "each",
            "rate": pfc_price,
            "total": pfc_price
        })

    # MV Supply
    transformer_kva = None
    if mv_supply or total_kva > 500:
        # Select transformer size
        for tx in INDUSTRIAL_MV_EQUIPMENT["transformer"]["options"]:
            if tx["kva"] >= total_kva * 1.25:  # 25% spare capacity
                transformer_kva = tx["kva"]
                tx_price = tx["price"]
                break

        if transformer_kva:
            bq_items.append({
                "category": "MV Supply",
                "item": f"Transformer {transformer_kva}kVA 11kV/400V",
                "qty": 1, "unit": "each",
                "rate": tx_price,
                "total": tx_price
            })
            bq_items.append({
                "category": "MV Supply",
                "item": "11kV RMU 3-way",
                "qty": 1, "unit": "each",
                "rate": INDUSTRIAL_MV_EQUIPMENT["switchgear_11kv"]["components"]["rmu"]["price"],
                "total": INDUSTRIAL_MV_EQUIPMENT["switchgear_11kv"]["components"]["rmu"]["price"]
            })

    # Mining-specific equipment
    if mining_type == "underground":
        bq_items.append({
            "category": "Mining Safety",
            "item": "Flameproof DB 12-way",
            "qty": 1, "unit": "each",
            "rate": MINING_SPECIFIC["underground"]["flameproof_db"]["price"],
            "total": MINING_SPECIFIC["underground"]["flameproof_db"]["price"]
        })
        bq_items.append({
            "category": "Mining Safety",
            "item": "Methane Monitor",
            "qty": 1, "unit": "each",
            "rate": MINING_SPECIFIC["underground"]["methane_monitor"]["price"],
            "total": MINING_SPECIFIC["underground"]["methane_monitor"]["price"]
        })

    # Labour
    installation_cost = total_motor_kw * 250  # R250 per kW installed
    bq_items.append({
        "category": "Labour",
        "item": "Installation & Cabling",
        "qty": 1, "unit": "sum",
        "rate": installation_cost,
        "total": installation_cost
    })
    bq_items.append({
        "category": "Labour",
        "item": "Testing & Commissioning",
        "qty": 1, "unit": "sum",
        "rate": total_motor_kw * 50,
        "total": total_motor_kw * 50
    })

    return {
        "total_motor_kw": total_motor_kw,
        "total_kva": round(total_kva, 1),
        "motor_count": sum(m["qty"] for m in motors),
        "motor_details": motor_details,
        "has_mcc": has_mcc,
        "has_pfc": has_pfc,
        "pfc_kvar": round(total_motor_kw * 0.4, 0) if has_pfc else 0,
        "transformer_kva": transformer_kva,
        "mining_type": mining_type,
        "bq_items": bq_items,
        "total_cost": sum(item["total"] for item in bq_items),
    }


def calculate_township_electrification(num_stands: int, service_level: str = "20A",
                                        street_lights: int = 0) -> dict:
    """
    Calculate township electrification costs per stand.

    Args:
        num_stands: Number of stands to electrify
        service_level: "20A", "40A", or "60A"
        street_lights: Number of street lights
    """
    service_key = f"{service_level}_service"
    if service_key not in TOWNSHIP_ELECTRIFICATION:
        service_key = "20A_service"

    spec = TOWNSHIP_ELECTRIFICATION[service_key]
    bq_items = []

    # Per-stand costs
    for cost_type, cost in spec["per_stand_cost"].items():
        bq_items.append({
            "category": "Electrification",
            "item": cost_type.replace("_", " ").title(),
            "qty": num_stands, "unit": "stand",
            "rate": cost,
            "total": cost * num_stands
        })

    # Street lighting
    if street_lights > 0:
        light_spec = STREET_LIGHTING["luminaires"]["led_60w"]
        pole_spec = STREET_LIGHTING["poles"]["galvanized_8m"]
        install_cost = sum(STREET_LIGHTING["installation_per_pole"].values())

        bq_items.append({
            "category": "Street Lighting",
            "item": light_spec["item"],
            "qty": street_lights, "unit": "each",
            "rate": light_spec["price"],
            "total": light_spec["price"] * street_lights
        })
        bq_items.append({
            "category": "Street Lighting",
            "item": pole_spec["item"],
            "qty": street_lights, "unit": "each",
            "rate": pole_spec["price"],
            "total": pole_spec["price"] * street_lights
        })
        bq_items.append({
            "category": "Street Lighting",
            "item": "Installation per pole",
            "qty": street_lights, "unit": "each",
            "rate": install_cost,
            "total": install_cost * street_lights
        })

    # Project management & contingency
    subtotal = sum(item["total"] for item in bq_items)
    bq_items.append({
        "category": "Project Costs",
        "item": "Project Management (8%)",
        "qty": 1, "unit": "sum",
        "rate": subtotal * 0.08,
        "total": subtotal * 0.08
    })
    bq_items.append({
        "category": "Project Costs",
        "item": "Contingency (10%)",
        "qty": 1, "unit": "sum",
        "rate": subtotal * 0.10,
        "total": subtotal * 0.10
    })

    total_cost = sum(item["total"] for item in bq_items)
    cost_per_stand = total_cost / num_stands

    return {
        "service_level": service_level,
        "admd_kva": spec["admd"],
        "num_stands": num_stands,
        "street_lights": street_lights,
        "cost_per_stand": round(cost_per_stand, 0),
        "bq_items": bq_items,
        "total_cost": round(total_cost, 0),
    }


def calculate_street_lighting(road_type: str, road_length_km: float,
                               both_sides: bool = False) -> dict:
    """
    Calculate street lighting costs per SANS 10098.

    Args:
        road_type: "residential", "collector", "arterial", "highway"
        road_length_km: Length of road in kilometers
        both_sides: Install lights on both sides
    """
    guidelines = STREET_LIGHTING["spacing_guidelines"].get(road_type, STREET_LIGHTING["spacing_guidelines"]["residential"])

    pole_height = guidelines["pole_height"]
    spacing = guidelines["spacing"]
    lumens = guidelines["lumens_required"]

    # Calculate number of poles
    num_poles = int((road_length_km * 1000) / spacing)
    if both_sides:
        num_poles *= 2

    # Select luminaire
    luminaire = None
    for key, spec in STREET_LIGHTING["luminaires"].items():
        if spec["lumens"] >= lumens:
            luminaire = spec
            break

    # Select pole
    pole_key = f"galvanized_{pole_height}m"
    pole = STREET_LIGHTING["poles"].get(pole_key, STREET_LIGHTING["poles"]["galvanized_8m"])

    bq_items = []

    bq_items.append({
        "category": "Luminaires",
        "item": luminaire["item"],
        "qty": num_poles, "unit": "each",
        "rate": luminaire["price"],
        "total": luminaire["price"] * num_poles
    })

    bq_items.append({
        "category": "Poles",
        "item": pole["item"],
        "qty": num_poles, "unit": "each",
        "rate": pole["price"],
        "total": pole["price"] * num_poles
    })

    # Cabling
    cable_length = road_length_km * 1000 * (2 if both_sides else 1.5)
    bq_items.append({
        "category": "Cables",
        "item": "Armoured Cable 4mm² 4-core",
        "qty": int(cable_length), "unit": "meters",
        "rate": 85,
        "total": int(cable_length) * 85
    })

    # Installation
    install_cost = sum(STREET_LIGHTING["installation_per_pole"].values())
    bq_items.append({
        "category": "Installation",
        "item": "Complete installation per pole",
        "qty": num_poles, "unit": "each",
        "rate": install_cost,
        "total": install_cost * num_poles
    })

    # Control
    bq_items.append({
        "category": "Control",
        "item": STREET_LIGHTING["control"]["photocell"]["item"],
        "qty": num_poles, "unit": "each",
        "rate": STREET_LIGHTING["control"]["photocell"]["price"],
        "total": STREET_LIGHTING["control"]["photocell"]["price"] * num_poles
    })

    # DB and metering
    control_points = max(1, num_poles // 20)  # 1 control point per 20 poles
    bq_items.append({
        "category": "Control",
        "item": "Street Light DB 12-way",
        "qty": control_points, "unit": "each",
        "rate": 8500,
        "total": 8500 * control_points
    })

    return {
        "road_type": road_type,
        "road_length_km": road_length_km,
        "both_sides": both_sides,
        "pole_height_m": pole_height,
        "spacing_m": spacing,
        "num_poles": num_poles,
        "luminaire": luminaire["item"],
        "bq_items": bq_items,
        "total_cost": sum(item["total"] for item in bq_items),
        "cost_per_km": round(sum(item["total"] for item in bq_items) / road_length_km, 0),
    }


def calculate_solar_system(system_type: str) -> dict:
    """
    Calculate residential solar system costs.

    Args:
        system_type: "essential", "standard", "premium", "offgrid"
    """
    if system_type not in RESIDENTIAL_SOLAR_SYSTEMS:
        system_type = "standard"

    system = RESIDENTIAL_SOLAR_SYSTEMS[system_type]
    bq_items = []

    # Components
    for comp_key, comp in system["components"].items():
        qty = comp.get("qty", 1)
        bq_items.append({
            "category": "Solar Components",
            "item": comp["item"],
            "qty": qty, "unit": "each",
            "rate": comp["price"],
            "total": comp["price"] * qty
        })

    # Labour
    for labour_type, cost in system["labour"].items():
        bq_items.append({
            "category": "Labour",
            "item": labour_type.replace("_", " ").title(),
            "qty": 1, "unit": "sum",
            "rate": cost,
            "total": cost
        })

    return {
        "system_name": system["name"],
        "inverter_kva": system["inverter_kva"],
        "battery_kwh": system["battery_kwh"],
        "panels_kw": system["panels_kw"],
        "autonomy_hours": system["autonomy_hours"],
        "circuits_covered": system["circuits_covered"],
        "bq_items": bq_items,
        "total_cost": sum(item["total"] for item in bq_items),
    }


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏗️ AfriPlan AI</h1>
        <p>Intelligent Architectural Floorplan Generator for South Africa — Prototype</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ─── SIDEBAR ───
    with st.sidebar:
        st.markdown("### ⚙️ Project Configuration")
        st.markdown("---")

        # ============================================
        # PROJECT TYPE SELECTOR (Multi-Tier)
        # ============================================
        st.markdown("**🏗️ Project Type**")

        # Tier selection
        tier_options = {
            "🏠 Residential": "residential",
            "🏢 Commercial": "commercial",
            "🏭 Industrial": "industrial",
            "🌍 Infrastructure": "infrastructure"
        }
        selected_tier_label = st.selectbox(
            "Select Tier",
            list(tier_options.keys()),
            index=0,
            help="Choose the type of electrical project"
        )
        selected_tier = tier_options[selected_tier_label]

        # Subtype selection based on tier
        if selected_tier in PROJECT_TYPES:
            subtypes = PROJECT_TYPES[selected_tier]["subtypes"]
            subtype_options = {f"{s['icon']} {s['name']}": s['code'] for s in subtypes}
            selected_subtype_label = st.selectbox(
                "Project Subtype",
                list(subtype_options.keys()),
                help="Select specific project type"
            )
            selected_subtype = subtype_options[selected_subtype_label]

            # Store in session state
            st.session_state["project_tier"] = selected_tier
            st.session_state["project_subtype"] = selected_subtype

            # Show applicable standards
            for s in subtypes:
                if s["code"] == selected_subtype:
                    if "standards" in s:
                        st.caption(f"Standards: {', '.join(s['standards'])}")
                    break

        st.markdown("---")

        # Plot dimensions
        st.markdown("**📐 Plot Dimensions**")
        col1, col2 = st.columns(2)
        with col1:
            plot_width = st.number_input("Width (m)", min_value=8.0, max_value=50.0, value=15.0, step=0.5)
        with col2:
            plot_length = st.number_input("Length (m)", min_value=8.0, max_value=50.0, value=20.0, step=0.5)
        
        plot_area = plot_width * plot_length
        st.info(f"Plot Area: **{plot_area:.0f} m²**")
        
        st.markdown("---")
        
        # Room configuration
        st.markdown("**🏠 Building Rooms**")
        
        # Quick presets
        preset_choice = st.selectbox("Quick Presets", [
            "Custom",
            "2-Bedroom House (Starter)",
            "3-Bedroom House (Standard)",
            "4-Bedroom House (Comfort)",
            "5-Bedroom Villa (Luxury)",
        ])
        
        if preset_choice == "2-Bedroom House (Starter)":
            default_rooms = [
                {"name": "Living Room", "type": "Living Room", "target_area": 16},
                {"name": "Bedroom 1", "type": "Bedroom", "target_area": 12},
                {"name": "Bedroom 2", "type": "Bedroom", "target_area": 10},
                {"name": "Kitchen", "type": "Kitchen", "target_area": 8},
                {"name": "Bathroom", "type": "Bathroom", "target_area": 5},
                {"name": "Toilet", "type": "Toilet", "target_area": 2},
            ]
        elif preset_choice == "3-Bedroom House (Standard)":
            default_rooms = [
                {"name": "Living Room", "type": "Living Room", "target_area": 20},
                {"name": "Dining Room", "type": "Dining Room", "target_area": 12},
                {"name": "Bedroom 1", "type": "Bedroom", "target_area": 14},
                {"name": "Bedroom 2", "type": "Bedroom", "target_area": 12},
                {"name": "Bedroom 3", "type": "Bedroom", "target_area": 10},
                {"name": "Kitchen", "type": "Kitchen", "target_area": 10},
                {"name": "Bathroom", "type": "Bathroom", "target_area": 6},
                {"name": "Toilet", "type": "Toilet", "target_area": 3},
                {"name": "Passage", "type": "Passage", "target_area": 6},
            ]
        elif preset_choice == "4-Bedroom House (Comfort)":
            default_rooms = [
                {"name": "Living Room", "type": "Living Room", "target_area": 25},
                {"name": "Dining Room", "type": "Dining Room", "target_area": 15},
                {"name": "Main Bedroom", "type": "Bedroom", "target_area": 16},
                {"name": "Bedroom 2", "type": "Bedroom", "target_area": 14},
                {"name": "Bedroom 3", "type": "Bedroom", "target_area": 12},
                {"name": "Bedroom 4", "type": "Bedroom", "target_area": 12},
                {"name": "Kitchen", "type": "Kitchen", "target_area": 12},
                {"name": "Main Bathroom", "type": "Bathroom", "target_area": 7},
                {"name": "Guest Bathroom", "type": "Bathroom", "target_area": 5},
                {"name": "Toilet", "type": "Toilet", "target_area": 3},
                {"name": "Passage", "type": "Passage", "target_area": 8},
                {"name": "Patio", "type": "Patio", "target_area": 10},
            ]
        elif preset_choice == "5-Bedroom Villa (Luxury)":
            default_rooms = [
                {"name": "Grand Living Room", "type": "Living Room", "target_area": 30},
                {"name": "Dining Room", "type": "Dining Room", "target_area": 18},
                {"name": "Master Suite", "type": "Bedroom", "target_area": 20},
                {"name": "Bedroom 2", "type": "Bedroom", "target_area": 16},
                {"name": "Bedroom 3", "type": "Bedroom", "target_area": 14},
                {"name": "Bedroom 4", "type": "Bedroom", "target_area": 14},
                {"name": "Bedroom 5", "type": "Bedroom", "target_area": 12},
                {"name": "Kitchen", "type": "Kitchen", "target_area": 14},
                {"name": "En-suite Bathroom", "type": "Bathroom", "target_area": 8},
                {"name": "Bathroom 2", "type": "Bathroom", "target_area": 6},
                {"name": "Bathroom 3", "type": "Bathroom", "target_area": 5},
                {"name": "Study", "type": "Study", "target_area": 12},
                {"name": "Passage", "type": "Passage", "target_area": 10},
                {"name": "Patio", "type": "Patio", "target_area": 15},
                {"name": "Garage", "type": "Garage", "target_area": 20},
            ]
        else: # Custom
            default_rooms = [
                {"name": "Living Room", "type": "Living Room", "target_area": 20},
                {"name": "Bedroom 1", "type": "Bedroom", "target_area": 14},
                {"name": "Bedroom 2", "type": "Bedroom", "target_area": 12},
                {"name": "Kitchen", "type": "Kitchen", "target_area": 10},
                {"name": "Bathroom", "type": "Bathroom", "target_area": 6},
                {"name": "Toilet", "type": "Toilet", "target_area": 3},
                {"name": "Passage", "type": "Passage", "target_area": 5},
            ]
        
        # Initialize session state
        if "rooms" not in st.session_state or preset_choice != st.session_state.get("last_preset"):
            st.session_state.rooms = default_rooms
            st.session_state.last_preset = preset_choice
        
        # Display rooms
        st.markdown(f"**{len(st.session_state.rooms)} rooms configured**")
        
        rooms_to_remove = None
        for i, room in enumerate(st.session_state.rooms):
            with st.expander(f"{room['name']} ({room['target_area']}m²)", expanded=False):
                room["name"] = st.text_input("Name", room["name"], key=f"name_{i}")
                room["type"] = st.selectbox("Type", list(ROOM_PRESETS.keys()),
                    index=list(ROOM_PRESETS.keys()).index(room["type"]) if room["type"] in ROOM_PRESETS else 0,
                    key=f"type_{i}")
                room["target_area"] = st.slider("Target Area (m²)", 2, 40, room["target_area"], key=f"area_{i}")
                if st.button("🗑️ Delete", key=f"del_{i}"):
                    rooms_to_remove = i
        
        if rooms_to_remove is not None:
            st.session_state.rooms.pop(rooms_to_remove)
            st.rerun()
        
        # Add room
        if st.button("➕ Add a Room"):
            st.session_state.rooms.append({
                "name": f"Room {len(st.session_state.rooms) + 1}",
                "type": "Bedroom",
                "target_area": 12
            })
            st.rerun()
        
        st.markdown("---")
        
        # Generation settings
        st.markdown("**🎲 Generation Options**")
        num_variations = st.slider("Number of variations", 1, 6, 4)
        
        st.markdown("---")
        
        # Generate button
        generate_btn = st.button("🚀 GENERATE PLANS", type="primary")
    
    # ─── MAIN CONTENT ───
    if generate_btn or "generated_plans" in st.session_state:
        if generate_btn:
            with st.spinner("🧠 The AI is generating your floorplans..."):
                generator = FloorplanGenerator(
                    plot_width=plot_width,
                    plot_length=plot_length,
                    rooms=st.session_state.rooms.copy(),
                    seed=42
                )
                variations = generator.generate_variations(n=num_variations)
                st.session_state.generated_plans = variations
                st.session_state.plot_w = plot_width
                st.session_state.plot_l = plot_length
        
        plans = st.session_state.generated_plans
        plot_w = st.session_state.plot_w
        plot_l = st.session_state.plot_l
        
        # Summary metrics
        total_built = sum(r["w"] * r["h"] for r in plans[0]) if plans else 0
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{len(plans)}</div>
                <div class="metric-label">Variations</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{len(plans[0]) if plans else 0}</div>
                <div class="metric-label">Rooms</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{total_built:.0f} m²</div>
                <div class="metric-label">Built Area</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            ratio = (total_built / (plot_w * plot_l) * 100) if plot_w * plot_l > 0 else 0
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{ratio:.0f}%</div>
                <div class="metric-label">Plot Coverage</div>
            </div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ─── TABS ───
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📐 Generated Plans", "📊 Cost Estimate", "⚡ Electrical Quote", "📄 Export", "🌍 3D View"])
        
        # TAB 1: GENERATED PLANS
        with tab1:
            st.markdown('<div class="section-title">AI Generated Floorplans</div>', unsafe_allow_html=True)
            
            # Display plans in grid
            cols_per_row = min(num_variations, 2)
            for row_start in range(0, len(plans), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    idx = row_start + j
                    if idx < len(plans):
                        with col:
                            fig = draw_floorplan(
                                plans[idx], plot_w, plot_l,
                                title=f"Variation {idx + 1}",
                            )
                            st.pyplot(fig)
                            plt.close(fig)
                            
                            # Room summary for this variation
                            with st.expander(f"Details for Variation {idx + 1}"):
                                for r in plans[idx]:
                                    area = r["w"] * r["h"]
                                    st.write(f"**{r['name']}**: {r['w']:.1f}m × {r['h']:.1f}m = {area:.1f} m²")
            
            # Select variation for BQ
            st.markdown("---")
            selected_var = st.selectbox(
                "Select variation for cost estimate and 3D view:",
                [f"Variation {i+1}" for i in range(len(plans))],
                key="selected_variation"
            )
            selected_idx = int(selected_var.split(" ")[1]) - 1
            st.session_state.selected_idx = selected_idx
        
        # TAB 2: BILL OF QUANTITIES
        with tab2:
            st.markdown('<div class="section-title">Bill of Quantities & Cost Estimate</div>', unsafe_allow_html=True)
            
            sel_idx = st.session_state.get("selected_idx", 0)
            selected_plan = plans[sel_idx]
            
            bq = calculate_bq(selected_plan)
            bq_items, total_zar = calculate_cost(bq)
            
            # Cost summary
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">R {total_zar:,.0f}</div>
                    <div class="metric-label">Total Cost (ZAR)</div>
                </div>""", unsafe_allow_html=True)
            with col2:
                cost_per_m2 = total_zar / total_built if total_built > 0 else 0
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-value">R {cost_per_m2:,.0f}/m²</div>
                    <div class="metric-label">Cost per m²</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            # BQ Table
            table_html = '<table class="bq-table"><thead><tr>'
            table_html += '<th>Material</th><th>Quantity</th><th>Unit</th><th>Rate (ZAR)</th><th>Total (ZAR)</th>'
            table_html += '</tr></thead><tbody>'
            
            for item in bq_items:
                table_html += f"""<tr>
                    <td>{item['material']}</td>
                    <td style="text-align:center;font-weight:bold;">{item['qty']}</td>
                    <td style="text-align:center;">{item['unit']}</td>
                    <td style="text-align:right;">R {item['unit_price_zar']:.2f}</td>
                    <td style="text-align:right;font-weight:bold;">R {item['total_zar']:,.0f}</td>
                </tr>"""
            
            table_html += f"""<tr style="background:#F59E0B22;font-weight:bold;">
                <td colspan="4" style="text-align:right;color:#F59E0B;">ESTIMATED TOTAL</td>
                <td style="text-align:right;color:#F59E0B;">R {total_zar:,.0f}</td>
            </tr>"""
            table_html += '</tbody></table>'
            
            st.markdown(table_html, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("💡 **Note:** Prices are based on average market rates in Johannesburg. "
                   "A margin of +/- 15% is recommended for market fluctuations.")

        # TAB 3: ELECTRICAL QUOTE
        with tab3:
            st.markdown('<p class="section-title">⚡ Electrical Installation Quote</p>', unsafe_allow_html=True)

            # Get selected project tier and subtype
            current_tier = st.session_state.get("project_tier", "residential")
            current_subtype = st.session_state.get("project_subtype", "new_house")

            # Display tier badge
            tier_info = PROJECT_TYPES.get(current_tier, PROJECT_TYPES["residential"])
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
                        padding: 10px 20px; border-radius: 8px; margin-bottom: 20px;
                        border-left: 4px solid #F59E0B;">
                <span style="font-size: 24px;">{tier_info['icon']}</span>
                <span style="color: #F59E0B; font-weight: bold; margin-left: 10px;">
                    {tier_info['name'].upper()} PROJECT
                </span>
                <span style="color: #94A3B8; margin-left: 10px;">
                    - {current_subtype.replace('_', ' ').title()}
                </span>
            </div>
            """, unsafe_allow_html=True)

            # ═══════════════════════════════════════════════════════════════
            # TIER-SPECIFIC FORMS
            # ═══════════════════════════════════════════════════════════════

            elec_bq_items = []
            elec_summary = {}

            # ─────────────────────────────────────────────
            # RESIDENTIAL TIER
            # ─────────────────────────────────────────────
            if current_tier == "residential":
                if current_subtype in ["new_house", "renovation", "coc_compliance"]:
                    # Use existing room-based calculation
                    sel_idx = st.session_state.get("selected_idx", 0)
                    selected_plan = plans[sel_idx]
                    elec_req = calculate_electrical_requirements(selected_plan)
                    circuit_info = calculate_load_and_circuits(elec_req)
                    elec_bq_items = calculate_electrical_bq(elec_req, circuit_info)

                    elec_summary = {
                        "Light Points": elec_req["total_lights"],
                        "Plug Points": elec_req["total_plugs"],
                        "Total Load": f"{circuit_info['total_load_kva']} kVA",
                        "DB Size": circuit_info['db_size'].replace('_', ' '),
                    }

                elif current_subtype == "solar_backup":
                    st.subheader("☀️ Solar & Backup Power System")

                    solar_type = st.selectbox(
                        "Select System Size",
                        ["essential", "standard", "premium", "offgrid"],
                        format_func=lambda x: RESIDENTIAL_SOLAR_SYSTEMS[x]["name"]
                    )

                    solar_result = calculate_solar_system(solar_type)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Inverter", f"{solar_result['inverter_kva']} kVA")
                    with col2:
                        st.metric("Battery", f"{solar_result['battery_kwh']} kWh")
                    with col3:
                        st.metric("Solar Panels", f"{solar_result['panels_kw']} kWp")
                    with col4:
                        st.metric("Autonomy", f"{solar_result['autonomy_hours']} hours")

                    st.info(f"**Circuits Covered:** {', '.join(solar_result['circuits_covered'])}")

                    elec_bq_items = solar_result["bq_items"]
                    elec_summary = {
                        "System": solar_result["system_name"],
                        "Inverter": f"{solar_result['inverter_kva']} kVA",
                        "Battery": f"{solar_result['battery_kwh']} kWh",
                        "Panels": f"{solar_result['panels_kw']} kWp",
                    }

                elif current_subtype == "security":
                    st.subheader("🔒 Security System")

                    security_level = st.selectbox(
                        "Security Level",
                        ["basic", "standard", "premium"],
                        format_func=lambda x: RESIDENTIAL_SECURITY_SYSTEMS[x]["name"]
                    )

                    sec_spec = RESIDENTIAL_SECURITY_SYSTEMS[security_level]

                    # Build BQ from security components
                    for comp_key, comp in sec_spec["components"].items():
                        elec_bq_items.append({
                            "category": "Security Equipment",
                            "item": comp["item"],
                            "qty": comp.get("qty", 1), "unit": "each",
                            "rate": comp["price"],
                            "total": comp["price"] * comp.get("qty", 1)
                        })

                    for labour_key, cost in sec_spec["labour"].items():
                        elec_bq_items.append({
                            "category": "Labour",
                            "item": labour_key.replace("_", " ").title(),
                            "qty": 1, "unit": "sum",
                            "rate": cost, "total": cost
                        })

                    elec_summary = {"System": sec_spec["name"]}

                elif current_subtype == "ev_charging":
                    st.subheader("🚗 EV Charging Station")

                    ev_level = st.selectbox(
                        "Charger Type",
                        ["level1", "level2", "level2_fast"],
                        format_func=lambda x: RESIDENTIAL_EV_CHARGING[x]["name"]
                    )

                    ev_spec = RESIDENTIAL_EV_CHARGING[ev_level]

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Power", f"{ev_spec['power_kw']} kW")
                    with col2:
                        st.metric("Current", f"{ev_spec['current_a']} A")
                    with col3:
                        st.metric("Charge Time", ev_spec['charge_time_typical'])

                    for comp_key, comp in ev_spec["components"].items():
                        elec_bq_items.append({
                            "category": "EV Charging",
                            "item": comp["item"],
                            "qty": comp.get("qty", 1), "unit": "each",
                            "rate": comp["price"],
                            "total": comp["price"] * comp.get("qty", 1)
                        })

                    for labour_key, cost in ev_spec["labour"].items():
                        elec_bq_items.append({
                            "category": "Labour",
                            "item": labour_key.replace("_", " ").title(),
                            "qty": 1, "unit": "sum",
                            "rate": cost, "total": cost
                        })

                    elec_summary = {
                        "Charger": ev_spec["name"],
                        "Power": f"{ev_spec['power_kw']} kW",
                    }

                else:
                    # Default to room-based for other residential subtypes
                    sel_idx = st.session_state.get("selected_idx", 0)
                    selected_plan = plans[sel_idx]
                    elec_req = calculate_electrical_requirements(selected_plan)
                    circuit_info = calculate_load_and_circuits(elec_req)
                    elec_bq_items = calculate_electrical_bq(elec_req, circuit_info)
                    elec_summary = {"Light Points": elec_req["total_lights"]}

            # ─────────────────────────────────────────────
            # COMMERCIAL TIER
            # ─────────────────────────────────────────────
            elif current_tier == "commercial":
                st.subheader("🏢 Commercial Electrical Design")

                com_col1, com_col2, com_col3 = st.columns(3)
                with com_col1:
                    building_type = st.selectbox(
                        "Building Type",
                        ["office", "retail", "hospitality", "healthcare", "education"],
                        index=["office", "retail", "hospitality", "healthcare", "education"].index(current_subtype) if current_subtype in ["office", "retail", "hospitality", "healthcare", "education"] else 0
                    )
                with com_col2:
                    building_area = st.number_input("Floor Area (m²)", min_value=100, max_value=50000, value=500)
                with com_col3:
                    num_floors = st.number_input("Number of Floors", min_value=1, max_value=50, value=1)

                com_opt_col1, com_opt_col2 = st.columns(2)
                with com_opt_col1:
                    emergency_power = st.checkbox("Emergency Power (Generator/UPS)", value=False)
                with com_opt_col2:
                    fire_alarm = st.checkbox("Fire Detection System", value=True)

                if st.button("📊 Calculate Commercial Quote", type="primary"):
                    commercial_result = calculate_commercial_electrical(
                        building_area, building_type, num_floors,
                        emergency_power, fire_alarm
                    )

                    st.session_state["commercial_result"] = commercial_result

                if "commercial_result" in st.session_state:
                    result = st.session_state["commercial_result"]

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Connected Load", f"{result['total_connected_kw']} kW")
                    with col2:
                        st.metric("Diversified Load", f"{result['diversified_kw']} kW")
                    with col3:
                        st.metric("Total kVA", f"{result['total_kva']} kVA")
                    with col4:
                        st.metric("Main Switch", result['main_switch'])

                    st.markdown("---")
                    st.markdown(f"""
                    **Circuit Summary:**
                    - Lighting Circuits: {result['lighting_circuits']}
                    - Power Circuits: {result['power_circuits']}
                    - HVAC Circuits: {result['hvac_circuits']}
                    - Light Points: {result['light_points']}
                    - Power Points: {result['power_points']}
                    - Emergency Power: {result['emergency_system']}
                    """)

                    elec_bq_items = result["bq_items"]
                    elec_summary = {
                        "Building Type": result["building_type"].title(),
                        "Area": f"{result['area_m2']} m²",
                        "Load": f"{result['total_kva']} kVA",
                    }

            # ─────────────────────────────────────────────
            # INDUSTRIAL TIER
            # ─────────────────────────────────────────────
            elif current_tier == "industrial":
                st.subheader("🏭 Industrial Electrical Design")

                # Motor input section
                st.markdown("**Motor Schedule**")

                if "industrial_motors" not in st.session_state:
                    st.session_state["industrial_motors"] = [
                        {"kw": 11, "qty": 2, "type": "dol"},
                        {"kw": 22, "qty": 1, "type": "sd"},
                    ]

                motors = st.session_state["industrial_motors"]

                for i, motor in enumerate(motors):
                    m_col1, m_col2, m_col3, m_col4 = st.columns([2, 1, 2, 1])
                    with m_col1:
                        motors[i]["kw"] = st.selectbox(
                            f"Motor {i+1} Size (kW)",
                            [0.75, 1.5, 2.2, 4, 5.5, 7.5, 11, 15, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200],
                            index=[0.75, 1.5, 2.2, 4, 5.5, 7.5, 11, 15, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200].index(motor["kw"]) if motor["kw"] in [0.75, 1.5, 2.2, 4, 5.5, 7.5, 11, 15, 22, 30, 37, 45, 55, 75, 90, 110, 132, 160, 200] else 6,
                            key=f"motor_kw_{i}"
                        )
                    with m_col2:
                        motors[i]["qty"] = st.number_input(f"Qty", 1, 20, motor["qty"], key=f"motor_qty_{i}")
                    with m_col3:
                        motors[i]["type"] = st.selectbox(
                            f"Starter Type",
                            ["dol", "sd", "vsd"],
                            format_func=lambda x: {"dol": "DOL", "sd": "Star-Delta", "vsd": "VSD"}[x],
                            index=["dol", "sd", "vsd"].index(motor["type"]),
                            key=f"motor_type_{i}"
                        )
                    with m_col4:
                        if st.button("🗑️", key=f"del_motor_{i}"):
                            motors.pop(i)
                            st.rerun()

                if st.button("➕ Add Motor"):
                    motors.append({"kw": 11, "qty": 1, "type": "dol"})
                    st.rerun()

                st.markdown("---")

                ind_opt_col1, ind_opt_col2, ind_opt_col3 = st.columns(3)
                with ind_opt_col1:
                    has_mcc = st.checkbox("Include MCC Panel", value=True)
                with ind_opt_col2:
                    has_pfc = st.checkbox("Power Factor Correction", value=True)
                with ind_opt_col3:
                    mining_type = st.selectbox(
                        "Mining Type (if applicable)",
                        [None, "surface", "underground"],
                        format_func=lambda x: "Not Mining" if x is None else x.title()
                    )

                if st.button("📊 Calculate Industrial Quote", type="primary"):
                    industrial_result = calculate_industrial_electrical(
                        motors, has_mcc, has_pfc,
                        mv_supply=(sum(m["kw"] * m["qty"] for m in motors) > 400),
                        mining_type=mining_type
                    )
                    st.session_state["industrial_result"] = industrial_result

                if "industrial_result" in st.session_state:
                    result = st.session_state["industrial_result"]

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Motor Load", f"{result['total_motor_kw']} kW")
                    with col2:
                        st.metric("Total kVA", f"{result['total_kva']} kVA")
                    with col3:
                        st.metric("Motors", result['motor_count'])
                    with col4:
                        if result['transformer_kva']:
                            st.metric("Transformer", f"{result['transformer_kva']} kVA")
                        else:
                            st.metric("PFC", f"{result['pfc_kvar']} kVAr")

                    elec_bq_items = result["bq_items"]
                    elec_summary = {
                        "Motor Load": f"{result['total_motor_kw']} kW",
                        "Total kVA": f"{result['total_kva']} kVA",
                    }

            # ─────────────────────────────────────────────
            # INFRASTRUCTURE TIER
            # ─────────────────────────────────────────────
            elif current_tier == "infrastructure":
                if current_subtype == "township":
                    st.subheader("🏘️ Township Electrification")

                    tw_col1, tw_col2 = st.columns(2)
                    with tw_col1:
                        num_stands = st.number_input("Number of Stands", min_value=10, max_value=10000, value=100)
                    with tw_col2:
                        service_level = st.selectbox(
                            "Service Level",
                            ["20A", "40A", "60A"],
                            help="ADMD: 20A=1.5kVA, 40A=3.5kVA, 60A=5.0kVA"
                        )

                    street_lights = st.number_input("Street Lights", min_value=0, max_value=1000, value=int(num_stands * 0.1))

                    if st.button("📊 Calculate Township Quote", type="primary"):
                        township_result = calculate_township_electrification(num_stands, service_level, street_lights)
                        st.session_state["township_result"] = township_result

                    if "township_result" in st.session_state:
                        result = st.session_state["township_result"]

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Stands", result['num_stands'])
                        with col2:
                            st.metric("Service Level", result['service_level'])
                        with col3:
                            st.metric("Cost per Stand", f"R {result['cost_per_stand']:,.0f}")
                        with col4:
                            st.metric("Total Project", f"R {result['total_cost']:,.0f}")

                        elec_bq_items = result["bq_items"]
                        elec_summary = {
                            "Stands": result['num_stands'],
                            "Service": result['service_level'],
                        }

                elif current_subtype == "street_lighting":
                    st.subheader("🛣️ Street Lighting Design")

                    sl_col1, sl_col2, sl_col3 = st.columns(3)
                    with sl_col1:
                        road_type = st.selectbox(
                            "Road Type",
                            ["residential", "collector", "arterial", "highway"]
                        )
                    with sl_col2:
                        road_length = st.number_input("Road Length (km)", min_value=0.1, max_value=100.0, value=1.0, step=0.1)
                    with sl_col3:
                        both_sides = st.checkbox("Lights on Both Sides", value=False)

                    if st.button("📊 Calculate Street Lighting Quote", type="primary"):
                        street_result = calculate_street_lighting(road_type, road_length, both_sides)
                        st.session_state["street_result"] = street_result

                    if "street_result" in st.session_state:
                        result = st.session_state["street_result"]

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Poles", result['num_poles'])
                        with col2:
                            st.metric("Pole Height", f"{result['pole_height_m']} m")
                        with col3:
                            st.metric("Spacing", f"{result['spacing_m']} m")
                        with col4:
                            st.metric("Cost per km", f"R {result['cost_per_km']:,.0f}")

                        elec_bq_items = result["bq_items"]
                        elec_summary = {
                            "Road Type": result['road_type'].title(),
                            "Length": f"{result['road_length_km']} km",
                        }

                else:
                    st.info(f"📋 {current_subtype.replace('_', ' ').title()} calculator coming soon...")
                    # Default placeholder for other infrastructure types
                    sel_idx = st.session_state.get("selected_idx", 0)
                    selected_plan = plans[sel_idx]
                    elec_req = calculate_electrical_requirements(selected_plan)
                    circuit_info = calculate_load_and_circuits(elec_req)
                    elec_bq_items = calculate_electrical_bq(elec_req, circuit_info)
                    elec_summary = {"Type": current_subtype}

            # ═══════════════════════════════════════════════════════════════
            # COMMON BQ DISPLAY (for all tiers)
            # ═══════════════════════════════════════════════════════════════

            if elec_bq_items:
                st.markdown("---")

                # Show summary metrics if available
                if elec_summary:
                    summary_cols = st.columns(len(elec_summary))
                    for i, (key, value) in enumerate(elec_summary.items()):
                        with summary_cols[i]:
                            st.metric(key, value)

                st.markdown("---")

                # Room-by-room breakdown (only for residential new house/renovation)
                if current_tier == "residential" and current_subtype in ["new_house", "renovation", "coc_compliance"]:
                    st.subheader("Room-by-Room Electrical Requirements")
                    room_data = []
                    for room in elec_req["room_details"]:
                        room_data.append({
                            "Room": room["name"],
                            "Type": room["type"],
                            "Area (m²)": room["area"],
                            "Lights": room["lights"],
                            "Plugs": room["plugs"],
                            "Special": ", ".join(room["special"]) if room["special"] else "-"
                        })
                    st.dataframe(room_data, use_container_width=True)

                    st.markdown("---")

                    # Circuit summary
                    st.subheader("Circuit Design (SANS 10142 Compliant)")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"""
                        **Distribution Board:** {circuit_info['db_size'].replace('_', ' ')}
                        - Main Switch: {circuit_info['main_size']}
                        - Earth Leakage: 63A 30mA
                        - Surge Protection: Type 2
                        """)
                    with col2:
                        st.info(f"""
                        **Circuits:**
                        - Lighting: {circuit_info['lighting_circuits']} circuits (max 10 pts each)
                        - Power: {circuit_info['power_circuits']} circuits (max 10 pts each)
                        - Dedicated: {circuit_info['dedicated_circuits']} circuits
                        """)

                    st.markdown("---")

                # Full BQ table with expandable categories
                st.subheader("Bill of Quantities")

                # Group by category
                categories = {}
                for item in elec_bq_items:
                    cat = item["category"]
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(item)

                for cat_name, items in categories.items():
                    cat_total = sum(i['total'] for i in items)
                    with st.expander(f"**{cat_name}** - R {cat_total:,.0f}"):
                        for item in items:
                            st.write(f"- {item['item']}: {item['qty']} {item['unit']} @ R{item['rate']:,} = **R{item['total']:,}**")

                # Totals
                st.markdown("---")
                subtotal = sum(item["total"] for item in elec_bq_items)
                vat = subtotal * 0.15
                total = subtotal + vat

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Subtotal (excl VAT)", f"R {subtotal:,.0f}")
                with col2:
                    st.metric("VAT (15%)", f"R {vat:,.0f}")
                with col3:
                    st.metric("TOTAL (incl VAT)", f"R {total:,.0f}")

                # ============================================
                # SMART COST OPTIMIZER - 4 QUOTATION OPTIONS
                # ============================================
                st.markdown("---")
                st.subheader("💡 Smart Cost Optimizer")
                st.markdown("Compare 4 quotation strategies to maximize profit or win more jobs.")

                # Generate the 4 options using generic function
                quotation_options = generate_quotation_options(elec_bq_items, {}, {})

                # Display options in columns
                opt_cols = st.columns(4)
                option_labels = ["A: Budget", "B: Best Value", "C: Premium", "D: Competitive"]
                option_icons = ["💰", "⭐", "👑", "🎯"]

                for idx, (col, opt) in enumerate(zip(opt_cols, quotation_options)):
                    with col:
                        is_recommended = opt.get("recommended", False)
                        border_color = "#F59E0B" if is_recommended else "#334155"

                        st.markdown(f"""
                        <div style="border: 2px solid {border_color}; border-radius: 10px; padding: 15px;
                                    background: {'rgba(245, 158, 11, 0.1)' if is_recommended else '#1E293B'};">
                            <div style="text-align: center; font-size: 24px;">{option_icons[idx]}</div>
                            <div style="text-align: center; font-weight: bold; color: {'#F59E0B' if is_recommended else '#E2E8F0'};
                                        margin: 8px 0;">{option_labels[idx]}</div>
                            {'<div style="text-align: center; font-size: 11px; color: #F59E0B;">⭐ RECOMMENDED</div>' if is_recommended else ''}
                            <hr style="border-color: #334155; margin: 10px 0;">
                            <div style="font-size: 12px; color: #94A3B8;">Base Cost</div>
                            <div style="font-size: 16px; color: #E2E8F0; font-weight: bold;">R {opt['base_cost']:,.0f}</div>
                            <div style="font-size: 12px; color: #94A3B8; margin-top: 8px;">Markup</div>
                            <div style="font-size: 14px; color: #E2E8F0;">{opt['markup_percent']:.0f}%</div>
                            <div style="font-size: 12px; color: #94A3B8; margin-top: 8px;">Selling Price</div>
                            <div style="font-size: 18px; color: #22C55E; font-weight: bold;">R {opt['selling_price']:,.0f}</div>
                            <div style="font-size: 12px; color: #94A3B8; margin-top: 8px;">Your Profit</div>
                            <div style="font-size: 16px; color: #F59E0B; font-weight: bold;">R {opt['profit']:,.0f}</div>
                            <div style="font-size: 11px; color: #64748B;">({opt['profit_margin']:.1f}% margin)</div>
                        </div>
                        """, unsafe_allow_html=True)

                # Summary comparison
                st.markdown("---")
                with st.expander("📊 Detailed Comparison Table"):
                    comparison_data = []
                    for idx, opt in enumerate(quotation_options):
                        comparison_data.append({
                            "Option": option_labels[idx],
                            "Strategy": opt["name"],
                            "Base Cost (R)": f"{opt['base_cost']:,.0f}",
                            "Markup %": f"{opt['markup_percent']:.0f}%",
                            "Selling Price (R)": f"{opt['selling_price']:,.0f}",
                            "Profit (R)": f"{opt['profit']:,.0f}",
                            "Margin %": f"{opt['profit_margin']:.1f}%",
                            "Recommended": "⭐" if opt.get("recommended") else ""
                        })
                    st.dataframe(comparison_data, use_container_width=True)

                # ============================================
                # OR OPTIMIZATION (Advanced)
                # ============================================
                st.markdown("---")
                with st.expander("🔬 Advanced OR Optimization (Operations Research)"):
                    st.markdown("""
                    Use **Integer Linear Programming (ILP)** to find the mathematically optimal
                    supplier selection. This uses industrial engineering optimization methods.
                    """)

                    or_col1, or_col2 = st.columns(2)
                    with or_col1:
                        min_quality = st.slider("Minimum Quality Score", 1, 5, 3,
                                               help="Minimum acceptable quality level (1-5)")
                    with or_col2:
                        budget_limit = st.number_input("Budget Limit (R)", min_value=0, value=0,
                                                       help="Leave 0 for no limit")

                    if st.button("🚀 Run OR Optimization", type="primary"):
                        with st.spinner("Solving optimization problem..."):
                            constraints = {
                                "min_quality": min_quality,
                                "budget": budget_limit if budget_limit > 0 else None
                            }
                            or_result = optimize_quotation_or(elec_bq_items, constraints)

                            if or_result["status"] == "optimal":
                                st.success(f"""
                                ✅ **Optimal Solution Found!**
                                - Solver Status: {or_result['solver_status']}
                                - Computation Time: {or_result.get('solve_time', 'N/A')}
                                """)

                                or_metrics = st.columns(4)
                                with or_metrics[0]:
                                    st.metric("Optimal Cost", f"R {or_result['total_cost']:,.0f}")
                                with or_metrics[1]:
                                    st.metric("Avg Quality", f"{or_result['average_quality']:.1f}/5")
                                with or_metrics[2]:
                                    st.metric("Suppliers Used", or_result['suppliers_used'])
                                with or_metrics[3]:
                                    savings = subtotal - or_result['total_cost']
                                    st.metric("Savings", f"R {savings:,.0f}",
                                             delta=f"{(savings/subtotal)*100:.1f}%" if subtotal > 0 else "0%")

                                st.markdown("**Optimal Supplier Selection:**")
                                for sel in or_result['selection']:
                                    st.write(f"- {sel['category']}: **{sel['supplier']}** @ R{sel['total']:,.0f}")
                            else:
                                st.warning(f"⚠️ Optimization Status: {or_result['status']}")
                                if "message" in or_result:
                                    st.info(or_result["message"])

                # Export buttons
                st.markdown("---")
                st.subheader("📄 Export Electrical Quotation")
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    if st.button("📄 Generate Electrical Quote PDF", type="primary", use_container_width=True):
                        # For non-residential or special projects, use generic PDF generation
                        if current_tier == "residential" and current_subtype in ["new_house", "renovation", "coc_compliance"]:
                            elec_pdf_bytes = generate_electrical_pdf(elec_req, circuit_info, elec_bq_items)
                        else:
                            # Generate generic PDF for other tiers
                            elec_pdf_bytes = generate_generic_electrical_pdf(elec_bq_items, elec_summary, current_tier, current_subtype)
                        st.download_button(
                            label="⬇️ Download Electrical Quote PDF",
                            data=elec_pdf_bytes,
                            file_name=f"electrical_quote_{current_tier}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                with exp_col2:
                    st.info("💡 Tip: Use the Cost Optimizer above to present multiple options to clients")

            else:
                st.info("👆 Configure your project parameters above and click Calculate to generate a quote.")

        # TAB 4: EXPORT
        with tab4:
            st.markdown('<div class="section-title">Export Quote to PDF</div>', unsafe_allow_html=True)
            
            sel_idx = st.session_state.get("selected_idx", 0)
            selected_plan = plans[sel_idx]
            
            st.write(f"Exporting plan **Variation {sel_idx + 1}** with full cost estimate.")
            
            if st.button("📄 Generate PDF"):
                with st.spinner("Generating PDF..."):
                    # Generate the plan figure for PDF
                    fig_pdf = draw_floorplan(
                        selected_plan, plot_w, plot_l,
                        title=f"AfriPlan AI - Variation {sel_idx + 1}",
                    )
                    
                    bq = calculate_bq(selected_plan)
                    bq_items, total_zar = calculate_cost(bq)
                    
                    pdf_bytes = generate_pdf(
                        selected_plan, bq_items, total_zar,
                        plot_w, plot_l, fig_pdf
                    )
                    plt.close(fig_pdf)
                    
                    st.success("✅ PDF generated successfully!")
                    st.download_button(
                        label="⬇️ Download Quote PDF",
                        data=pdf_bytes,
                        file_name=f"AfriPlan_Quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                    )
            
            st.markdown('<div class="section-title" style="margin-top: 30px;">Export Plan to DXF</div>', unsafe_allow_html=True)
            st.write(f"Exporting plan **Variation {sel_idx + 1}** as a DXF file for use in CAD software.")

            if st.button("📐 Generate DXF"):
                with st.spinner("Generating DXF file..."):
                    dxf_string = generate_dxf(selected_plan, plot_w, plot_l)
                    st.success("✅ DXF file generated successfully!")
                    st.download_button(
                        label="⬇️ Download DXF File",
                        data=dxf_string,
                        file_name=f"AfriPlan_Plan_{datetime.now().strftime('%Y%m%d_%H%M')}.dxf",
                        mime="application/dxf",
                    )

        # TAB 5: 3D VIEW
        with tab5:
            st.markdown('<div class="section-title">3D Visualization</div>', unsafe_allow_html=True)
            st.info("Use your mouse to rotate, zoom, and pan the 3D view.")
            
            sel_idx = st.session_state.get("selected_idx", 0)
            selected_plan = plans[sel_idx]

            fig_3d = draw_3d_floorplan(selected_plan, wall_height=3.0)
            st.plotly_chart(fig_3d, use_container_width=True)
    
    else:
        # Welcome state
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px;">
            <div style="font-size: 64px;">🏠</div>
            <h2 style="color: #E2E8F0; margin-bottom: 8px;">Welcome to AfriPlan AI</h2>
            <p style="color: #64748B; font-size: 16px; max-width: 500px; margin: 0 auto; line-height: 1.6;">
                Configure your plot and rooms in the sidebar,<br>
                then click <strong style="color: #F59E0B;">GENERATE PLANS</strong> to begin.
            </p>
            <br><br>
            <div style="display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;">
                <div style="text-align: center;">
                    <div style="font-size: 32px;">📐</div>
                    <div style="color: #94A3B8; font-size: 13px; margin-top: 4px;">Automatic Plans</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px;">💰</div>
                    <div style="color: #94A3B8; font-size: 13px; margin-top: 4px;">SA Cost Estimates</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px;">📄</div>
                    <div style="color: #94A3B8; font-size: 13px; margin-top: 4px;">PDF Export</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32px;">🇿🇦</div>
                    <div style="color: #94A3B8; font-size: 13px; margin-top: 4px;">Built for South Africa</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

