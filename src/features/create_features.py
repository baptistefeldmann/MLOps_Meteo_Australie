import os
import os.path as osp
import json, glob, logging, sys, argparse
import pandas as pd
import numpy as np

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
    
    logger.propagate = False
    return logger

# Define ENV variables
# They will soon be defined directly in the Dockerfile
try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except:
    PROJECT_ROOT = os.getcwd()

JSON_FILE = osp.abspath(osp.join(PROJECT_ROOT,'..','utils','stations_infos.json'))
with open(JSON_FILE) as src:
    STATIONS_DATA = json.load(src)

PREPROCESSED_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data','preprocessed'))
TRAINING_FOLDER = osp.abspath(osp.join(PROJECT_ROOT,'..','..','data','training_ready'))
TARGET_COL_NAME = "RainTomorrow"

logger = get_logger()
logger.debug(PROJECT_ROOT)

_description = f""" 
Génére les attributs pour le modèle + Compile les données et Créé les fichier X_train, X_test, y_train et y_test

"""
parser = argparse.ArgumentParser(description='\n'.join([_description]))
parser.add_argument('--split_train_test', type=float, required=False, default=0.8, help="Percent for splitting Train/Test")
parser.add_argument('--mode', type=str, required=False, default='INFO', choices=['WARNING','INFO','DEBUG'], help="Logger level")

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
        self.create_lag_features(list_lag_cols, lags=[1,3])
        # self.create_rolling_features(self, cols: List[str], windows: List[int]):

        list_cols_drop = [date_col, location_col] + list_dir_cols + \
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


def run(split_train_test=0.8, mode='INFO'):
    logger.setLevel(getattr(logging,mode))

    origin_dataset = osp.join(PREPROCESSED_FOLDER, 'weatherAUS.csv')
    list_files = glob.glob(osp.join(PREPROCESSED_FOLDER, 'clean_*.csv'))

    # Manage weatherAUS
    origin_df = pd.read_csv(origin_dataset)
    origin_df['Date'] = pd.to_datetime(origin_df['Date'],errors="coerce")
    list_city  = np.unique(origin_df['Location'])

    # # dataset validation - Not yet implemented
    # city_validation = 'MelbourneAirport'
    # extract_df = df[df['Location']==city_validation]

    # features = CreateFeatures(extract_df)
    # features.build_features()
    # data_valid_df = features.df.dropna()

    list_train_df = []
    list_test_df = []
    for city in list_city:
        # if city == city_validation:
        #     continue
        extract_df = origin_df[origin_df['Location']==city]

        features = CreateFeatures(extract_df)
        features.build_features()
        new_df = features.df.dropna()
        logger.info(f'{city} : {len(extract_df)} -> {len(new_df)}')
        
        if len(new_df) > 0:
            split = int(len(new_df) * split_train_test)

            X_train, X_test = new_df.iloc[:split], new_df.iloc[split:]
            list_train_df.append(X_train)
            list_test_df.append(X_test)
    
    # Manage other datafiles
    for csv_file in list_files:
        df = pd.read_csv(csv_file)
        df['Date'] = pd.to_datetime(df['Date'],errors="coerce")
        city_name = df['Location'].values[0]

        features = CreateFeatures(df)
        features.build_features()
        new_df = features.df.dropna()
        logger.info(f'{osp.basename(csv_file)} - {city_name} : {len(df)} -> {len(new_df)}')

        if len(new_df) > 0:
            split = int(len(new_df) * split_train_test)

            X_train, X_test = new_df.iloc[:split], new_df.iloc[split:]
            list_train_df.append(X_train)
            list_test_df.append(X_test)

    # Concatenate all data + create X/y train/test files
    data_train_df = pd.concat(list_train_df, ignore_index=True)
    data_test_df = pd.concat(list_test_df, ignore_index=True)
    logger.info(f'Size train: {len(data_train_df)}')
    logger.info(f'Size test: {len(data_test_df)}')

    y_train = data_train_df[TARGET_COL_NAME].astype(int)
    # y_val   = val_df[target_col].astype(int)
    y_test  = data_test_df[TARGET_COL_NAME].astype(int)

    X_train = data_train_df.drop(columns=TARGET_COL_NAME)
    # X_val   = val_df.drop(columns=target_col)
    X_test  = data_test_df.drop(columns=TARGET_COL_NAME)
    
    y_train.to_csv(osp.join(TRAINING_FOLDER, 'y_train.csv'))
    y_test.to_csv(osp.join(TRAINING_FOLDER, 'y_test.csv'))
    X_train.to_csv(osp.join(TRAINING_FOLDER, 'X_train.csv'))
    X_test.to_csv(osp.join(TRAINING_FOLDER, 'X_test.csv'))

if __name__ == "__main__":
    # Parse command line arguments
    kwargs = parser.parse_args()
    print("get Daily Weather Report command line arguments: \n")
    print(json.dumps(vars(kwargs), indent=1)) # Pretty print dictionary
    print()
    # Run
    run(**vars(kwargs))