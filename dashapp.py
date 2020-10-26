import io
import os
import datetime
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table as dt
import warnings
from sklearn import preprocessing
import plotly.express as px
import plotly.graph_objects as go
import base64
import pandas as pd
import numpy as np
import json
import multiprocessing as mp


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
PARAMETRES = pd.DataFrame(pd.read_csv("data/parametres.csv", sep=";", encoding="utf-8"))
PARAMETRES = list(PARAMETRES["Parametre"])

FILTER1 = "RegionHydro"
FILTER2 = "Riviere"


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = "Rodrigue GOVAN x ISEA"
app.layout = html.Div([
    
    dcc.Upload(
        id='DATA',
        children=html.Div([
            html.A("Insérez la matrice statistique")
        ]),
        style={
            'width': 'calc(98vw)',
            'height': '75%',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),

    html.Div(id='myDataFrame',
             style={'display':'none'}),
    
    html.Div(id='uploadedText',
             style={'text-align':'center',
                    'font-size':'20px',
                    'margin-bottom':'5px'}),
    html.Div(
        className="row", children=[
            html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='ID1', # IDPrelevement/Site/Riviere
                    options=[],
                    value=[],
                    clearable=True,
                    searchable=True,
                    multi=True,
                    placeholder="Filtre par %s" %FILTER1,
                )], style={'width':'35%', 'margin-left':"10px"})
            , html.Div(className='six columns', children=[
                dcc.Dropdown(
                    id='ID2', # HER
                    options=[],
                    value=[],  # [![enter image description here][1]][1]
                    clearable=True,
                    searchable=True,
                    multi=True,
                    placeholder="Filtre par %s" %FILTER2,
                )], style={'width':'65%'})
        ], style={'display':'flex',
                  'width': 'calc(98.5vw)'}),

    html.Hr(style={'margin-bottom':'-1px'}),

    html.P("Appliquer le filtre de Tukey",
           style={"margin-left":"25px"}),
    
    dcc.RadioItems(id="tukey",
                   options=[{"label":"Oui", "value":"oui"},
                            {"label":"Non", "value":"non"}],
                   value="oui",
                   style={"margin-left":"25px"},
                   labelStyle={'display': 'inline-block'}),
    
    dcc.Graph(id='myBoxplot',
              style={'height':'calc(74.5vh)',
                     'width':'calc(98vw)'}),
    html.Footer("© %s, Rodrigue GOVAN — ISEA. Tous droits réservés." % datetime.datetime.now().year,
                style={'font-style':'italic'})
])

def load_data_points(df, tukey):
    warnings.filterwarnings("ignore")

    standardized = False
    apply_tukey_filter = (tukey == "oui")

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

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    # Assume that the user uploaded a CSV file
    df = pd.DataFrame(pd.read_csv(io.StringIO(decoded.decode('utf-8')), sep=";", low_memory=False))
    df = df.replace(np.nan, "", regex=True)
    return df

@app.callback(Output('myDataFrame', 'children'),
              [Input('DATA', 'contents'),
              Input('DATA', 'filename')])
def load_csv_file(contents, filename):
    if contents is not None:
        children = [
            parse_contents(c, n) for c, n in
            zip(contents, filename)]
        df = children[0]
        return df.to_json(orient="split")
    else:
        return []
    
@app.callback(Output('uploadedText', 'children'),
             [Input('myDataFrame', 'children'),
              Input('DATA', 'filename')])
def update_output(contents, filename):
    if contents != []:
        return "contenu chargé : " + filename[-1]
    else:
        return "aucun contenu chargé"
    
@app.callback(Output('ID1', 'options'),
             [Input('myDataFrame', 'children')])
def update_ID1(contents):
    if contents != []:
        df = pd.read_json(contents, orient="split")
        choice = [{'label':'Sélectionner tout', 'value':'all'}]
        return choice + [{'label':c, 'value':c} for c in sorted(df[FILTER1].unique())]
    else:
        return []

@app.callback(Output('ID2', 'options'),
              [Input('ID1', 'value'),
               Input('myDataFrame', 'children')])
def update_ID2(selected_ID1, contents):
    if (selected_ID1 != []) and (contents != []):
        df = pd.read_json(contents, orient="split")
        if "all" in selected_ID1:
            df = df.loc[:, FILTER2].unique()
        else:
            df = df.loc[df[FILTER1].isin(selected_ID1), FILTER2].unique()
        return [{"label":"Sélectionner tout", "value":"all"}] + [{'label': i, 'value': i} for i in sorted(df)]
    else:
        return []

@app.callback(Output('myBoxplot', 'figure'),
              [Input('ID1', 'value'),
               Input('ID2', 'value'),
               Input('tukey', 'value'),
               Input('myDataFrame', 'children')])
def update_graph(selected_ID1, selected_ID2, tukey, contents):
    if (selected_ID1 != []) and (selected_ID2 != []) and (contents != []):
        df = pd.read_json(contents, orient="split")
        parametres = sorted(list(df.columns[df.columns.isin(PARAMETRES)]), key=lambda x:x.lower())
        if "all" in selected_ID1:
            if "all" in selected_ID2: # ok
                df = df.loc[:, parametres]
            else: # ok
                df = df.loc[(df[FILTER2].isin(selected_ID2)), parametres]
        else:
            df = df.loc[(df[FILTER1].isin(selected_ID1)), :]
            if "all" in selected_ID2: # ok
                df = df.loc[:, parametres]
            else: # ok
                df = df.loc[(df[FILTER2].isin(selected_ID2)), parametres]
        data, labs, param, filter = load_data_points(df, tukey)

        fig = go.Figure()
        for i in range(len(data)):
            fig.add_trace(go.Box(y=data[i], name=labs[i], x0=param[i]))
        fig.update_layout(
            title={"text":"Paramètres analysés%s - %s/%s paramètres affichés"
                   %(" (avec filtre)" if (tukey == "oui") else " (sans filtre)", len(data), len(df.columns)),
                   "x":0.5,
           "font":{"size": 25}},
            legend_title="Légende")

        return fig
    else:
        return {}


if __name__ == '__main__':
    app.run_server()
