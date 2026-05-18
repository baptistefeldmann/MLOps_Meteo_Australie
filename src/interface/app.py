import os
import os.path as osp
import json, re
import folium
import streamlit as st
from streamlit_folium import st_folium

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

STATIONS_FILE = osp.join(PROJECT_ROOT,'..','utils','stations_infos.json')

def camelCase2Space(string):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', string)

# Configuration de la page en mode "large" pour bien profiter de la carte
st.set_page_config(page_title="Cartographie POI", layout="wide")

st.title("📍 Cartographie et Sélection de Points d'Intérêt")
st.write("Visualisez vos points et sélectionnez-les pour interagir.")

# 1. Chargement des données JSON
@st.cache_data
def load_poi():
    with open(STATIONS_FILE) as src:
        stations_data = json.load(src)
    return stations_data

pois = load_poi()

# --- SIDEBAR (Barre latérale) ---
with st.sidebar:
    st.header("⚙️ Options & Liste")
    
    # Permet de choisir un point aussi par une liste déroulante
    liste_noms = [camelCase2Space(key) for key,value in pois.items()]
    point_selectionne_liste = st.selectbox("Sélectionner un point via la liste :", ["Aucun"] + liste_noms)
    
    st.divider()
    
    # Ton futur bouton météo (prêt pour la suite)
    st.subheader("🌤️ Prévisions")
    if st.button("Consulter la météo du lendemain", use_container_width=True):
        st.info("Simulation : La requête API météo sera implémentée ici plus tard ! 😉")


# --- ZONE CENTRALE ---
col_carte, col_details = st.columns([3, 1])

# Initialisation de la variable qui stockera le point choisi (soit via carte, soit via liste)
poi_final = None

with col_carte:
    st.subheader("Carte Interactive")
    
    # Création de la carte centrée
    center_city = pois['AliceSprings']
    m = folium.Map(location=center_city['latlong'], zoom_start=5)
    icon_pluie = folium.Icon(color="blue", icon="cloud-showers-heavy", prefix="fa")
    
    # Ajout des marqueurs
    for key,value in pois.items():
        coords = value['latlong']
        folium.Marker(
            location=[coords[0], coords[1]],
            popup=camelCase2Space(key),
            tooltip=camelCase2Space(key),
            icon=icon_pluie
        ).add_to(m)
    
    # Affichage de la carte
    map_data = st_folium(m, width="100%", height=750, returned_objects=["last_object_clicked"])

# --- LOGIQUE DE SÉLECTION ---
key_final = None
# Cas 1 : L'utilisateur a cliqué sur la carte
if map_data and map_data.get("last_object_clicked"):
    click_lat = map_data["last_object_clicked"]["lat"]
    click_lon = map_data["last_object_clicked"]["lng"]
    for key,value in pois.items():
        coords = value['latlong']
        if round(coords[0], 4) == round(click_lat, 4) and round(coords[1], 4) == round(click_lon, 4):
            key_final = key
            break

# Cas 2 : L'utilisateur a choisi via la liste déroulante (écrase le clic carte pour l'exemple)
if point_selectionne_liste != "Aucun":
    for key,value in pois.items():
        if key == point_selectionne_liste:
            key_final = key
            break


# --- AFFICHAGE DES DÉTAILS ---
with col_details:
    st.subheader("Détails")
    
    if key_final:
        st.markdown(f"### {key_final}")
        st.markdown(f"**BOM id :** `{pois[key_final]['bom_id']}`")
        st.markdown(f"**Latitude :** `{pois[key_final]['latlong'][0]}`")
        st.markdown(f"**Longitude :** `{pois[key_final]['latlong'][1]}`")
    else:
        st.info("Veuillez sélectionner un point d'intérêt sur la carte ou dans la liste.")