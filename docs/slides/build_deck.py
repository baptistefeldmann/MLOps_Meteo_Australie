# -*- coding: utf-8 -*-
"""
Generateur du deck de presentation technique du projet MLOps Meteo Australie.

Le .pptx n'est PAS versionne (fichier binaire lourd) : c'est ce script qui l'est.
Regenerer le deck avec :

    python3 docs/slides/build_deck.py [chemin/de/sortie.pptx]

Sortie par defaut : presentation_technique_mlops.pptx a la racine du depot.
Dependance : python-pptx  (pip install python-pptx)
"""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# ---------- palette ----------
NAVY="0E3A5F"; NAVY2="0B2A44"; BLUE="1C6E8C"; TEAL="2E8C9E"
AMBER="E8A33D"; AMBERD="C9822A"; INK="16283A"; MUTED="5E7284"
LIGHT="F1F5F8"; CARD="FFFFFF"; LINE="D8E2EA"; WHITE="FFFFFF"
HEAD="Cambria"; BODY="Calibri"
def C(h): return RGBColor.from_string(h)

prs = Presentation()
prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    f = s.background.fill; f.solid(); f.fore_color.rgb = C(bg)
    return s

def shape(s, mso, x,y,w,h, fill=None, line=None, line_w=1.0, radius=None, shadow=False):
    shp = s.shapes.add_shape(mso, Inches(x),Inches(y),Inches(w),Inches(h))
    if radius is not None and mso==MSO_SHAPE.ROUNDED_RECTANGLE:
        try: shp.adjustments[0]=radius
        except Exception: pass
    if fill is None: shp.fill.background()
    else: shp.fill.solid(); shp.fill.fore_color.rgb=C(fill)
    if line is None: shp.line.fill.background()
    else: shp.line.color.rgb=C(line); shp.line.width=Pt(line_w)
    if not shadow: shp.shadow.inherit=False
    return shp

def label(shp, text, size, color, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, font=BODY):
    tf=shp.text_frame; tf.word_wrap=True; tf.vertical_anchor=anchor
    for m in ('margin_left','margin_right','margin_top','margin_bottom'): setattr(tf,m,0)
    p=tf.paragraphs[0]; p.alignment=align
    r=p.add_run(); r.text=text; f=r.font
    f.size=Pt(size); f.bold=bold; f.name=font; f.color.rgb=C(color)

def tb(s, x,y,w,h, paras, size=14, color=INK, font=BODY, align=PP_ALIGN.LEFT,
       anchor=MSO_ANCHOR.TOP, ls=None, sa=None, wrap=True):
    box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h)); tf=box.text_frame
    tf.word_wrap=wrap; tf.vertical_anchor=anchor
    for m in ('margin_left','margin_right','margin_top','margin_bottom'): setattr(tf,m,0)
    if isinstance(paras,str): paras=[paras]
    for i,runs in enumerate(paras):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.alignment=align
        if ls: p.line_spacing=ls
        if sa is not None: p.space_after=Pt(sa)
        if isinstance(runs,str): runs=[(runs,{})]
        for txt,o in runs:
            r=p.add_run(); r.text=txt; f=r.font
            f.size=Pt(o.get('size',size)); f.bold=o.get('bold',False)
            f.italic=o.get('italic',False); f.name=o.get('font',font)
            f.color.rgb=C(o.get('color',color))
    return box

def oval(s,x,y,d,fill,line=None,lw=1.0): return shape(s,MSO_SHAPE.OVAL,x,y,d,d,fill=fill,line=line,line_w=lw)
def badge(s,x,y,d,txt,fill,tcol=WHITE,fs=14):
    o=oval(s,x,y,d,fill); label(o,str(txt),fs,tcol)
def arrow_r(s,x,y,w,color,h=0.16): shape(s,MSO_SHAPE.RIGHT_ARROW,x,y,w,h,fill=color)
def arrow_d(s,x,y,h,color,w=0.18): shape(s,MSO_SHAPE.DOWN_ARROW,x,y,w,h,fill=color)

def kicker(s,x,y,text,color): tb(s,x,y,11,0.3,[[(text.upper(),{'bold':True,'color':color,'size':12.5})]],size=12.5)
def title(s,x,y,text,color=INK,w=12.3): tb(s,x,y,w,0.85,[[(text,{'bold':True,'color':color,'font':HEAD,'size':31})]])

RR=MSO_SHAPE.ROUNDED_RECTANGLE; RECT=MSO_SHAPE.RECTANGLE

# ===================== S1 TITLE =====================
s=slide(NAVY2)
oval(s,9.7,-1.7,5.6,"123A56"); oval(s,11.4,3.7,4.3,"103F52"); oval(s,8.9,4.9,2.2,"12456A")
tb(s,0.75,1.55,9,0.4,[[("PRÉSENTATION TECHNIQUE",{'bold':True,'color':AMBER,'size':14})]])
tb(s,0.72,2.05,9.7,1.9,[[("MLOps — Prédiction météo",{'bold':True,'color':WHITE,'font':HEAD,'size':44})],
                        [("en Australie",{'bold':True,'color':WHITE,'font':HEAD,'size':44})]],ls=1.02)
tb(s,0.75,4.2,8.4,0.9,"« Pleuvra-t-il demain ? » — un système ML complet : de la donnée brute au service, industrialisé et reproductible.",
   size=16,color="C7D6E2",ls=1.15)
cx=0.75
for c in ["XGBoost","DVC","DagsHub","MLflow","Docker","FastAPI"]:
    w=0.35+len(c)*0.115
    ch=shape(s,RR,cx,5.5,w,0.42,fill="163C5C",line="2C557A",line_w=1,radius=0.5); label(ch,c,12.5,"CFE0EC")
    cx+=w+0.18
s.notes_slide.notes_text_frame.text="Présentation technique du projet MLOps de prédiction météo. Montrer les technos et justifier les choix."

# ===================== S1b CONTEXTE FORMATION =====================
s = slide(WHITE)
tb(s, 0.6, 0.5, 11, 0.3, [[("CONTEXTE · FORMATION", {'bold': True, 'color': TEAL, 'size': 12.5})]])
tb(s, 0.6, 0.85, 12.3, 0.85, [[("Un projet realise en formation MLOps".replace("realise", "réalisé"),
                               {'bold': True, 'color': INK, 'font': HEAD, 'size': 31})]])
