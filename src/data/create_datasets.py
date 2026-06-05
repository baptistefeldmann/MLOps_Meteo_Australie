import os
import os.path as osp
import pandas as pd
import json, argparse, glob
import logging
from tqdm import tqdm

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

with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

logger = utils.get_logger()
logger.debug(PROJECT_ROOT)

def create_datasets(data_train_path:str, data_test_path:str, data_valid_path:str,
                    train_ratio:float=0.75, test_ratio:float=0.2):
    logger.info('Create datasets')
    list_data_files = glob.glob(osp.join(DATA_FOLDER, 'features', '*.parquet'))
    list_train_df = []
    list_test_df = []
    list_valid_df = []

    for filepath in tqdm(list_data_files):
        df = pd.read_parquet(filepath)
        df.drop(['Date'], inplace=True, axis=1)
        idx_train = int(len(df) * train_ratio)
        idx_test = idx_train + int(len(df) * test_ratio)

        X_train, X_test, X_valid  = df.iloc[:idx_train], df.iloc[idx_train:idx_test], df.iloc[idx_test:]
        list_train_df.append(X_train)
        list_test_df.append(X_test)
        list_valid_df.append(X_valid)

    data_train_df = pd.concat(list_train_df, ignore_index=True)
    data_test_df = pd.concat(list_test_df, ignore_index=True)
    data_valid_df = pd.concat(list_valid_df, ignore_index=True)

    logger.info(f'Size Train: {len(data_train_df)}')
    logger.info(f'Size Test: {len(data_test_df)}')
    logger.info(f'Size Validation: {len(data_valid_df)}')

    data_train_df.to_parquet(data_train_path, index=False)
    data_test_df.to_parquet(data_test_path, index=False)
    data_valid_df.to_parquet(data_valid_path, index=False)
    logger.info('Completed !')

##############
_description = f""" 
A partir des base de données par station, créé les datasets d'entrainement

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--ratio_train', type=float, required=False, default=0.75, help="Training ratio per station")
parser.add_argument('--ratio_test', type=float, required=False, default=0.2, help="Testing ratio per station")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    
    logger.setLevel(getattr(logging,kwargs.verbose))

    os.makedirs(osp.join(DATA_FOLDER, 'datasets'), exist_ok=True)
    train_path = osp.join(DATA_FOLDER, 'datasets', 'data_train.parquet')
    test_path = osp.join(DATA_FOLDER, 'datasets', 'data_test.parquet')
    valid_path = osp.join(DATA_FOLDER, 'datasets', 'data_valid.parquet')
    create_datasets(train_path, test_path, valid_path, kwargs.ratio_train, kwargs.ratio_test)
    print('Finished !')