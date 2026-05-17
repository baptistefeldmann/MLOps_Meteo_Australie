import pandas as pd
import os
import os.path as osp
import numpy as np
import json, argparse, glob, time
import logging, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from tqdm import tqdm

# Local modules
import formation_mlops.MLOps_Meteo_Australie.src.data.utils as utils

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data'))
JSON_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','stations_infos.json'))
MAX_LAG = 3

with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

logger = utils.get_logger()
logger.debug(PROJECT_ROOT)

def collect_inference_data(city:str):
    inference_folder = osp.join(DATA_FOLDER, 'inference')

    if city not in STATIONS_DATA.keys():
        logger.error('Unknown city name')
        raise ValueError(f'city name: {city} not in Stations database')
    
    station_info = STATIONS_DATA[city]
    station_date = datetime.now(ZoneInfo(station_info['timezone']))
    station_lag_date = station_date - timedelta(days=MAX_LAG)

    if station_date.strftime("%m") != station_lag_date.strftime("%m"):
        month_list = [station_date.strftime("%Y%m"), station_lag_date.strftime("%Y%m")]
    else:
        month_list = [station_date.strftime("%Y%m")]
    
    list_clean_report = []
    for yearmonth in month_list:
        logger.info(f'Process {city}:{yearmonth}')
        raw_file = utils.download_raw_report(city, yearmonth, inference_folder, force_save=True)
        processed_file = utils.cleaning_report(city, raw_file, inference_folder, force_save=True)
        list_clean_report.append(processed_file)
    
    if len(list_clean_report) > 1:
        logger.info('Merge all reports')
        list_df = [pd.read_csv(i) for i in list_clean_report]
        merge_df = pd.concat(list_df)

        merge_df['Date'] = pd.to_datetime(merge_df['Date'], errors='coerce')
        merge_df = merge_df.sort_values(by='Date')
        merge_df.to_csv(list_clean_report[0], sep=',', header=True, index=False, mode='w')
        
        os.remove(list_clean_report[1])
    
    logger.info('Create features')
    processed_file = list_clean_report[0]
    df = pd.read_csv(processed_file)
    df['Date'] = pd.to_datetime(df['Date'],errors="coerce")

    features = utils.CreateFeatures(df)
    features.build_features()
    last_row = features.df.iloc[-1].fillna(0)
    last_row.drop(['Date'], inplace=True)
    last_row_date = station_date.strftime("%Y-%m-%d")
    
    out_path = osp.join(inference_folder, f'{city}_{last_row_date}_weather.json')
    with open(out_path, 'w') as dst:
        json.dump(last_row.to_dict(), dst, indent=2)

    logger.info('Collect inference completed')
    return out_path

def collect_training_data():
    raw_folder = osp.join(DATA_FOLDER, 'raw')
    processed_folder = osp.join(DATA_FOLDER, 'processed')

    #Purge not_completed folder
    [os.remove(i) for i in glob.glob(osp.join(processed_folder, 'not_completed', 'clean_*.csv'))]
    
    center_city_date = datetime.now(ZoneInfo(STATIONS_DATA['AliceSprings']['timezone']))
    center_city_date_1month_before = center_city_date - relativedelta(months=1)
    center_city_date_2month_before = center_city_date - relativedelta(months=2)

    month_list = [center_city_date.strftime("%Y%m"),
                  center_city_date_1month_before.strftime("%Y%m"),
                  center_city_date_2month_before.strftime("%Y%m")]
    
    dict_clean_reports = {}
    for city in STATIONS_DATA.keys():
        logger.info(f'Process {city}')
        list_clean_report = []

        # process not completed month
        yearmonth = month_list[0]
        out_folder = osp.join(processed_folder, 'not_completed')
        try:
            raw_file = utils.download_raw_report(city, yearmonth, raw_folder)
            processed_file = utils.cleaning_report(city, raw_file, out_folder)
            list_clean_report.append(processed_file)
        except Exception as e:
            logger.warning(e)
        
        # processed completed months
        for yearmonth in month_list[1::]:
            out_folder = osp.join(processed_folder, yearmonth)
            os.makedirs(out_folder, exist_ok=True)

            try:
                raw_file = utils.download_raw_report(city, yearmonth, raw_folder)
                processed_file = utils.cleaning_report(city, raw_file, out_folder)
                list_clean_report.append(processed_file)
            except Exception as e:
                logger.warning(e)
        
        dict_clean_reports[city] = list_clean_report
    
    logger.info('Collect training data completed')
    return dict_clean_reports

def compute_training_features(processed_reports:dict, replace:bool=False):
    features_folder = osp.join(DATA_FOLDER, 'features')
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
        logger.info(f'{city} : {len(df)} -> {len(new_df)}')

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

    data_train_df.to_parquet(data_train_path, index=False)
    data_test_df.to_parquet(data_test_path, index=False)
    data_valid_df.to_parquet(data_valid_path, index=False)
    logger.info('Completed !')

##############
_description = f""" 
Collecte les données météo Australien depuis le site bom.gov.au

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--mode', type=str, required=True, choices=['inference','training'], help="Collecting mode")
parser.add_argument('--city', type=str, required=False, help="City name to get weather report, required for inference mode")
parser.add_argument('--replace', required=False, action='store_true', help="replace mode for features computing in training mode")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print(kwargs.city)
    
    logger.setLevel(getattr(logging,kwargs.verbose))

    if kwargs.mode == 'inference':
        if kwargs.city is None:
            raise ValueError('In inference mode, city is required')
        
        collect_inference_data(kwargs.city)
    
    else:
        # training mode
        dict_reports = collect_training_data()
        time.sleep(0.5)
        compute_training_features(dict_reports, kwargs.replace)
        time.sleep(0.5)

        train_path = osp.join(DATA_FOLDER, 'datasets', 'data_train.parquet')
        test_path = osp.join(DATA_FOLDER, 'datasets', 'data_test.parquet')
        valid_path = osp.join(DATA_FOLDER, 'datasets', 'data_valid.parquet')
        train_ratio = 0.75
        test_ratio = 0.2
        create_datasets(train_path, test_path, valid_path, train_ratio, test_ratio)
    
    print('Finished !')




