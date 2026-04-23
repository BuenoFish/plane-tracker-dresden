import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import time

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="D-ECJU Tracker",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

  html, body, [class*="css"] {
    font-family: 'Share Tech Mono', monospace;
    background-color: #0a0e1a;
    color: #00e5ff;
  }

  .stApp {
    background: radial-gradient(ellipse at 20% 50%, #0d1b2a 0%, #0a0e1a 60%);
  }

  h1, h2, h3 {
    font-family: 'Orbitron', sans-serif !important;
    color: #00e5ff !important;
    text-shadow: 0 0 20px rgba(0,229,255,0.5);
    letter-spacing: 3px;
  }

  .metric-card {
    background: rgba(0, 229, 255, 0.05);
    border: 1px solid rgba(0, 229, 255, 0.3);
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }

  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #00e5ff, transparent);
  }

  .metric-label {
    font-size: 0.7rem;
    color: #4dd0e1;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 6px;
  }

  .metric-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #00e5ff;
    text-shadow: 0 0 10px rgba(0,229,255,0.6);
  }

  .status-online {
    color: #00ff88;
    text-shadow: 0 0 10px rgba(0,255,136,0.6);
    font-weight: bold;
    animation: pulse 2s infinite;
  }

  .status-offline {
    color: #ff4444;
    text-shadow: 0 0 10px rgba(255,68,68,0.5);
    font-weight: bold;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .info-box {
    background: rgba(0, 229, 255, 0.03);
    border: 1px solid rgba(0, 229, 255, 0.15);
    border-left: 3px solid #00e5ff;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 0.85rem;
    color: #80deea;
    margin: 8px 0;
  }

  .title-glow {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.4rem;
    font-weight: 900;
    background: linear-gradient(135deg, #00e5ff, #00b0ff, #00e5ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: none;
    filter: drop-shadow(0 0 20px rgba(0,229,255,0.4));
    letter-spacing: 4px;
  }

  div[data-testid="stButton"] button {
    background: rgba(0, 229, 255, 0.1);
    border: 1px solid #00e5ff;
    color: #00e5ff;
    font-family: 'Orbitron', sans-serif;
    letter-spacing: 2px;
    border-radius: 4px;
    transition: all 0.3s;
  }

  div[data-testid="stButton"] button:hover {
    background: rgba(0, 229, 255, 0.25);
    box-shadow: 0 0 20px rgba(0,229,255,0.4);
  }

  .stCheckbox label {
    color: #4dd0e1 !important;
    font-size: 0.85rem;
    letter-spacing: 1px;
  }

  .separator {
    border: none;
    border-top: 1px solid rgba(0, 229, 255, 0.15);
    margin: 16px 0;
  }

  .tail-badge {
    display: inline-block;
    background: rgba(0,229,255,0.15);
    border: 1px solid #00e5ff;
    color: #00e5ff;
    font-family: 'Orbitron', sans-serif;
    font-size: 1.1rem;
    padding: 6px 18px;
    border-radius: 4px;
    letter-spacing: 3px;
    box-shadow: 0 0 15px rgba(0,229,255,0.2);
  }

  .aircraft-type {
    color: #4dd0e1;
    font-size: 0.8rem;
    letter-spacing: 2px;
    margin-top: 4px;
  }
</style>
""", unsafe_allow_html=True)


# ── Constants ─────────────────────────────────────────────────────────────────
CALLSIGN = "D-ECJU"
ICAO24   = "3d0aee"   # wird dynamisch ermittelt
OPENSKY_URL = "https://opensky-network.org/api"

# ── Helper Functions ──────────────────────────────────────────────────────────

def fetch_by_callsign(callsign: str) -> dict | None:
    """Sucht Flugzeug über Callsign in OpenSky (alle Staaten)."""
    try:
        cs_padded = callsign.ljust(8)  # OpenSky braucht 8 Zeichen
        resp = requests.get(
            f"{OPENSKY_URL}/states/all",
            params={"callsign": cs_padded},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("states"):
                return parse_state(data["states"][0])
    except Exception:
        pass
    return None


def fetch_by_icao(icao24: str) -> dict | None:
    """Sucht Flugzeug direkt über ICAO24-Transponder-Code."""
    try:
        resp = requests.get(
            f"{OPENSKY_URL}/states/all",
            params={"icao24": icao24.lower()},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("states"):
                return parse_state(data["states"][0])
    except Exception:
        pass
    return None


def parse_state(s: list) -> dict:
    """Konvertiert OpenSky State-Vector in lesbares Dict."""
    return {
        "icao24":        s[0],
        "callsign":      (s[1] or "").strip(),
        "origin":        s[2],
        "time_position": s[3],
        "last_contact":  s[4],
        "longitude":     s[5],
        "latitude":      s[6],
        "baro_altitude": s[7],    # Meter
        "on_ground":     s[8],
        "velocity":      s[9],    # m/s
        "true_track":    s[10],   # Grad
        "vertical_rate": s[11],   # m/s
        "geo_altitude":  s[13],   # Meter
        "squawk":        s[14],
    }


def m_to_ft(m):
    if m is None: return "—"
    return f"{int(m * 3.28084):,} ft"

def ms_to_kts(ms):
    if ms is None: return "—"
    return f"{int(ms * 1.94384)} kts"

def ms_to_fpm(ms):
    if ms is None: return "—"
    val = int(ms * 196.85)
    sign = "+" if val >= 0 else ""
    return f"{sign}{val} fpm"

def format_time(ts):
    if ts is None: return "—"
    return datetime.utcfromtimestamp(ts).strftime("%H:%M:%S UTC")

def heading_arrow(deg):
    if deg is None: return "?"
    arrows = ["↑","↗","→","↘","↓","↙","←","↖"]
    idx = int((deg + 22.5) / 45) % 8
    return arrows[idx]


def build_map(lat, lon, track, altitude_m, callsign):
    """Erstellt eine Folium-Karte mit Flugzeug-Position."""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=10,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # Flugzeug-Icon mit Rotation
    icon_html = f"""
    <div style="
        transform: rotate({track or 0}deg);
        font-size: 28px;
        text-shadow: 0 0 8px #00e5ff, 0 0 16px rgba(0,229,255,0.5);
        filter: drop-shadow(0 0 6px #00e5ff);
    ">✈</div>
    """
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=icon_html, icon_size=(40, 40), icon_anchor=(20, 20)),
        popup=folium.Popup(
            f"<b>{callsign}</b><br>"
            f"Alt: {m_to_ft(altitude_m)}<br>"
            f"Heading: {int(track or 0)}°",
            max_width=200
        ),
    ).add_to(m)

    # Puls-Kreis
    folium.CircleMarker(
        location=[lat, lon],
        radius=12,
        color="#00e5ff",
        fill=True,
        fill_color="#00e5ff",
        fill_opacity=0.15,
        weight=1,
    ).add_to(m)

    return m


# ── UI Layout ─────────────────────────────────────────────────────────────────

# Header
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("<div style='font-size:3.5rem; text-align:center; margin-top:8px'>✈️</div>", unsafe_allow_html=True)
with col_title:
    st.markdown("<div class='title-glow'>FLIGHT TRACKER</div>", unsafe_allow_html=True)
    st.markdown(
        "<span class='tail-badge'>D-ECJU</span>&nbsp;&nbsp;"
        "<span class='aircraft-type'>CESSNA C172 · VFR TRACKER</span>",
        unsafe_allow_html=True
    )

st.markdown("<hr class='separator'>", unsafe_allow_html=True)

# Controls
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 3])
with ctrl_col1:
    refresh_btn = st.button("⟳  REFRESH NOW", use_container_width=True)
with ctrl_col2:
    auto_refresh = st.checkbox("AUTO-REFRESH (30 s)", value=False)
with ctrl_col3:
    icao_input = st.text_input(
        "ICAO24 (optional, z.B. 3dac5a)",
        placeholder="Leer lassen für Callsign-Suche",
        label_visibility="visible"
    ).strip().lower()

st.markdown("")

# ── Data Fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_aircraft_data(icao_override: str) -> dict | None:
    if icao_override:
        return fetch_by_icao(icao_override)
    return fetch_by_callsign(CALLSIGN)


if refresh_btn:
    st.cache_data.clear()

aircraft = get_aircraft_data(icao_input if icao_input else "")

# ── Display ───────────────────────────────────────────────────────────────────
if aircraft:
    lat  = aircraft["latitude"]
    lon  = aircraft["longitude"]
    alt  = aircraft["baro_altitude"]
    gs   = aircraft["velocity"]
    hdg  = aircraft["true_track"]
    vr   = aircraft["vertical_rate"]
    sqk  = aircraft["squawk"]
    gnd  = aircraft["on_ground"]

    # Status-Badge
    status_txt = "● ON GROUND" if gnd else "● AIRBORNE"
    status_cls = "status-offline" if gnd else "status-online"
    st.markdown(
        f"<div style='text-align:center; margin-bottom:16px'>"
        f"<span class='{status_cls}'>{status_txt}</span>"
        f"&nbsp;&nbsp;<span style='color:#4dd0e1;font-size:0.8rem'>LAST UPDATE: {format_time(aircraft['last_contact'])}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # Metriken
    m1, m2, m3, m4, m5 = st.columns(5)
    metrics = [
        (m1, "ALTITUDE",     m_to_ft(alt)),
        (m2, "GROUNDSPEED",  ms_to_kts(gs)),
        (m3, "HEADING",      f"{heading_arrow(hdg)} {int(hdg or 0)}°"),
        (m4, "VERT. RATE",   ms_to_fpm(vr)),
        (m5, "SQUAWK",       sqk or "—"),
    ]
    for col, label, val in metrics:
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-label'>{label}</div>"
                f"<div class='metric-value'>{val}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("")

    # Karte + Details nebeneinander
    map_col, info_col = st.columns([3, 1])

    with map_col:
        if lat and lon:
            fmap = build_map(lat, lon, hdg, alt, aircraft["callsign"])
            st_folium(fmap, width=None, height=480, use_container_width=True)
        else:
            st.warning("Keine Positionsdaten verfügbar.")

    with info_col:
        st.markdown("<h3 style='font-size:0.9rem'>DETAILS</h3>", unsafe_allow_html=True)
        details = [
            ("CALLSIGN",   aircraft["callsign"] or CALLSIGN),
            ("ICAO24",     aircraft["icao24"].upper()),
            ("ORIGIN CTY", aircraft["origin"] or "—"),
            ("LATITUDE",   f"{lat:.4f}°" if lat else "—"),
            ("LONGITUDE",  f"{lon:.4f}°" if lon else "—"),
            ("GEO ALT",    m_to_ft(aircraft["geo_altitude"])),
        ]
        for label, val in details:
            st.markdown(
                f"<div class='info-box'>"
                f"<span style='color:#4dd0e1;font-size:0.7rem;letter-spacing:1px'>{label}</span><br>"
                f"<span style='color:#e0f7fa'>{val}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

else:
    # Nicht online
    st.markdown("""
    <div style='
        text-align: center;
        padding: 60px 20px;
        border: 1px solid rgba(0,229,255,0.15);
        border-radius: 8px;
        margin: 20px 0;
        background: rgba(0,229,255,0.02);
    '>
        <div style='font-size:4rem; margin-bottom:16px; filter: grayscale(1) opacity(0.5)'>✈️</div>
        <div style='font-family:Orbitron,sans-serif; font-size:1.2rem; color:#546e7a; letter-spacing:3px'>
            D-ECJU — NOT IN RANGE
        </div>
        <div style='color:#37474f; font-size:0.8rem; margin-top:8px; letter-spacing:1px'>
            Das Flugzeug sendet kein ADS-B Signal oder ist nicht aktiv.<br>
            OpenSky erfasst nur aktive Transponder.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box' style='max-width:600px; margin:0 auto'>
    💡 <b>Hinweis:</b> C172 fliegen häufig ohne Mode-S Transponder oder nur mit Mode-C (kein ADS-B).
    Falls D-ECJU einen ADS-B Transponder hat, erscheint sie hier sobald sie fliegt.
    Du kannst den ICAO24-Code oben eintragen, falls du ihn kennst.
    </div>
    """, unsafe_allow_html=True)


# Footer
st.markdown("<hr class='separator'>", unsafe_allow_html=True)
st.markdown(
    "<div style='text-align:center; color:#37474f; font-size:0.7rem; letter-spacing:2px'>"
    "POWERED BY OPENSKY NETWORK · DATA DELAY ~10-15s · ADS-B ONLY"
    "</div>",
    unsafe_allow_html=True
)

# Auto-Refresh
if auto_refresh:
    time.sleep(30)
    st.rerun()