shape(s, RR, 0.6, 1.95, 6.0, 2.2, fill=NAVY, radius=0.05)
tb(s, 0.95, 2.22, 5.3, 0.3, [[("ORGANISME DE FORMATION", {'bold': True, 'color': AMBER, 'size': 11.5})]])
tb(s, 0.95, 2.58, 5.3, 0.8, [[("Liora", {'bold': True, 'color': WHITE, 'font': HEAD, 'size': 40})]])
tb(s, 0.95, 3.42, 5.3, 0.45, [[("anciennement ", {'color': "BFD3E2", 'size': 14}),
                               ("DataScientest", {'bold': True, 'color': "BFD3E2", 'size': 14})]])
tb(s, 0.6, 4.5, 6.0, 1.8,
   [[("Le projet ", {'color': MUTED, 'size': 15}),
     ("MLOps Météo Australie", {'bold': True, 'color': INK, 'size': 15}),
     (" a été conçu et développé dans ce cadre : de la collecte automatisée des données "
      "jusqu'au monitoring du modèle en production.", {'color': MUTED, 'size': 15})]], ls=1.2)
_faits = [("6 mois", "Durée du parcours", BLUE),
          ("100 % distanciel", "Aucun présentiel", TEAL),
          ("Formation continue", "Suivie en parallèle d'une activité professionnelle", AMBERD),
          ("CPF · OPCO", "Dispositifs de financement mobilisés", NAVY)]
_x, _w, _y, _h, _gap = 6.95, 5.95, 1.95, 1.0, 0.12
for _t, _d, _c in _faits:
    shape(s, RR, _x, _y, _w, _h, fill=CARD, line=LINE, line_w=1, radius=0.1)
    oval(s, _x + 0.3, _y + 0.42, 0.18, _c)
    tb(s, _x + 0.68, _y + 0.16, _w - 1.0, 0.36, [[(_t, {'bold': True, 'color': INK, 'size': 16})]])
    tb(s, _x + 0.68, _y + 0.55, _w - 1.0, 0.36, [[(_d, {'color': MUTED, 'size': 12.5})]])
    _y += _h + _gap
