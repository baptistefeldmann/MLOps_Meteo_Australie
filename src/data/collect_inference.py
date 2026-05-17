import os
import os.path as osp
import pandas as pd
import json, argparse
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Local modules
import utils

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

##############
_description = f""" 
Collecte les données pour l'inférence

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--city', type=str, required=True, help="City name to get weather report, required for inference mode")
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    
    logger.setLevel(getattr(logging,kwargs.verbose))
        
    collect_inference_data(kwargs.city)
    print('Finished !')