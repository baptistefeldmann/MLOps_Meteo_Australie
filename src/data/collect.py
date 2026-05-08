import pandas as pd
import os
import os.path as osp
import numpy as np
import json, requests, argparse, glob, time
import logging, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta

def get_skiprows(pathfile):
    blank_line_index = None

    with open(pathfile, "r", encoding="latin-1") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        if not line.strip():
            blank_line_index = i
            break

    if blank_line_index is None:
        logger.error('No blank lines found in the file')
        raise ValueError

    return blank_line_index + 1

def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Set rasterio log level
    logger.propagate = False
    return logger

# %%
# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data'))
# RAW_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data','raw'))
# PROCESSED_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data','processed'))
JSON_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','stations_infos.json'))
URL_WEATHER = 'https://www.bom.gov.au/climate/dwo/{year_month}/text/{bom_id}.{year_month}.csv'
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_LAG = 3

with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

logger = get_logger()
logger.debug(PROJECT_ROOT)

def download_raw_report(city:str, yearmonth:str, out_folder:str):
    if city not in STATIONS_DATA.keys():
        logger.error('Unknown city name')
        raise ValueError(f'city name: {city} not in Stations database')
    
    if not len(yearmonth)==6 or not yearmonth[0:2]=='20':
        logger.error(f'Not valid time, expected YYYYMM format but got {yearmonth}')
        raise ValueError(f'{yearmonth}')
    
    station_info = STATIONS_DATA[city]
    if station_info['bom_id'] is None:
        logger.error(f'Invalid Bom Id for {city}')
        raise ValueError
    
    csv_url = URL_WEATHER.format(year_month=yearmonth, bom_id=station_info['bom_id'])

    temp_filename_split = osp.basename(csv_url).split('.')
    out_path = osp.join(out_folder, f'{temp_filename_split[0]}_{temp_filename_split[1]}.{temp_filename_split[2]}')

    if not osp.exists(out_path):
        logger.info('Download weather report')
        response = requests.get(csv_url, headers=HEADERS)
        response.raise_for_status()

        with open(out_path, "wb") as f:
            f.write(response.content)
    
    return out_path

def cleaning_report(city, csv_file:str, out_folder:str):
    if city not in STATIONS_DATA.keys():
        logger.error('Unknown city name')
        raise ValueError(f'city name: {city} not in Stations database')
    
    raw_cols = ['Date', 'Minimum temperature (°C)', 'Maximum temperature (°C)',
                'Rainfall (mm)', 'Evaporation (mm)', 'Sunshine (hours)',
                'Direction of maximum wind gust ', 'Speed of maximum wind gust (km/h)',
                'Time of maximum wind gust', '9am Temperature (°C)',
                '9am relative humidity (%)', '9am cloud amount (oktas)',
                '9am wind direction', '9am wind speed (km/h)', '9am MSL pressure (hPa)',
                '3pm Temperature (°C)', '3pm relative humidity (%)',
                '3pm cloud amount (oktas)', '3pm wind direction',
                '3pm wind speed (km/h)', '3pm MSL pressure (hPa)']

    dict_cols = {
            'Date':'datetime', 'MinTemp': 'float32', 'MaxTemp': 'float32', 'Rainfall': 'float32', 'Evaporation': 'float32',
            'Sunshine': 'float32', 'WindGustDir': 'string', 'WindGustSpeed': 'float32', 'TimeMaxWindGust': 'string',
            'Temp9am': 'float32', 'Humidity9am': 'Int16', 'Cloud9am': 'float32', 'WindDir9am': 'string',
            'WindSpeed9am': 'float32', 'Pressure9am': 'float32', 'Temp3pm': 'float32', 'Humidity3pm': 'Int16',
            'Cloud3pm': 'float32', 'WindDir3pm': 'string', 'WindSpeed3pm': 'float32', 'Pressure3pm': 'float32'
            }
    dict_raintoday = {0: 'No', 1: 'Yes'}

    logger.info('Cleaning weather report')
    skiprows_val = get_skiprows(csv_file)
    df = pd.read_csv(csv_file, delimiter=',', skiprows=skiprows_val, encoding='latin-1')
    df = df.drop(columns=df.columns[0])
    
    if all(df.columns == raw_cols):
        df.columns = dict_cols.keys()
    else:
        logger.warning(f'No perfect matches between the columns')
        
    for col,dtype in dict_cols.items():
        logger.debug(f'{col} {dtype}')
        if dtype in ('int16', 'float32'):
            df[col] = pd.to_numeric(df[col], errors='coerce').astype(dtype)
        elif dtype=='datetime':
            df[col] = pd.to_datetime(df[col], errors='coerce')
        else:
            df[col] = df[col].astype(dtype)
    
    df = df.replace(
        [pd.NA, None, "NaN", "nan", "NAN", "NA", "N/A", "", " ", "null", "None"],
        np.nan
    )
    df = df.drop(columns='TimeMaxWindGust')
    df['RainToday'] = df['Rainfall'].apply(lambda x: dict_raintoday.get(x>1, None))
    df['RainTomorrow'] = df['RainToday'].shift(-1)
    df['Location'] = [city] * len(df)

    filename = osp.basename(csv_file)
    out_file = osp.join(out_folder, f'clean_{filename}')

    if not osp.exists(out_file):
        df.to_csv(out_file, sep=',', header=True, index=False)
    return out_file

