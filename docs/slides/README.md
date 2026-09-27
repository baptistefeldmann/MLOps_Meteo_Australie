# Présentation technique

Le deck (`.pptx`) n'est **pas versionné** : c'est un binaire lourd, et il est
entièrement reconstructible. C'est le **générateur** qui est versionné, comme
pour les rapports de drift (artefact regénérable, pas stocké dans git).

## Régénérer le deck

```bash
pip install python-pptx
python3 docs/slides/build_deck.py
```

Sortie par défaut : `presentation_technique_mlops.pptx` à la racine du dépôt
(ignoré par `.gitignore`). Un chemin de sortie peut être passé en argument :

```bash
python3 docs/slides/build_deck.py /tmp/deck.pptx
```

## Contenu

17 slides. La slide 2 (`S1b CONTEXTE FORMATION`) présente le cadre du projet —
formation MLOps Liora (ex-DataScientest), formation continue, 100 % distanciel,
6 mois, financement CPF/OPCO. Elle porte un intitulé non numéroté, donc elle
n'interfère pas avec la numérotation `01 · … 09 ·` des sections techniques.

## Modifier une slide

Chaque slide est délimitée dans `build_deck.py` par un marqueur :

```python
# ===================== S4 DONNEES =====================
```

La charte (palette, polices) et les helpers (`slide`, `shape`, `tb`, `oval`)
sont définis en tête du fichier — les réutiliser pour rester cohérent.
