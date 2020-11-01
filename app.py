########## Imports ##########

import os, copy, datetime, math, io, json, base64, warnings, time

import numpy as np
import pandas as pd

from flask import Flask
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
import dash_daq as daq
import dash_leaflet as dl

import plotly.graph_objects as go
import plotly.express as px

from sklearn import preprocessing
import multiprocessing as mp

from utils import *

########## Global variables ##########

PARAMETRES = pd.DataFrame(pd.read_csv("data/parametres.csv", sep=";", encoding="utf-8"))
PARAMETRES = list(PARAMETRES["Parametre"])

FILTER1 = "RegionHydro"
FILTER2 = "Riviere"

########## Layout ##########
app = dash.Dash(__name__)
app.title = "Rodrigue GOVAN x ISEA"
server = app.server

app.layout = html.Div(
    [########## Header ##########
        dcc.Store(id='data_loaded'),
        html.Div(
            [
                html.Div(
                    [
                        html.H2(
                            'Analyse de données relatives à la qualité des eaux naturelles superficielles et souterraines en Nouvelle-Calédonie',
                        ),
                    ],

                    className='nine columns'
                ),
                html.Div([], className='two columns'),
                html.A(
                    html.Button(
                        "GitHub",
                        id="learnMore",
                    ),
                    href="https://github.com/rodrigueg/dash-application", target="_blank",
                    #className="two column",
                ),
            ],
            id="header",
            className='row',
        ),
        html.Div(
            [########## Upload & Informations ##########
                html.Div(
                    [
                        dcc.Upload(id='upload_file',
                                   children=html.Div(['Insérez la matrice statistique (fichier .csv)']),
                                   style={'height': '100%',
                                          'lineHeight': '60px',
                                          'borderWidth': '1px',
                                          'borderStyle': 'dashed',
                                          'borderRadius': '5px',
                                          'textAlign': 'center',
                                          'margin': '10px',
                                          'font-style':'bold'
                                          },
                                   multiple=True),
                    ],
                    className="pretty_container five columns"
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H6(0,
                                            id="ech_text",
                                            className="info_text"),
                                        html.P("échantillons prélevés")
                                    ],
                                    id="ech",
                                    className="pretty_container five columns"
                                ),
                                html.Div(
                                    [
                                        html.H6(0,
                                            id="param_text",
                                            className="info_text"
                                        ),
                                        html.P("paramètres")
                                    ],
                                    id="param",
                                    className="pretty_container five columns"
                                ),
                                html.Div(
                                    [
                                        html.H6(0,
                                            id="dp_text",
                                            className="info_text"
                                        ),
                                        html.P("données présentes")
                                    ],
                                    id="dp",
                                    className="pretty_container five columns"
                                ),
                                html.Div(
                                    [
                                        html.H6(0,
                                            id="dm_text",
                                            className="info_text"
                                        ),
                                        html.P("données manquantes")
                                    ],
                                    id="dm",
                                    className="pretty_container five columns"
                                ),
                            ],
                            id="infoContainer",
                            className="row"
                        ),
                    ],
                    id="rightCol",
                    className="eight columns"
                )
            ],
            className="row"
        ),
        html.Div(
            [########## Filters ##########
                html.Div(
                    [
                        dcc.Checklist(
                            id='apply_tukey',
                            options=[
                                {'label': '  Appliquer le filtre de Tukey', 'value': 'oui'}
                            ],
                            value=['oui'],
                            style={"margin-top":"5px"}
                        ),
                    ],
                    className='pretty_container two columns',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="dd1",
                                     options=[],
                                     value=[],
                                     clearable=True,
                                     searchable=True,
                                     multi=True,
                                     placeholder="Filtre par %s" %FILTER1,)
                    ],
                    className='pretty_container five columns',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="dd2",
                                     options=[],
                                     value=[],
                                     clearable=True,
                                     searchable=True,
                                     multi=True,
                                     placeholder="Filtre par %s" %FILTER2,)
                    ],
                    className='pretty_container seven columns',
                ),
            ],
            className='row'
        ),
        html.Div(
            [########## Boxplots ##########
                html.Div(
                    [
                        dcc.Graph(id='myBoxplot', style={'height':'calc(80vh)'})
                    ], 
                ),
            ],
            className='pretty_container'
        ),
        html.Div(
            [########## Map ##########
                html.Div(
                    [
                        dcc.Graph(id='map', style={'height': '400px'})
                    ],
                    className='pretty_container eight columns',
                ),
                html.Div(id='map_div', style={'vertical-align':'middle'},
                    #[
                    #    dt.DataTable(id='map_table')
                    #],
                    className='pretty_container four columns',
                ),
            ],
            className='row'
        ),
        html.Footer(html.Div(["© %s, Rodrigue GOVAN — ISEA. Tous droits réservés. "
                % (datetime.datetime.now().year)]),
                style={'font-style':'italic'})
    ],
    id="mainContainer",
    style={
        "display": "flex",
        "flex-direction": "column",
        "margin-top":"-60px",
        "margin-bottom":"-60px",
        "margin-left":"-45px",
        "margin-right":"-45px"
        }
)

########## Callbacks ##########

