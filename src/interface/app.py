import os
import os.path as osp
from dotenv import load_dotenv
import json, re
import folium
import streamlit as st
from streamlit_folium import st_folium
import requests
import glob
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
import streamlit.components.v1 as components

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

STATIONS_FILE = osp.join(PROJECT_ROOT,'..','utils','stations_infos.json')
CONFIG_FILE = osp.join(PROJECT_ROOT, 'config.yaml')
DRIFT_DIR = osp.abspath(osp.join(PROJECT_ROOT, '..', '..', 'reports', 'drift'))
GRAFANA_URL = os.getenv('GRAFANA_URL', 'http://localhost:3000')
EVIDENTLY_URL = os.getenv('EVIDENTLY_URL', 'http://localhost:8888')

load_dotenv()

def camelCase2Space(string):
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', string)

def request_predict(city):
    headers = {
        "Content-Type": "application/json",
        "x-api-key": os.environ['API_KEY']
    }
    payload = {'city':city}

    response = requests.post(
        os.getenv('API_PREDICTION_URL'),
        json=payload,
        headers=headers,
        timeout=15
        )
    response.raise_for_status()
    return response.json()

# Configuration de la page en mode "large" pour bien profiter de la carte
st.set_page_config(page_title="Cartographie POI", layout="wide")

# ---------------- Authentification (login + rôles) ----------------
with open(CONFIG_FILE) as _f:
    _config = yaml.load(_f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    _config["credentials"],
    _config["cookie"]["name"],
    _config["cookie"]["key"],
    _config["cookie"]["expiry_days"],
    auto_hash=False,   # les mots de passe sont déjà hachés dans config.yaml
)
authenticator.login(location="main")

_auth_status = st.session_state.get("authentication_status")
if _auth_status is False:
    st.error("Nom d'utilisateur ou mot de passe incorrect.")
    st.stop()
if _auth_status is None:
    st.info("Veuillez vous connecter pour accéder à l'interface.")
    st.stop()

# --- Utilisateur authentifié ---
username = st.session_state.get("username")
name = st.session_state.get("name")
role = _config["credentials"]["usernames"].get(username, {}).get("role", "user")

with st.sidebar:
    authenticator.logout("Déconnexion", "sidebar")
    st.caption(f"Connecté : {name} · rôle : **{role}**")
    st.divider()
# ------------------------------------------------------------------

st.title("📍 Cartographie et Sélection de Points d'Intérêt")
st.write("Visualisez vos points et sélectionnez-les pour interagir.")

# --- Espace réservé aux administrateurs ---
if role == "admin":
    with st.expander("🔧 Espace admin — monitoring & rapports de drift", expanded=False):
        col_admin_a, col_admin_b = st.columns(2)
        with col_admin_a:
            st.markdown("**Monitoring**")
            st.link_button("📊 Ouvrir Grafana", GRAFANA_URL, use_container_width=True)
            st.link_button("📈 Ouvrir Evidently", EVIDENTLY_URL, use_container_width=True)
        with col_admin_b:
            st.markdown("**Rapports de drift (Evidently)**")
            _drift_reports = sorted(glob.glob(osp.join(DRIFT_DIR, "*.html")), reverse=True)
            if _drift_reports:
                _choix = st.selectbox("Choisir un rapport", [osp.basename(r) for r in _drift_reports])
                _chemin = osp.join(DRIFT_DIR, _choix)
                _poids = osp.getsize(_chemin) / 1e6
                st.caption(f"{_poids:.1f} Mo — préférer l'UI Evidently pour la consultation courante.")
                # ATTENTION : le contenu d'un expander est execute meme replie.
                # Un rapport Evidently pese plusieurs Mo : on ne le charge donc
                # QUE sur demande explicite, sinon chaque rerun transfere des Mo
                # inutiles vers le navigateur (page qui semble figee).
                if st.checkbox("Charger ce rapport", key="load_drift_report"):
                    with open(_chemin, "r", encoding="utf-8") as _rf:
                        _rapport_html = _rf.read()
                    st.download_button("⬇️ Télécharger", _rapport_html, file_name=_choix, mime="text/html")
                    components.html(_rapport_html, height=600, scrolling=True)
            else:
                st.info("Aucun rapport de drift pour l'instant (lance `docker compose run --rm drift`).")

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
    weather_button_clicked = st.button("Consulter la météo du lendemain", use_container_width=True)
    # st.info("Simulation : La requête API météo sera implémentée ici plus tard ! 😉")

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

#--- Prédiction Météo
if weather_button_clicked:
    if key_final:
        with st.spinner(f'Prédiction en cours pour {camelCase2Space(key_final)}...'):
            result = request_predict(key_final)

        st.session_state["last_pred"] = {
            "station": key_final,
            "resultat": result,
        }
    else:
        st.session_state["last_pred"] = None
        st.sidebar.warning("Veuillez d'abord sélectionner un point d'intérêt (carte ou liste).")

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

    weather_prediction = st.session_state.get('last_pred')
    if weather_prediction and weather_prediction.get('station') == key_final:
        st.divider()
        st.subheader("🌧️ Prévision du lendemain")
        resultat = weather_prediction["resultat"]
        if resultat['status']=='success':
            st.success("Prédiction reçue !")

            if resultat['result']['prediction'] == 'Pas de pluie demain':
                st.markdown(f"### ☀️ Pas de pluie prévue demain pour {camelCase2Space(key_final)}")
            else:
                st.markdown(f"### 🌧️ Pluie prévue demain pour {camelCase2Space(key_final)}")

            st.metric("Probabilité de pluie", f"{resultat['result']['rain_probability'] * 100:.1f} %")
        else:
            st.error(f"Erreur lors de la requête à l'API: {resultat}")