tb(s, 0.6, 6.55, 12.1, 0.5,
   [[("Objectif de la formation : ", {'bold': True, 'color': AMBERD, 'size': 13}),
     ("industrialiser le cycle de vie d'un modèle de machine learning, "
      "de la donnée brute au service supervisé.", {'color': MUTED, 'size': 13})]],
   anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text = ("Contexte : formation MLOps chez Liora (ex-DataScientest). "
    "Formation continue, 100 % a distance, sur 6 mois, financee via CPF / OPCO. "
    "Ce projet en est la realisation pratique.")

# ===================== S2 CONTEXTE =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"01 · Contexte",TEAL); title(s,0.6,0.85,"Un projet MLOps, pas seulement un modèle")
tb(s,0.6,1.95,6.6,1.0,[[("Objectif métier. ",{'bold':True,'color':INK}),("Prédire s'il ",{'color':MUTED}),
   ("pleuvra demain",{'bold':True,'color':BLUE}),(" (RainTomorrow) pour chaque station → une classification binaire.",{'color':MUTED})]],
   size=15.5,ls=1.18)
tb(s,0.6,3.05,6.6,1.5,[[("Enjeu MLOps. ",{'bold':True,'color':INK}),("Au-delà de l'entraînement, ",{'color':MUTED}),
   ("industrialiser tout le cycle de vie",{'bold':True,'color':INK}),
   (" : collecte → entraînement → déploiement → monitoring, de façon automatisée, reproductible et versionnée.",{'color':MUTED})]],
   size=15.5,ls=1.18)
pil=[("Reproductible","Données & pipeline versionnés (DVC)",TEAL),
     ("Automatisé","Réentraînement mensuel (Airflow)",AMBER),
     ("Observable","Métriques & drift (Grafana / Evidently)",BLUE)]
py=4.75
for t,d,col in pil:
    oval(s,0.62,py+0.03,0.22,col)
    tb(s,0.98,py-0.05,6.4,0.4,[[(t+".  ",{'bold':True,'color':INK}),(d,{'color':MUTED})]],size=14,anchor=MSO_ANCHOR.MIDDLE)
    py+=0.55
stats=[("49","stations météo (Australie)"),("1 / jour","horizon de prédiction"),
       ("Binaire","pluie / pas de pluie"),("Mensuel","cycle de réentraînement")]
gx,gy,cw,chp,gap=7.55,1.95,2.5,2.05,0.25
for i,(a,b) in enumerate(stats):
    x=gx+(i%2)*(cw+gap); y=gy+(i//2)*(chp+gap)
    shape(s,RR,x,y,cw,chp,fill=(NAVY if i==0 else LIGHT),radius=0.08)
    tb(s,x+0.05,y+0.42,cw-0.1,0.8,[[(a,{'bold':True,'color':(WHITE if i==0 else BLUE),'font':HEAD,'size':34})]],align=PP_ALIGN.CENTER)
    tb(s,x+0.18,y+1.25,cw-0.36,0.6,b,size=12.5,color=("C7D6E2" if i==0 else MUTED),align=PP_ALIGN.CENTER,ls=1.05)
s.notes_slide.notes_text_frame.text="Le modèle n'est qu'une brique ; la valeur vient de l'automatisation, la reproductibilité et le monitoring."

# ===================== S3 ARCHITECTURE =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"02 · Architecture",TEAL); title(s,0.6,0.85,"Une architecture micro-services conteneurisée")
tb(s,0.6,1.62,12,0.4,[[("Chaque brique = 1 conteneur Docker isolé",{'bold':True,'color':INK}),
   (", orchestrés par un seul ",{'color':MUTED}),("docker-compose",{'bold':True,'color':BLUE}),(".",{'color':MUTED})]],size=14.5)
groups=[("Données & ML",BLUE,["collect_raw","create_features","create_datasets","training","drift_report"]),
        ("Serving",TEAL,["api — FastAPI","nginx — reverse proxy","interface — Streamlit"]),
        ("Orchestration",AMBERD,["airflow-webserver","airflow-scheduler","postgres"]),
        ("Monitoring",NAVY,["prometheus","grafana"])]
gx,gy,cw,chh,gp=0.6,2.15,3.55,2.15,0.22
for i,(t,col,items) in enumerate(groups):
    x=gx+(i%2)*(cw+gp); y=gy+(i//2)*(chh+gp)
    shape(s,RR,x,y,cw,chh,fill=CARD,line=LINE,line_w=1,radius=0.06)
    oval(s,x+0.22,y+0.24,0.2,col)
    tb(s,x+0.52,y+0.14,cw-0.7,0.4,[[(t,{'bold':True,'color':INK,'size':14.5})]],anchor=MSO_ANCHOR.MIDDLE)
    tb(s,x+0.52,y+0.62,cw-0.7,chh-0.72,[[(it,{'color':MUTED,'size':12})] for it in items],sa=3)
dx,dy,dw,dh=8.15,2.15,4.6,chh*2+gp
shape(s,RR,dx,dy,dw,dh,fill=NAVY,radius=0.05)
tb(s,dx+0.3,dy+0.25,dw-0.6,0.3,[[("PLATEFORME EXTERNE",{'bold':True,'color':AMBER,'size':11.5})]])
tb(s,dx+0.3,dy+0.55,dw-0.6,0.55,[[("DagsHub",{'bold':True,'color':WHITE,'font':HEAD,'size':24})]])
sub=[("Remote DVC (S3)","stockage versionné des données"),("MLflow","tracking d'expériences + Model Registry")]
sy=dy+1.35
for a,b in sub:
    shape(s,RR,dx+0.3,sy,dw-0.6,1.15,fill="14456B",radius=0.06)
    tb(s,dx+0.55,sy+0.16,dw-1.1,0.4,[[(a,{'bold':True,'color':WHITE,'size':15})]])
    tb(s,dx+0.55,sy+0.58,dw-1.1,0.45,b,size=12.5,color="BFD3E2",ls=1.05)
    sy+=1.32
tb(s,0.6,6.78,12.1,0.5,[[("Pourquoi ce choix ?  ",{'bold':True,'color':AMBERD}),
   ("isolation des dépendances (chaque service son image), responsabilités séparées, briques remplaçables et testables séparément.",{'color':MUTED})]],
   size=12.5,anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text="Chaque étape dans son conteneur : isolation des dépendances, séparation des responsabilités, remplaçabilité. DagsHub = plateforme externe centralisant données (DVC) et modèles (MLflow)."

# ===================== S4 DONNEES SOURCE =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"03 · Données · Source",TEAL); title(s,0.6,0.85,"D'où viennent les données ?")
rows=[("Source officielle","Bureau of Meteorology — bom.gov.au (« Daily Weather Observations »).",BLUE),
      ("Un CSV par station / par mois","URL templatée : /dwo/{AAAAMM}/text/{bom_id}.{AAAAMM}.csv",TEAL),
      ("Fenêtre de collecte","49 stations × 2 mois (mois courant + précédent) à chaque cycle.",AMBERD),
      ("Nettoyage","parsing, renommage & typage des colonnes, gestion des valeurs manquantes.",NAVY)]
y=1.95
for i,(t,d,col) in enumerate(rows):
    badge(s,0.62,y,0.34,i+1,col)
    tb(s,1.12,y-0.05,6.2,0.35,[[(t,{'bold':True,'color':INK,'size':14.5})]])
    tb(s,1.12,y+0.3,6.2,0.55,d,size=12.5,color=MUTED,ls=1.08)
    y+=1.02
fx,fw=7.75,5.0
shape(s,RR,fx,1.95,fw,4.05,fill=LIGHT,radius=0.05)
tb(s,fx+0.3,2.15,fw-0.6,0.3,[[("DU BRUT AUX DATASETS",{'bold':True,'color':TEAL,'size':11.5})]])
steps=[("CSV brut","BOM — data/raw","94A3B0"),("CSV nettoyé","data/processed",BLUE),
       (".parquet / station","data/features",TEAL),("train · test · valid","data/datasets",AMBER)]
sy=2.6
for i,(a,b,col) in enumerate(steps):
    shape(s,RR,fx+0.35,sy,fw-0.7,0.62,fill=CARD,line=LINE,line_w=1,radius=0.1)
    oval(s,fx+0.52,sy+0.19,0.24,col)
    tb(s,fx+0.9,sy+0.06,fw-1.35,0.28,[[(a,{'bold':True,'color':INK,'size':13.5})]])
    tb(s,fx+0.9,sy+0.33,fw-1.35,0.24,b,size=11,color=MUTED)
    if i<3: arrow_d(s,fx+0.6,sy+0.63,0.18,"B8C6D2",w=0.16)
    sy+=0.85
s.notes_slide.notes_text_frame.text="Données publiques du BOM australien, un CSV par station et par mois, récupéré par HTTP. Nettoyage puis transformation vers datasets Parquet."

# ===================== S5 CIBLE =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"03 · Données · Cible",TEAL); title(s,0.6,0.85,"Variables mesurées & construction de la cible")
shape(s,RR,0.6,1.95,6.05,4.15,fill=LIGHT,radius=0.05)
tb(s,0.9,2.15,5.5,0.3,[[("≈ 21 VARIABLES BRUTES / JOUR",{'bold':True,'color':BLUE,'size':11.5})]])
vars_=["Températures : min, max, 9h, 15h","Pluie (mm) · Évaporation · Ensoleillement",
       "Vent : direction & vitesse (rafale, 9h, 15h)","Humidité relative (9h / 15h)",
       "Pression MSL (9h / 15h) · Nébulosité"]
tb(s,0.95,2.6,5.4,3.3,[[("•  "+v,{'color':INK,'size':14})] for v in vars_],sa=9,ls=1.05)
tx,tw=6.95,5.8
tb(s,tx,1.95,tw,0.3,[[("LA CIBLE À PRÉDIRE",{'bold':True,'color':AMBERD,'size':11.5})]])
shape(s,RR,tx,2.35,tw,0.95,fill=CARD,line=LINE,line_w=1,radius=0.08)
tb(s,tx+0.3,2.52,tw-0.6,0.6,[[("RainToday  ",{'bold':True,'color':BLUE,'size':15}),("= Rainfall > 1 mm  →  Oui / Non",{'color':MUTED,'size':13.5})]],anchor=MSO_ANCHOR.MIDDLE,ls=1.05)
arrow_d(s,tx+0.5,3.35,0.22,AMBER,w=0.18)
shape(s,RR,tx,3.62,tw,0.95,fill=NAVY,radius=0.08)
tb(s,tx+0.3,3.79,tw-0.6,0.6,[[("RainTomorrow  ",{'bold':True,'color':WHITE,'size':15}),("= RainToday décalé de −1 jour",{'color':"C7D6E2",'size':13.5})]],anchor=MSO_ANCHOR.MIDDLE)
shape(s,RR,tx,4.9,tw,1.2,fill="FBF1DF",radius=0.06)
tb(s,tx+0.3,5.05,tw-0.6,0.95,[[("Classes déséquilibrées.  ",{'bold':True,'color':AMBERD}),
   ("Les jours de pluie sont minoritaires → géré à l'entraînement (pondération) et évalué avec la PR-AUC plutôt que l'accuracy.",{'color':"6B5836"})]],
   size=12.5,anchor=MSO_ANCHOR.MIDDLE,ls=1.12)
s.notes_slide.notes_text_frame.text="Colonnes brutes = météo du jour. Cible RainTomorrow = RainToday décalé d'un jour. Déséquilibre traité au training, mesuré via PR-AUC."

# ===================== S6 FEATURES =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"04 · Modèle · Features",TEAL); title(s,0.6,0.85,"Les features calculées pour le modèle")
feats=[("Temporel",BLUE,"dayofyear","capture la saisonnalité (jour de l'année)."),
       ("Géographique",TEAL,"latitude · longitude","localise chaque station météo."),
       ("Vent — encodage cyclique",AMBERD,"WindGustDir → sin / cos","évite la discontinuité 360° ≈ 0°."),
       ("Historique — lags",NAVY,"J-1 & J-3 sur 8 variables","temp, pluie, vent, humidité, pression.")]
gx,gy,cw,chh,gpx,gpy=0.6,1.95,6.0,1.9,0.2,0.22
for i,(t,col,code,desc) in enumerate(feats):
    x=gx+(i%2)*(cw+gpx); y=gy+(i//2)*(chh+gpy)
    shape(s,RR,x,y,cw,chh,fill=CARD,line=LINE,line_w=1,radius=0.06)
    o=oval(s,x+0.28,y+0.28,0.34,col); label(o,str(i+1),14,WHITE)
    tb(s,x+0.78,y+0.24,cw-1.0,0.4,[[(t,{'bold':True,'color':INK,'size':15.5})]],anchor=MSO_ANCHOR.MIDDLE)
    tb(s,x+0.78,y+0.78,cw-1.0,0.4,[[(code,{'bold':True,'color':col,'size':14})]])
    tb(s,x+0.78,y+1.16,cw-1.05,0.55,desc,size=12.5,color=MUTED,ls=1.08)
tb(s,0.6,6.35,12.1,0.5,[[("Idée directrice :  ",{'bold':True,'color':AMBERD}),
   ("saison, position, direction du vent (sans rupture d'angle) et surtout la ",{'color':MUTED}),
   ("dynamique récente",{'bold':True,'color':INK}),(" via les décalages temporels.",{'color':MUTED})]],
   size=13,anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text="Saisonnalité (dayofyear), position (lat/long), encodage cyclique sin/cos du vent, lags J-1/J-3 pour la dynamique récente."

# ===================== S7 XGBOOST =====================
s=slide(LIGHT)
kicker(s,0.6,0.5,"04 · Modèle · Algorithme",TEAL); title(s,0.6,0.85,"XGBoost : classification binaire de la pluie")
tb(s,0.6,1.9,6,0.3,[[("POURQUOI XGBOOST ?",{'bold':True,'color':BLUE,'size':11.5})]])
why=[("Données tabulaires","référence sur ce type de données hétérogènes.",BLUE),
     ("Non-linéarités & interactions","capturées nativement par les arbres boostés.",TEAL),
     ("Robuste & rapide","early stopping pour éviter le sur-apprentissage.",AMBER)]
y=2.35
for t,d,col in why:
    oval(s,0.64,y+0.02,0.22,col)
    tb(s,1.0,y-0.08,5.7,0.55,[[(t+".  ",{'bold':True,'color':INK}),(d,{'color':MUTED})]],size=14,anchor=MSO_ANCHOR.MIDDLE,ls=1.05)
    y+=0.75
shape(s,RR,0.6,4.85,6.15,1.35,fill=CARD,line=LINE,line_w=1,radius=0.07)
tb(s,0.85,5.02,5.7,1.0,[[("Déséquilibre :  ",{'bold':True,'color':AMBERD}),("scale_pos_weight",{'bold':True,'color':INK}),
   (" (pondération de la classe « pluie ») + ",{'color':MUTED}),("early stopping",{'bold':True,'color':INK}),(".",{'color':MUTED})]],
   size=13,anchor=MSO_ANCHOR.MIDDLE,ls=1.15)
rx,rw=7.15,5.6
shape(s,RR,rx,1.9,rw,1.85,fill=NAVY,radius=0.06)
tb(s,rx+0.3,2.1,rw-0.6,0.3,[[("MÉTRIQUE DE SÉLECTION",{'bold':True,'color':AMBER,'size':11.5})]])
tb(s,rx+0.3,2.42,rw-0.6,0.7,[[("PR-AUC",{'bold':True,'color':WHITE,'font':HEAD,'size':38})]])
tb(s,rx+0.32,3.15,rw-0.64,0.55,"Aire sous la courbe précision/rappel — bien plus fiable que l'accuracy quand les classes sont déséquilibrées.",
   size=12.5,color="C7D6E2",ls=1.1)
tb(s,rx,4.0,rw,0.3,[[("DÉCOUPAGE CHRONOLOGIQUE (par station)",{'bold':True,'color':BLUE,'size':11.5})]])
split=[("Train","75 %",BLUE),("Test","20 %",TEAL),("Valid","5 %",AMBER)]
sww=[(rw-0.4)*0.60,(rw-0.4)*0.28,(rw-0.4)*0.12]; sxx=rx
for i,(a,b,col) in enumerate(split):
    shape(s,RR,sxx,4.4,sww[i],0.75,fill=col,line=WHITE,line_w=1.5,radius=0.08)
    tb(s,sxx,4.5,sww[i],0.35,[[(b,{'bold':True,'color':WHITE,'size':15})]],align=PP_ALIGN.CENTER)
    tb(s,sxx,4.82,sww[i],0.28,[[(a,{'color':"F0F6FA",'size':11})]],align=PP_ALIGN.CENTER)
    sxx+=sww[i]+0.2
tb(s,rx,5.35,rw,0.6,[[("Le plus ancien → entraînement · le plus récent → validation (respecte le temps).",{'italic':True,'color':MUTED})]],size=12,ls=1.05)
s.notes_slide.notes_text_frame.text="XGBoost pour les données tabulaires. Déséquilibre : scale_pos_weight + early stopping. Sélection sur PR-AUC. Split chronologique par station."

# ===================== S8 DVC =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"05 · Pipeline · DVC",TEAL); title(s,0.6,0.85,"DVC : versionner données & pipeline comme du code")
stages=[("raw_processed","collect_raw",BLUE),("features","create_features",TEAL),("datasets","create_datasets",AMBERD)]
bx,by,bw,bhh,gap=0.6,2.05,3.55,1.15,0.62
for i,(t,d,col) in enumerate(stages):
    x=bx+i*(bw+gap)
    shape(s,RR,x,by,bw,bhh,fill=LIGHT,line=LINE,line_w=1,radius=0.08)
    badge(s,x+0.22,by+0.35,0.44,i+1,col)
    tb(s,x+0.8,by+0.24,bw-0.95,0.4,[[(t,{'bold':True,'color':INK,'size':15.5})]])
    tb(s,x+0.8,by+0.63,bw-0.95,0.35,d+".py",size=12,color=MUTED)
    if i<2: arrow_r(s,x+bw+0.2,by+bhh/2-0.08,0.24,AMBER)
tb(s,0.6,3.4,12,0.35,[[("Déclaré dans ",{'color':MUTED}),("src/pipelines/dvc.yaml",{'bold':True,'color':BLUE}),
   ("  —  une chaîne reproductible de bout en bout.",{'color':MUTED})]],size=13)
cmds=[("dvc repro",BLUE,"rejoue uniquement les étapes dont les entrées ont changé (cache intelligent)."),
      ("dvc push",TEAL,"envoie les gros fichiers vers le stockage distant (DagsHub S3)."),
      ("git + dvc.lock",AMBERD,"Git ne versionne que des pointeurs légers, pas les données.")]
cx,cy,cw,chh,cgp=0.6,4.0,3.95,2.0,0.2
for i,(t,col,d) in enumerate(cmds):
    x=cx+i*(cw+cgp)
    shape(s,RR,x,cy,cw,chh,fill=CARD,line=LINE,line_w=1,radius=0.06)
    b=shape(s,RR,x+0.28,cy+0.28,cw-0.56,0.5,fill=col,radius=0.12); label(b,t,14.5,WHITE,font="Consolas")
    tb(s,x+0.3,cy+0.95,cw-0.6,0.95,d,size=13,color=MUTED,ls=1.12)
tb(s,0.6,6.35,12.1,0.5,[[("Pourquoi DVC ?  ",{'bold':True,'color':AMBERD}),
   ("reproductibilité totale — on retrouve exactement les données ayant produit chaque modèle, sans stocker les gros fichiers dans Git.",{'color':MUTED})]],
   size=12.5,anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text="dvc.yaml = 3 étapes. dvc repro (cache), dvc push (DagsHub S3), Git ne garde que dvc.lock. Reproductibilité complète."

# ===================== S9 DAGSHUB + MLFLOW =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"05 · Pipeline · DagsHub + MLflow",TEAL); title(s,0.6,0.85,"DagsHub + MLflow : suivi et registre des modèles")
tb(s,0.6,1.9,6.2,0.3,[[("MLFLOW (hébergé sur DagsHub)",{'bold':True,'color':BLUE,'size':11.5})]])
ml=[("Tracking","params, métriques et modèle loggés à chaque run.",BLUE),
    ("Model Registry","modèle enregistré : XGBoost_WeatherAUS.",TEAL),
    ("Alias best_model","le challenger est comparé au meilleur (PR-AUC)…",AMBERD),
    ("Promotion","…et remplace best_model s'il est meilleur.",NAVY)]
y=2.35
for i,(t,d,col) in enumerate(ml):
    badge(s,0.62,y,0.34,i+1,col)
    tb(s,1.1,y-0.05,5.7,0.6,[[(t+".  ",{'bold':True,'color':INK}),(d,{'color':MUTED})]],size=13.5,anchor=MSO_ANCHOR.MIDDLE,ls=1.08)
    y+=0.92
rx,rw=7.1,5.65
shape(s,RR,rx,1.9,rw,2.15,fill=NAVY,radius=0.06)
tb(s,rx+0.3,2.1,rw-0.6,0.3,[[("DAGSHUB = 3 EN 1, AUTOUR DU REPO GIT",{'bold':True,'color':AMBER,'size':11.5})]])
trio=[("Git","code"),("DVC remote","données"),("MLflow","modèles")]
tww=(rw-0.6-0.4)/3; txx=rx+0.3
for a,b in trio:
    shape(s,RR,txx,2.5,tww,1.25,fill="14456B",line="2C6089",line_w=1,radius=0.08)
    tb(s,txx,2.72,tww,0.4,[[(a,{'bold':True,'color':WHITE,'size':14.5})]],align=PP_ALIGN.CENTER)
    tb(s,txx,3.16,tww,0.35,[[(b,{'color':AMBER,'size':12})]],align=PP_ALIGN.CENTER)
    txx+=tww+0.2
shape(s,RR,rx,4.25,rw,2.55,fill="FBF1DF",radius=0.05)
tb(s,rx+0.3,4.45,rw-0.6,0.3,[[("POURQUOI C'EST PRATIQUE ICI",{'bold':True,'color':AMBERD,'size':11.5})]])
why2=["Zéro infrastructure à héberger (pas de serveur MLflow, S3 ou base à gérer)",
      "Une seule authentification par token pour DVC + MLflow",
      "Gratuit et intégré au dépôt — idéal pour une petite équipe / formation"]
tb(s,rx+0.35,4.85,rw-0.65,1.9,[[("•  "+w,{'color':"5C4A2E",'size':12})] for w in why2],sa=7,ls=1.05)
s.notes_slide.notes_text_frame.text="MLflow : tracking + registry ; challenger comparé au best_model (PR-AUC). DagsHub réunit Git + DVC + MLflow : aucune infra, un token, gratuit."

# ===================== S10 PIPELINE COMPLET =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"06 · Pipeline complet",TEAL); title(s,0.6,0.85,"De l'entraînement à l'inférence")
l1=shape(s,RR,0.6,1.8,1.55,0.5,fill=BLUE,radius=0.12); label(l1,"ENTRAÎNEMENT",10.5,WHITE)
t1=[("Collecte BOM","49 stations"),("DVC repro","features → datasets"),("dvc push","→ DagsHub"),("Train XGBoost","fit + éval"),("MLflow Registry","best_model")]
y1,cw,chh,gap=2.5,2.28,1.05,0.14; x=0.6
for i,(a,b) in enumerate(t1):
    shape(s,RR,x,y1,cw,chh,fill=LIGHT,line=LINE,line_w=1,radius=0.08)
    tb(s,x+0.15,y1+0.16,cw-0.3,0.4,[[(a,{'bold':True,'color':INK,'size':12.5})]],align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)
    tb(s,x+0.12,y1+0.58,cw-0.24,0.38,b,size=10.5,color=MUTED,align=PP_ALIGN.CENTER)
    if i<4: arrow_r(s,x+cw+0.005,y1+chh/2-0.065,0.13,AMBER,h=0.13)
    x+=cw+gap
arrow_d(s,11.15,3.62,0.55,TEAL,w=0.2)
tb(s,9.9,3.72,1.2,0.35,[[("best_model",{'italic':True,'bold':True,'color':TEAL,'size':11})]],align=PP_ALIGN.RIGHT,anchor=MSO_ANCHOR.MIDDLE)
l2=shape(s,RR,0.6,4.35,1.55,0.5,fill=TEAL,radius=0.12); label(l2,"INFÉRENCE",10.5,WHITE)
t2=[("Collecte 1 ville","data/inference (JSON)"),("predict.py","charge best_model"),("API FastAPI","+ nginx (clé API)"),("Interface","Streamlit")]
y2,cw2,gap2=5.05,2.88,0.15; x=0.6
for i,(a,b) in enumerate(t2):
    shape(s,RR,x,y2,cw2,chh,fill="EAF3F5",line="CDE4E8",line_w=1,radius=0.08)
    tb(s,x+0.15,y2+0.16,cw2-0.3,0.4,[[(a,{'bold':True,'color':INK,'size':13})]],align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)
    tb(s,x+0.12,y2+0.58,cw2-0.24,0.38,b,size=11,color=MUTED,align=PP_ALIGN.CENTER)
    if i<3: arrow_r(s,x+cw2+0.01,y2+chh/2-0.065,0.13,TEAL,h=0.13)
    x+=cw2+gap2
tb(s,0.6,6.4,12.1,0.5,[[("Le fil rouge :  ",{'bold':True,'color':AMBERD}),
   ("le Model Registry (DagsHub) relie les deux mondes — l'entraînement publie ",{'color':MUTED}),
   ("best_model",{'bold':True,'color':INK}),(", l'inférence le télécharge.",{'color':MUTED})]],
   size=12.5,anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text="Haut : entraînement mensuel. Bas : inférence à la demande. Le Model Registry DagsHub relie les deux (best_model)."

# ===================== S11 SECTION 2 (divider) =====================
s=slide(NAVY2)
oval(s,-1.7,4.1,4.8,"103F52"); oval(s,11.3,-1.6,4.8,"123A56"); oval(s,10.2,5.0,2.2,"12456A")
tb(s,0.75,1.7,8,0.4,[[("PARTIE 2",{'bold':True,'color':AMBER,'size':14})]])
tb(s,0.72,2.15,12,1.0,[[("Orchestration, Monitoring & Serving",{'bold':True,'color':WHITE,'font':HEAD,'size':36})]])
tb(s,0.75,3.25,10.8,0.5,"Comment le système tourne, se surveille et s'expose — en continu.",size=15.5,color="C7D6E2")
pil2=[("Orchestration","Airflow · 2 DAGs · versioning Git auto",AMBER),
      ("Monitoring","Evidently · Prometheus / Grafana · Slack",TEAL),
      ("Serving","Nginx (API) · Streamlit (interface)",BLUE)]
px=0.75; pw=3.85; pgap=0.15
for i,(t,d,col) in enumerate(pil2):
    x=px+i*(pw+pgap)
    shape(s,RR,x,4.15,pw,1.75,fill="12324E",radius=0.06)
    oval(s,x+0.3,4.42,0.26,col)
    tb(s,x+0.3,4.85,pw-0.55,0.4,[[(t,{'bold':True,'color':WHITE,'size':16})]])
    tb(s,x+0.3,5.28,pw-0.55,0.5,d,size=12,color="AEC4D6",ls=1.05)
s.notes_slide.notes_text_frame.text="Section 2 : orchestration (Airflow), monitoring (Evidently + Prometheus/Grafana + Slack) et serving (Nginx + Streamlit)."

# ===================== S12 ORCHESTRATION (Airflow) =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"07 · Orchestration",TEAL); title(s,0.6,0.85,"Airflow : 2 DAGs pour automatiser le cycle")
shape(s,RR,0.6,1.85,7.35,1.8,fill=LIGHT,line=LINE,line_w=1,radius=0.05)
tb(s,0.85,2.02,7,0.35,[[("DAG 1 · ",{'bold':True,'color':INK,'size':14}),("data_pipeline",{'bold':True,'color':BLUE,'size':14}),("   (@monthly)",{'color':MUTED,'size':12})]])
tb(s,0.85,2.45,6.9,1.1,[[("raw_processed → features → datasets → ",{'color':INK,'size':12.5}),
   ("drift_report*",{'italic':True,'bold':True,'color':AMBERD,'size':12.5}),
   (" → dvc_push → git_commit_push",{'color':INK,'size':12.5})]],ls=1.3)
arrow_r(s,8.02,2.62,0.3,AMBER,h=0.18)
tb(s,7.9,2.3,0.55,0.28,[[("trigger",{'italic':True,'color':AMBERD,'size':9})]],align=PP_ALIGN.CENTER)
shape(s,RR,8.45,1.85,4.3,1.8,fill=LIGHT,line=LINE,line_w=1,radius=0.05)
tb(s,8.7,2.02,3.9,0.35,[[("DAG 2 · ",{'bold':True,'color':INK,'size':14}),("model_training",{'bold':True,'color':TEAL,'size':14})]])
tb(s,8.7,2.45,3.85,1.1,[[("train_model → ",{'color':INK,'size':12.5}),("update_reference*",{'italic':True,'bold':True,'color':AMBERD,'size':12.5}),(" → restart_api",{'color':INK,'size':12.5})]],ls=1.3)
whyd=[("Pourquoi 2 DAGs ?","Relancer l'un sans l'autre : juste collecter, ou juste réentraîner (ex. après un ajustement du modèle).",AMBERD),
      ("Versioning automatique","Le pipeline commit & push dvc.lock sur Git à chaque exécution.",TEAL),
      ("Exécution isolée","Chaque tâche tourne dans son propre conteneur (DockerOperator).",BLUE)]
cx=0.6; cw=3.95; cgap=0.2; cy=4.0
for i,(t,d,col) in enumerate(whyd):
    x=cx+i*(cw+cgap)
    shape(s,RR,x,cy,cw,2.05,fill=CARD,line=LINE,line_w=1,radius=0.06)
    oval(s,x+0.3,cy+0.3,0.26,col)
    tb(s,x+0.3,cy+0.7,cw-0.55,0.4,[[(t,{'bold':True,'color':INK,'size':14.5})]])
    tb(s,x+0.3,cy+1.12,cw-0.55,0.8,d,size=12,color=MUTED,ls=1.1)
tb(s,0.6,6.35,12.1,0.5,[[("* ",{'bold':True,'color':AMBERD}),("drift_report",{'italic':True,'color':INK}),(" et ",{'color':MUTED}),("update_reference",{'italic':True,'color':INK}),(" sont prévus — pas encore branchés dans les DAGs.",{'color':MUTED})]],size=12,anchor=MSO_ANCHOR.MIDDLE)
s.notes_slide.notes_text_frame.text="Airflow automatise le cycle. 2 DAGs (data_pipeline @monthly qui déclenche model_training) : on peut relancer l'un sans l'autre (juste collecter, ou juste réentraîner après un ajustement). Le pipeline versionne tout sur Git automatiquement. drift_report et update_reference sont prévus."

# ===================== S13 MONITORING · EVIDENTLY =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"08 · Monitoring · Drift",TEAL); title(s,0.6,0.85,"Evidently : suivi de la dérive des données")
tb(s,0.6,1.9,6,0.3,[[("CE QU'ON COMPARE",{'bold':True,'color':BLUE,'size':11.5})]])
shape(s,RR,0.6,2.3,5.9,0.95,fill=NAVY,radius=0.07)
tb(s,0.85,2.47,5.4,0.6,[[("Référence  ",{'bold':True,'color':WHITE,'size':14}),("snapshot figé du modèle déployé",{'color':"C7D6E2",'size':12.5})]],anchor=MSO_ANCHOR.MIDDLE,ls=1.05)
tb(s,3.15,3.32,0.7,0.3,[[("vs",{'italic':True,'bold':True,'color':MUTED,'size':13})]],align=PP_ALIGN.CENTER)
shape(s,RR,0.6,3.68,5.9,0.95,fill=LIGHT,line=LINE,line_w=1,radius=0.07)
tb(s,0.85,3.85,5.4,0.6,[[("Courant  ",{'bold':True,'color':BLUE,'size':14}),("nouveau dataset d'entraînement",{'color':MUTED,'size':12.5})]],anchor=MSO_ANCHOR.MIDDLE,ls=1.05)
tb(s,0.6,4.95,5.9,1.2,[[("Chaque mois, on mesure si les données ont ",{'color':MUTED,'size':12.5}),("dérivé",{'bold':True,'color':INK,'size':12.5}),(" par rapport à celles ayant entraîné le modèle en production.",{'color':MUTED,'size':12.5})]],ls=1.15)
tb(s,6.9,1.9,6,0.3,[[("LES MÉTRIQUES",{'bold':True,'color':AMBERD,'size':11.5})]])
mets=[("Data drift (features)","Test statistique par colonne → share_of_drifted_columns (% de colonnes driftées) ; dataset_drift = vrai si la part dépasse le seuil (déf. 50 %).",BLUE),
      ("Target drift","Dérive de la distribution de la cible RainTomorrow : target_drift_score + target_drift_detected.",TEAL),
      ("Sorties","Rapport HTML détaillé + métriques loggées dans MLflow → historique mois après mois.",AMBERD)]
my=2.3
for t,d,col in mets:
    shape(s,RR,6.9,my,5.85,1.3,fill=CARD,line=LINE,line_w=1,radius=0.06)
    oval(s,7.12,my+0.22,0.22,col)
    tb(s,7.45,my+0.17,5.1,0.35,[[(t,{'bold':True,'color':INK,'size':14})]])
    tb(s,7.45,my+0.54,5.1,0.7,d,size=11.5,color=MUTED,ls=1.08)
    my+=1.4
s.notes_slide.notes_text_frame.text="Evidently compare la référence (snapshot du modèle déployé) au dataset courant. Data drift = test statistique par feature, agrégé en part de colonnes driftées + flag dataset. Target drift = dérive de la cible. Sorties : rapport HTML + métriques dans MLflow pour le suivi mensuel."

# ===================== S14 MONITORING · PROMETHEUS/GRAFANA =====================
s=slide(WHITE)
kicker(s,0.6,0.5,"08 · Monitoring · Temps réel",TEAL); title(s,0.6,0.85,"Prometheus, Grafana & alertes Slack")
tb(s,0.6,1.62,12,0.35,[[("L'API est instrumentée (",{'color':MUTED,'size':13}),("/metrics",{'bold':True,'color':BLUE,'size':13}),(") → Prometheus scrape, Grafana affiche & alerte.",{'color':MUTED,'size':13})]])
tb(s,0.6,2.15,6,0.3,[[("LE DASHBOARD GRAFANA",{'bold':True,'color':BLUE,'size':11.5})]])
panels=["API Status (UP / DOWN)","Prédictions (total)","Taux d'échec (%)","Requêtes / s","Confidence (moy. & p95)","Prédictions pluie / pas pluie","Latence API p95"]
gx=0.6; gw=3.0; gh=0.55; ggx=0.2; ggy=0.18; gy=2.55
for i,p in enumerate(panels):
    x=gx+(i%2)*(gw+ggx); y=gy+(i//2)*(gh+ggy)
    shape(s,RR,x,y,gw,gh,fill=LIGHT,line=LINE,line_w=1,radius=0.14)
    oval(s,x+0.18,y+0.195,0.16,TEAL)
    tb(s,x+0.44,y,gw-0.55,gh,[[(p,{'color':INK,'size':11.5})]],anchor=MSO_ANCHOR.MIDDLE)
tb(s,6.95,2.15,6,0.3,[[("LES ALERTES → SLACK",{'bold':True,'color':AMBERD,'size':11.5})]])
alerts=[("API DOWN","up < 1 pendant 1 min","critique","C0392B"),
        ("Taux d'échec élevé","> 20 % de réponses 4xx / 5xx","warning",AMBERD)]
ay=2.55
for t,cond,sev,col in alerts:
    shape(s,RR,6.95,ay,5.8,1.15,fill=CARD,line=LINE,line_w=1,radius=0.06)
    oval(s,7.2,ay+0.44,0.26,col)
    tb(s,7.58,ay+0.2,4.95,0.35,[[(t,{'bold':True,'color':INK,'size':14.5})]])
    tb(s,7.58,ay+0.57,5.0,0.45,[[(cond,{'color':MUTED,'size':12}),("   ["+sev+"]",{'bold':True,'color':col,'size':11})]])
    ay+=1.3
shape(s,RR,6.95,ay+0.05,5.8,1.0,fill="FBF1DF",radius=0.06)
tb(s,7.2,ay+0.2,5.35,0.7,[[("Contact point Slack provisionné",{'bold':True,'color':AMBERD,'size':12.5}),(" — webhook depuis .env, règles versionnées en fichiers.",{'color':"6B5836",'size':12})]],anchor=MSO_ANCHOR.MIDDLE,ls=1.1)
s.notes_slide.notes_text_frame.text="L'API FastAPI expose /metrics (requêtes, statuts, latence + confidence des prédictions). Prometheus scrape, Grafana affiche le dashboard (statut, volumes, taux d'échec, confidence, latence). Deux alertes (API DOWN, taux d'échec) notifient sur Slack via un contact point provisionné."

# ===================== S15 SERVING (Nginx + Streamlit) =====================
s=slide(LIGHT)
kicker(s,0.6,0.5,"09 · Serving & accès utilisateur",TEAL); title(s,0.6,0.85,"Exposition : API sécurisée & interface")
shape(s,RR,0.6,1.95,5.95,4.25,fill=CARD,line=LINE,line_w=1,radius=0.05)
oval(s,0.9,2.28,0.32,BLUE)
tb(s,1.35,2.26,4.9,0.4,[[("Nginx",{'bold':True,'color':INK,'size':18})]],anchor=MSO_ANCHOR.MIDDLE)
tb(s,0.9,2.85,5.35,0.3,[[("REVERSE PROXY DEVANT L'API",{'bold':True,'color':BLUE,'size':10.5})]])
nginx_pts=["Point d'entrée unique (:8000 → api) : l'API n'est jamais exposée directement",
           "Applique une clé API (X-Api-Key) sur toutes les routes sauf /health",
           "Config par template : la clé est injectée depuis l'environnement (envsubst)",
           "Prépare l'évolution : TLS/HTTPS, rate limiting, logs & headers centralisés"]
tb(s,0.9,3.28,5.4,2.8,[[("•  "+p,{'color':INK,'size':12.5})] for p in nginx_pts],sa=11,ls=1.1)
shape(s,RR,6.75,1.95,5.95,4.25,fill=CARD,line=LINE,line_w=1,radius=0.05)
oval(s,7.05,2.28,0.32,TEAL)
tb(s,7.5,2.26,4.9,0.4,[[("Streamlit",{'bold':True,'color':INK,'size':18})]],anchor=MSO_ANCHOR.MIDDLE)
tb(s,7.05,2.85,5.35,0.3,[[("INTERFACE UTILISATEUR (:8501)",{'bold':True,'color':TEAL,'size':10.5})]])
st_pts=["Carte interactive : choix d'une ville → prédiction météo via l'API",
        "Page de connexion : mots de passe hachés (bcrypt) + cookie de session"]
tb(s,7.05,3.28,5.4,1.0,[[("•  "+p,{'color':INK,'size':12.5})] for p in st_pts],sa=11,ls=1.1)
shape(s,RR,7.05,4.4,5.35,0.72,fill=LIGHT,radius=0.09)
tb(s,7.28,4.5,5.0,0.52,[[("Rôle user  ",{'bold':True,'color':BLUE,'size':12.5}),("→ interface d'inférence",{'color':MUTED,'size':12})]],anchor=MSO_ANCHOR.MIDDLE)
shape(s,RR,7.05,5.2,5.35,0.85,fill=LIGHT,radius=0.09)
tb(s,7.28,5.3,5.0,0.65,[[("Rôle admin  ",{'bold':True,'color':AMBERD,'size':12.5}),("→ + liens Grafana & rapports de drift",{'color':MUTED,'size':12})]],anchor=MSO_ANCHOR.MIDDLE,ls=1.05)
s.notes_slide.notes_text_frame.text="Serving = la couche d'exposition. Nginx : reverse proxy qui protège l'API par clé API et masque le service ; prêt pour TLS/rate-limiting. Streamlit : interface (carte + prédiction) avec page de connexion (mots de passe hachés) et 2 rôles — user (inférence) et admin (+ Grafana et rapports de drift)."

# ===================== S16 CONCLUSION =====================
s=slide(NAVY2)
oval(s,-1.7,-1.7,4.8,"123A56"); oval(s,11.3,4.4,4.8,"103F52")
tb(s,0.75,1.45,8,0.4,[[("CONCLUSION",{'bold':True,'color':AMBER,'size':14})]])
tb(s,0.72,1.9,12,0.9,[[("Une boucle MLOps de bout en bout",{'bold':True,'color':WHITE,'font':HEAD,'size':34})]])
loop=["Données (BOM)","Entraînement (XGBoost)","Registry (DagsHub)","Serving (API + UI)","Monitoring (drift + métriques)"]
lx=0.75; lw=2.3; lgap=0.13; ly=3.15
for i,st in enumerate(loop):
    x=lx+i*(lw+lgap)
    shape(s,RR,x,ly,lw,0.95,fill="12324E",radius=0.08)
    tb(s,x+0.12,ly+0.1,lw-0.24,0.75,[[(st,{'bold':True,'color':WHITE,'size':11.5})]],align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)
    if i<len(loop)-1: arrow_r(s,x+lw+0.005,ly+0.39,0.115,AMBER,h=0.13)
tb(s,0.75,4.35,12,0.4,[[("→ le monitoring déclenche le réentraînement (Airflow) : la boucle se referme.",{'italic':True,'color':"C7D6E2",'size':13})]])
tb(s,0.75,5.05,11,0.3,[[("STACK TECHNIQUE",{'bold':True,'color':AMBER,'size':11})]])
chips2=["Docker Compose","DVC","DagsHub","MLflow","XGBoost","Airflow","Evidently","Prometheus","Grafana","Nginx","FastAPI","Streamlit"]
ccx=0.75; ccy=5.45
for c in chips2:
    w=0.3+len(c)*0.108
    if ccx+w>12.75: ccx=0.75; ccy+=0.55
    shape(s,RR,ccx,ccy,w,0.42,fill="163C5C",line="2C557A",line_w=1,radius=0.5)
    tb(s,ccx,ccy,w,0.42,[[(c,{'bold':True,'color':"CFE0EC",'size':11.5})]],align=PP_ALIGN.CENTER,anchor=MSO_ANCHOR.MIDDLE)
    ccx+=w+0.15
s.notes_slide.notes_text_frame.text="Conclusion : le projet forme une boucle MLOps complète — données, entraînement, registre, serving, monitoring — que le drift et Airflow referment via le réentraînement automatique."

import os.path as _osp
_default = _osp.join(_osp.dirname(_osp.dirname(_osp.dirname(_osp.abspath(__file__)))),
                     "presentation_technique_mlops.pptx")
out = sys.argv[1] if len(sys.argv) > 1 else _default
prs.save(out)
print("OK ->", out, "| slides:", len(prs.slides._sldIdLst))
