import os
import os.path as osp
import json, argparse, glob
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

# Local modules
from src.data import utils
# import utils

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

def collect_training_data():
    raw_folder = osp.join(DATA_FOLDER, 'raw')
    processed_folder = osp.join(DATA_FOLDER, 'processed')

    # Purge not_completed sub-folders
    [os.remove(i) for i in glob.glob(osp.join(raw_folder,'not_completed','*.csv'))]
    [os.remove(i) for i in glob.glob(osp.join(processed_folder,'not_completed','*.csv'))]
    
    center_city_date = datetime.now(ZoneInfo(STATIONS_DATA['AliceSprings']['timezone']))
    center_city_date_1month_before = center_city_date - relativedelta(months=1)
    # center_city_date_2month_before = center_city_date - relativedelta(months=2)
    # center_city_date_3month_before = center_city_date - relativedelta(months=3)
    # center_city_date_4month_before = center_city_date - relativedelta(months=4)

    month_list = [center_city_date.strftime("%Y%m"),
                  center_city_date_1month_before.strftime("%Y%m")]
    
    dict_clean_reports = {}
    processed_subfolder_notcompleted = osp.join(processed_folder, 'not_completed')
    raw_subfolder_notcompleted = osp.join(raw_folder, 'not_completed')
    os.makedirs(processed_subfolder_notcompleted, exist_ok=True)
    os.makedirs(raw_subfolder_notcompleted, exist_ok=True)

    for city in STATIONS_DATA.keys():
        logger.info(f'Process {city}')
        list_clean_report = []

        # process not completed month
        yearmonth = month_list[0]
        try:
            raw_file = utils.download_raw_report(city, yearmonth, raw_subfolder_notcompleted)
            processed_file = utils.cleaning_report(city, raw_file, processed_subfolder_notcompleted)
            list_clean_report.append(processed_file)
        except Exception as e:
            logger.warning(e)
        
        # processed completed months
        for yearmonth in month_list[1::]:
            processed_subfolder = osp.join(processed_folder, yearmonth)
            raw_subfolder = osp.join(raw_folder, yearmonth)
            os.makedirs(raw_subfolder, exist_ok=True)
            os.makedirs(processed_subfolder, exist_ok=True)

            try:
                raw_file = utils.download_raw_report(city, yearmonth, raw_subfolder)
                processed_file = utils.cleaning_report(city, raw_file, processed_subfolder)
                list_clean_report.append(processed_file)
            except Exception as e:
                logger.warning(e)
        
        dict_clean_reports[city] = list_clean_report
    
    logger.info('Collect training data completed')
    return dict_clean_reports

##############
_description = f""" 
Collecte les données météo Australien depuis le site bom.gov.au

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--verbose', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

if __name__ == '__main__':
    kwargs = parser.parse_args()
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    
    logger.setLevel(getattr(logging,kwargs.verbose))

    dict_reports = collect_training_data()

    with open(REPORTS_FILE,'w') as dst:
        json.dump(dict_reports, dst, indent=2)
    print('Finished')