@app.callback(Output('data_loaded', 'data'),
              [Input('upload_file', 'contents'),
              Input('upload_file', 'filename')])
def load_csv_file(contents, filename): ########## Parse the data ##########
    if (contents != None) and (len(filename) == 1):
        children = [
            parse_contents(c, n) for c, n in
            zip(contents, filename)]
        df = children[0]
        to_return = df.to_json(orient="split")
        return to_return
    else:
        return []

@app.callback([Output('ech_text', 'children'),
               Output('param_text', 'children'),
               Output('dp_text', 'children'),
               Output('dm_text', 'children'),
               Output('dd1', 'options')],
              [Input('data_loaded', 'data')])
def update_well_text(dfjson): ########## Informations ##########

    if dfjson != []:
        df = pd.read_json(dfjson, orient="split")
        dp, dm = get_dp_dm(df.loc[:,df.columns.isin(PARAMETRES)])

        choice = [{'label':'Sélectionner tout', 'value':'all'}]
        choice += [{'label':c, 'value':c} for c in sorted(df[FILTER1].unique())]
        return ('{:,}'.format(df.shape[0]).replace(',', ' '),
                '{:,}'.format(len(df.loc[:,df.columns.isin(PARAMETRES)].columns)).replace(',', ' '),
                '{:,}'.format(dp).replace(',', ' '),
                '{:,}'.format(dm).replace(',', ' '),
                choice)
    return ("0","0","0","0", [])

@app.callback(Output('dd2', 'options'),
              [Input('data_loaded', 'data'),
               Input('dd1', 'value')])
def update_dd2(data, selected_rh):
    if (selected_rh != []) and (data != []):
        df = pd.read_json(data, orient="split")
        if "all" in selected_rh:
            df = df.loc[:, FILTER2].unique()
        else:
            df = df.loc[df[FILTER1].isin(selected_rh), FILTER2].unique()
        return [{"label":"Sélectionner tout", "value":"all"}] + [{'label': i, 'value': i} for i in sorted(df)]
    else:
        return []

@app.callback(Output('myBoxplot', 'figure'),
              [Input('dd1', 'value'),
               Input('dd2', 'value'),
               Input('data_loaded', 'data'),
              Input('apply_tukey', 'value')])
def update_graph(selected_dd1, selected_dd2, data, tukey): ########## Generate the boxplots ##########
    if (selected_dd1 != []) and (selected_dd2 != []) and (data != []):
        df = pd.read_json(data, orient="split")
        parametres = sorted(list(df.columns[df.columns.isin(PARAMETRES)]), key=lambda x:x.lower())
        if "all" not in selected_dd1:
              df = df.loc[(df[FILTER1].isin(selected_dd1)), :]
        if "all" not in selected_dd2:
              df = df.loc[(df[FILTER2].isin(selected_dd2)), :]
        df = df.loc[:, parametres]
        
        data, labs, param, filter = load_data_points(df, tukey)

        fig = go.Figure()
        for i in range(len(data)):
            fig.add_trace(go.Box(y=data[i], name=labs[i], x0=param[i]))
        fig.update_layout(
            title={"text":"Paramètres analysés%s - %s/%s paramètres affichés"
                   %(" (avec filtre)" if (tukey == ["oui"]) else " (sans filtre)", len(data), len(df.columns)),
                   "x":0.5,
           "font":{"size": 25}},
            legend_title="Légende")

        return fig
    else:
        return {}

@app.callback(Output('map', 'figure'),
              Input('data_loaded', 'data'))
def make_main_figure(data): ########## Generate the map ##########

    if data == []: return {}
    
    df = pd.read_json(data, orient="split")
    df["Latitude"] = pd.to_numeric(df["Latitude"])
    df["Longitude"] = pd.to_numeric(df["Longitude"])
    
    fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name=FILTER1,
                            hover_data=["IDPrelevement"],
                            color_discrete_sequence=["cornflowerblue"], opacity=0.75, zoom=7)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    
    return fig

@app.callback(Output('map_div', 'children'),
              [Input('data_loaded', 'data'),
               Input('map', 'clickData'),
               Input('map', 'figure')])
def update_map_table(data, cData, fig):
    if cData is not None: ########## Generate the list from the map ##########
        df = pd.read_json(data, orient="split")
        df = df.loc[df["IDPrelevement"] == cData['points'][0]['customdata'][0]].replace("", np.nan, regex=True)
        df = df.dropna(axis=1,how='all')
##        print(dt.DataTable(columns=[{"name": i, "id": i} for i in df.columns],
##                           data=df.to_dict('records')).data, end="\n\n")
        variable = df.columns
        df = df.T.rename(columns=lambda x:"Attribut")
        df["Variable"] = variable
        df = df.reindex(columns=["Variable", "Attribut"])
        to_return = dt.DataTable(id='map_table',
                            columns=[{"name": i, "id": i} for i in df.columns],
                            data=df.to_dict('records'),
                            fixed_rows={'headers': True},
                            style_table={'height': '400px'})
        return to_return
    elif (fig != {}) and (data != []):
        return html.H6("Sélectionnez un échantillon pour visualiser ses paramètres analysés")


########## Launching ##########
if __name__ == '__main__':
    app.run_server(debug=True)
