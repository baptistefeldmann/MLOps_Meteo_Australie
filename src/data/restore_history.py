"""
Restauration ponctuelle de l'historique perdu (incident du 2026-06-03).

Contexte : le pipeline a reconstruit `data/features` a partir de zero au lieu
d'accumuler, ce qui a reduit la base d'entrainement de ~120 000 a ~2 000 lignes.
L'ancienne version reste disponible dans DVC (commit 8a15fdf).

Ce script FUSIONNE l'ancienne base et l'actuelle par station :
  concat -> dedoublonnage sur `Date` -> tri chronologique
Aucune des deux n'est un sur-ensemble de l'autre, donc on ne perd rien.

Par defaut le script ne fait qu'afficher ce qu'il ferait (--apply pour ecrire).

Prerequis (extraction depuis DVC) :
    dvc get . data/features --rev 8a15fdf -o /tmp/features_old
    dvc get . data/processed/origin/weatherAUS.csv --rev 8a15fdf -o /tmp/weatherAUS.csv

Exemples :
    python -m src.data.restore_history --old-features /tmp/features_old          # simulation
    python -m src.data.restore_history --old-features /tmp/features_old --apply  # ecriture
"""
import argparse
import glob
import os
import os.path as osp
import shutil

import pandas as pd

PROJECT_ROOT = osp.abspath(osp.join(osp.dirname(__file__), "..", ".."))
FEATURES_DIR = osp.join(PROJECT_ROOT, "data", "features")
ORIGIN_DIR = osp.join(PROJECT_ROOT, "data", "processed", "origin")


def merge_station(old_path, cur_path):
    """Fusionne les deux versions d'une station (dedoublonnage par Date)."""
    frames = [pd.read_parquet(p) for p in (old_path, cur_path) if p and osp.exists(p)]
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    if "Date" in df.columns:
        df = df.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return df


def main():
    parser = argparse.ArgumentParser(description="Fusionne l'historique DVC recupere avec la base actuelle.")
    parser.add_argument("--old-features", required=True, help="Dossier contenant les parquets recuperes (dvc get)")
    parser.add_argument("--origin-csv", default=None, help="weatherAUS.csv recupere, a replacer dans data/processed/origin/")
    parser.add_argument("--apply", action="store_true", help="Ecrire reellement (sinon simulation)")
    args = parser.parse_args()

    old = {osp.basename(p): p for p in glob.glob(osp.join(args.old_features, "*.parquet"))}
    cur = {osp.basename(p): p for p in glob.glob(osp.join(FEATURES_DIR, "*.parquet"))}
    stations = sorted(set(old) | set(cur))
    if not stations:
        raise SystemExit("Aucun parquet trouve : verifier --old-features")

    print(f"{'station':<22}{'ancien':>9}{'actuel':>9}{'fusion':>9}   periode")
    tot_old = tot_cur = tot_new = 0
    for s in stations:
        n_old = len(pd.read_parquet(old[s])) if s in old else 0
        n_cur = len(pd.read_parquet(cur[s])) if s in cur else 0
        df = merge_station(old.get(s), cur.get(s))
        tot_old += n_old
        tot_cur += n_cur
        tot_new += len(df)
        periode = f"{str(df.Date.min())[:10]} -> {str(df.Date.max())[:10]}" if "Date" in df.columns and len(df) else ""
        print(f"{s[:-8]:<22}{n_old:>9}{n_cur:>9}{len(df):>9}   {periode}")
        if args.apply:
            df.to_parquet(osp.join(FEATURES_DIR, s), index=False)

    print(f"\n{'TOTAL':<22}{tot_old:>9}{tot_cur:>9}{tot_new:>9}")
    print(f"stations : ancien {len(old)} | actuel {len(cur)} | fusion {len(stations)}")

    if args.origin_csv:
        dst = osp.join(ORIGIN_DIR, "weatherAUS.csv")
        print(f"\norigin : {args.origin_csv} -> {dst}")
        if args.apply:
            os.makedirs(ORIGIN_DIR, exist_ok=True)
            shutil.copyfile(args.origin_csv, dst)

    print("\n" + ("ECRITURE EFFECTUEE." if args.apply else "SIMULATION — relancer avec --apply pour ecrire."))


if __name__ == "__main__":
    main()