class CreateFeatures:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.dict_bool = {'No': 0, 'Yes': 1}
        self.direction_to_angle = {
            "N": 0.0, "NNE": 22.5, "NE": 45.0, "ENE": 67.5,
            "E": 90.0, "ESE": 112.5, "SE": 135.0, "SSE": 157.5,
            "S": 180.0, "SSW": 202.5, "SW": 225.0, "WSW": 247.5,
            "W": 270.0, "WNW": 292.5, "NW": 315.0, "NNW": 337.5
        }
    
    def build_features(self):
        date_col = 'Date'
        location_col = 'Location' 
        list_dir_cols = ['WindGustDir']
        list_lag_cols = ['WindGustDir_sin', 'WindGustDir_cos', 'MinTemp', 'MaxTemp', 'Rainfall',
                         'WindGustSpeed', 'Humidity9am', 'Pressure9am']

        self.df = self.df.sort_values(date_col)

        self.df['RainToday'] = self.df['RainToday'].apply(lambda x: self.dict_bool.get(x,np.nan))
        self.df['RainTomorrow'] = self.df['RainTomorrow'].apply(lambda x: self.dict_bool.get(x,np.nan))

        self.create_time_features(date_col)
        self.create_coords_features(location_col)
        self.create_sin_cos_features(list_dir_cols)
        self.create_lag_features(list_lag_cols, lags=[1,3]) # Update MAX_LAG if change lags
        # self.create_rolling_features(self, cols: List[str], windows: List[int]):

        list_cols_drop = [location_col] + list_dir_cols + \
            ['Evaporation', 'Sunshine', 'Cloud9am', 'Cloud3pm', 'WindDir9am', 'WindDir3pm']
        self.df.drop(list_cols_drop, inplace=True, axis=1)

    def create_time_features(self, date_col: str):
        self.df["dayofyear"] = self.df[date_col].dt.dayofyear

    def create_coords_features(self, location_col: str, latlong=None):
        if latlong is not None:
            self.df['latitude'] = latlong[0]
            self.df['longitude'] = latlong[1]
        else:
            self.df['latitude'] = self.df[location_col].apply(lambda x: STATIONS_DATA.get(x, {'latlong':[0,0]})['latlong'][0])
            self.df['longitude'] = self.df[location_col].apply(lambda x: STATIONS_DATA.get(x, {'latlong':[0,0]})['latlong'][1])
            self.df.loc[(self.df["latitude"] == 0) & (self.df["longitude"] == 0), ['latitude', 'longitude']] = np.nan
        
    def create_sin_cos_features(self, cols: list[str]):
        for col in cols:
            self.df[f'{col}_sin'] = self.df[col].apply(
                lambda x: np.sin(np.deg2rad(self.direction_to_angle.get(x,0)))
            )
            self.df[f'{col}_cos'] = self.df[col].apply(
                lambda x: np.cos(np.deg2rad(self.direction_to_angle.get(x,0)))
            )

    def create_lag_features(self, cols: list[str], lags: list[int]):
        for col in cols:
            for lag in lags:
                self.df[f"{col}_lag_{lag}"] = self.df[col].shift(lag)

    def create_rolling_features(self, cols: list[str], windows: list[int]):
        for col in cols:
            for window in windows:
                self.df[f"{col}_roll_mean_{window}"] = np.nanmean(self.df[col].rolling(window))
                self.df[f"{col}_roll_std_{window}"] = np.nanstd(self.df[col].rolling(window))

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
        raw_file = download_raw_report(city, yearmonth, inference_folder)
        processed_file = cleaning_report(city, raw_file, inference_folder)
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

    features = CreateFeatures(df)
    features.build_features()
    last_row = features.df.iloc[-1].fillna(0)
    last_row.drop(['Date'], inplace=True)
    last_row_date = station_date.strftime("%Y-%m-%d")
    
    out_path = osp.join(inference_folder, f'{city}_{last_row_date}_weather.json')
    with open(out_path, 'w') as dst:
        json.dump(last_row.to_dict(), dst, indent=2)

    logger.info('Collect inference completed')

