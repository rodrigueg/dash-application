import io
import base64
import pandas as pd
import numpy as np
from sklearn import preprocessing
import warnings


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    # Assume that the user uploaded a CSV file
    df = pd.DataFrame(pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=";", low_memory=False))
    df = df.replace(np.nan, "", regex=True)
    return df


def load_data_points(df, tukey):
    warnings.filterwarnings("ignore")

    standardized = False
    apply_tukey_filter = (tukey == ["oui"])

    data, labs, parameters = [], [], []

    for param in df.columns:
        data_i = np.array(df.loc[(df[param] != ""),param])
        if len(data_i) < 10: continue
        data_i = preprocessing.scale(data_i, 
                                     with_mean=standardized, with_std=standardized)
        #### avec filtre
        if apply_tukey_filter:
            q1, q3 = np.quantile(data_i, 0.25), np.quantile(data_i, 0.75)
            iqr = q3 - q1
            #print(q1, q3, iqr, q1 - 1.5*iqr, q3 - 1.5*iqr)
            in_, out_ = [], []
            for i in data_i:
                if (i < (q1 - 1.5*iqr)) or (i > (q3 + 1.5*iqr)):
                    out_.append(i)
                else: 
                    in_.append(i)
            data.append(in_)
            lab = "%s (%s valeurs)\nµ = %s, σ = %s" % (param,len(in_), round(np.mean(in_),2), round(np.std(in_),2))
        #### sans filtre
        else:
            data.append(data_i)
            lab = "%s (%s valeurs)\nµ = %s, σ = %s" % (param,len(data_i), round(np.mean(data_i),2), round(np.std(data_i),2))
        # (avec ou sans filtre)
        parameters.append(param)
        labs.append(lab)
    return (data, labs, parameters, apply_tukey_filter)

def get_dp_dm(df):
    warnings.filterwarnings("ignore")
    dp, dm = 0, 0
    for c in df.columns:
        dp += (df[c] != '').sum()
        dm += (df[c] == '').sum()
    return dp, dm
