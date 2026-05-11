import pandas as pd
import os
import os.path as osp
import numpy as np
import json, requests, logging, sys

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

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

JSON_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','stations_infos.json'))
URL_WEATHER = 'https://www.bom.gov.au/climate/dwo/{year_month}/text/{bom_id}.{year_month}.csv'
HEADERS = {"User-Agent": "Mozilla/5.0"}

with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

logger = get_logger()
logger.debug(PROJECT_ROOT)

def download_raw_report(city:str, yearmonth:str, out_folder:str, force_save:bool=False):
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

    if not osp.exists(out_path) or force_save:
        logger.info('Download weather report')
        response = requests.get(csv_url, headers=HEADERS)
        response.raise_for_status()

        with open(out_path, "wb") as f:
            f.write(response.content)
    
    return out_path

def cleaning_report(city, csv_file:str, out_folder:str, force_save:bool=False):
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

    if not osp.exists(out_file) or force_save:
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