def collect_training_data():
    raw_folder = osp.join(DATA_FOLDER, 'raw')
    processed_folder = osp.join(DATA_FOLDER, 'processed')
    
    center_city_date = datetime.now(ZoneInfo(STATIONS_DATA['AliceSprings']['timezone']))
    center_city_date_1month_before = center_city_date - relativedelta(months=1)
    month_list = [center_city_date.strftime("%Y%m"), center_city_date_1month_before.strftime("%Y%m")]
    
    for city in STATIONS_DATA.keys(): 
        logger.info(f'Process {city}')
        list_clean_report = []
        for yearmonth in month_list:
            try:
                raw_file = download_raw_report(city, yearmonth, raw_folder)
                processed_file = cleaning_report(city, raw_file, processed_folder)
                list_clean_report.append(processed_file)
            except Exception as e:
                logger.warning(e)
        
        if len(list_clean_report) > 0:
            logger.info('Merging reports')
            list_df = [pd.read_csv(i) for i in list_clean_report]
            merge_df = pd.concat(list_df)

            merge_df['Date'] = pd.to_datetime(merge_df['Date'], errors='coerce')
            merge_df = merge_df.sort_values(by='Date')
            merge_df.to_csv(list_clean_report[0], sep=',', header=True, index=False, mode='w')

            if len(list_clean_report) == 2:
                os.remove(list_clean_report[1])
    
    logger.info('Collect training data completed')

def compute_training_features(replace:bool=False):
    processed_folder = osp.join(DATA_FOLDER, 'processed')
    features_folder = osp.join(DATA_FOLDER, 'features')
    origin_data_file = osp.join(processed_folder,'weatherAUS.csv')
    list_files = glob.glob(osp.join(processed_folder, 'clean_*.csv'))
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

            features = CreateFeatures(extract_df)
            features.build_features()
            new_df = features.df.dropna()
            logger.info(f'{city} : {len(extract_df)} -> {len(new_df)}')

            if len(new_df) > 0:
                out_path = osp.join(features_folder, city + '.parquet')
                new_df.to_parquet(out_path, index=False)

                stations_infos_dict[city] = len(new_df)
    

    for filepath in list_files:
        logger.info(f'Processing {osp.basename(filepath)}')

        df = pd.read_csv(filepath)
        df['Date'] = pd.to_datetime(df['Date'],errors="coerce")
        city_name = df['Location'].values[0]

        features = CreateFeatures(df)
        features.build_features()
        new_df = features.df.dropna()
        logger.info(f'{osp.basename(filepath)} - {city_name} : {len(df)} -> {len(new_df)}')

        if len(new_df) == 0:
            continue

        city_file = osp.join(features_folder, city_name + '.parquet')
        if osp.exists(city_file):
            df_old = pd.read_parquet(city_file)

            # concat
            df = pd.concat([df_old, new_df], ignore_index=True)

            # éviter doublons (très important)
            df = df.drop_duplicates(subset=["Date"])
        else:
            df = new_df.copy()
        
        df.to_parquet(city_file, index=False)
        stations_infos_dict[city_name] = len(df)
    
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
Télécharge les données météo Australien depuis le site bom.gov.au

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
        # collect_training_data()
        time.sleep(0.5)
        compute_training_features(kwargs.replace)
    
    print('Finished !')