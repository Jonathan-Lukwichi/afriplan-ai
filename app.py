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

            sel_idx = st.session_state.get("selected_idx", 0)
            selected_plan = plans[sel_idx]

            # Calculate electrical requirements from floor plan
            elec_req = calculate_electrical_requirements(selected_plan)
            circuit_info = calculate_load_and_circuits(elec_req)
            elec_bq_items = calculate_electrical_bq(elec_req, circuit_info)

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Light Points", elec_req["total_lights"])
            with col2:
                st.metric("Plug Points", elec_req["total_plugs"])
            with col3:
                st.metric("Total Load", f"{circuit_info['total_load_kva']} kVA")
            with col4:
                elec_total_cost = sum(item["total"] for item in elec_bq_items)
                st.metric("Total Cost", f"R {elec_total_cost:,.0f}")

            st.markdown("---")

            # Room-by-room breakdown
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

            # Export buttons
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Generate Electrical Quote PDF", type="primary", use_container_width=True):
                    elec_pdf_bytes = generate_electrical_pdf(elec_req, circuit_info, elec_bq_items)
                    st.download_button(
                        label="⬇️ Download Electrical Quote PDF",
                        data=elec_pdf_bytes,
                        file_name=f"electrical_quote_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            with col2:
                st.info("💡 Tip: This quote is auto-calculated from your floor plan rooms")

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

