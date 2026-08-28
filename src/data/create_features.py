import os
import os.path as osp
import numpy as np
import pandas as pd
import json, argparse, glob
import logging

# Local modules
from src.data import utils

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data'))
JSON_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','stations_infos.json'))
REPORTS_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','processed_reports.json'))

with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

logger = utils.get_logger()
logger.debug(PROJECT_ROOT)

def compute_training_features(processed_reports:dict, replace:bool=False, bootstrap:bool=False):
    features_folder = osp.join(DATA_FOLDER, 'features')
    os.makedirs(features_folder, exist_ok=True)

    # GARDE-FOU : sans base existante, ce script reconstruit tout a partir des
    # seuls mois qui viennent d'etre collectes -> l'historique accumule est
    # silencieusement perdu (incident du 2026-06-03 : 120 000 -> 2 000 lignes).
    # On refuse donc de repartir de zero sauf demande explicite.
    if not glob.glob(osp.join(features_folder, '*.parquet')) and not (replace or bootstrap):
        raise RuntimeError(
            f"Aucun parquet dans {features_folder} : le calcul repartirait de zero et "
            "ecraserait l'historique. Restaurer les donnees (dvc pull) ou, s'il s'agit "
            "d'une vraie initialisation, relancer avec --bootstrap (ou --replace)."
        )
    
    origin_data_file = osp.join(DATA_FOLDER, 'processed', 'origin', 'weatherAUS.csv')
    stations_infos_file = osp.join(features_folder, 'stations_data_infos.json')
    stations_infos_dict = {}

    if replace:
        # Replace database in case of CreateFeatures has change
        logger.info(f'Processing {osp.basename(origin_data_file)}')
        df = pd.read_csv(origin_data_file)
        df['Date'] = pd.to_datetime(df['Date'],errors="coerce")
        list_city  = np.unique(df['Location'])

        for city in list_city:
            extract_df = df[df['Location']==city]

            features = utils.CreateFeatures(extract_df)
            features.build_features()
            new_df = features.df.dropna()
            logger.info(f'{city} : {len(extract_df)} -> {len(new_df)}')

            if len(new_df) > 0:
                out_path = osp.join(features_folder, city + '.parquet')
                new_df.to_parquet(out_path, index=False)

                stations_infos_dict[city] = len(new_df)

    # Etat connu avant traitement : sert a detecter une station dont le parquet
    # a disparu (symptome de l'incident de perte d'historique).
    stations_infos_file_start = osp.join(features_folder, 'stations_data_infos.json')
    stations_infos_origin_at_start = {}
    if osp.exists(stations_infos_file_start):
        with open(stations_infos_file_start) as src:
            stations_infos_origin_at_start = json.load(src)

    for city, list_paths in processed_reports.items():
        if len(list_paths) == 0:
            continue

        logger.info(f'Processing {city}')
        list_df = [pd.read_csv(i) for i in list_paths]
        merge_df = pd.concat(list_df)

        merge_df['Date'] = pd.to_datetime(merge_df['Date'], errors='coerce')
        merge_df = merge_df.sort_values(by='Date')

        logger.info('Create features')
        features = utils.CreateFeatures(merge_df)
        features.build_features()
        new_df = features.df.dropna()
        logger.info(f'{city} : {len(merge_df)} -> {len(new_df)}')

        if len(new_df) == 0:
            continue

        city_file = osp.join(features_folder, city + '.parquet')
        if osp.exists(city_file):
            df_old = pd.read_parquet(city_file)

            # concat
            df = pd.concat([df_old, new_df], ignore_index=True)

            # éviter doublons (très important)
            df = df.drop_duplicates(subset=["Date"])
        else:
            if city in stations_infos_origin_at_start:
                logger.warning(
                    f"{city} : parquet absent alors que la station comptait "
                    f"{stations_infos_origin_at_start[city]} lignes -> reconstruction depuis zero"
                )
            df = new_df.copy()
        
        df.to_parquet(city_file, index=False)
        stations_infos_dict[city] = len(df)
    
    # Update stations data infos
    logger.info('Update stations data infos')
    if osp.exists(stations_infos_file):
        with open(stations_infos_file) as src:
            stations_infos_origin = json.load(src)
        
        stations_infos_origin.update(stations_infos_dict)
    else:
        stations_infos_origin = stations_infos_dict
    
    with open(stations_infos_file,'w') as dst:
        json.dump(stations_infos_origin, dst, indent=2)
    
    logger.info('Features computing completed')

##############
_description = f""" 
Calcul les features pour chaque station

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--replace', required=False, action='store_true', help="replace mode for features computing in training mode")
parser.add_argument('--bootstrap', required=False, action='store_true', help="autorise une reconstruction depuis zero (aucune base existante)")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    
    logger.setLevel(getattr(logging,kwargs.verbose))

    with open(REPORTS_FILE) as src:
        dict_reports = json.load(src)
    
    compute_training_features(dict_reports, kwargs.replace, kwargs.bootstrap)
    print('Finished !')