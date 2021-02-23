########## Imports ##########

import os, copy, datetime, math, io, json, base64, warnings, time

import numpy as np
import pandas as pd
import geopandas as gpd

from flask import Flask
import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
import dash_table as dt
import dash_daq as daq
import dash_leaflet as dl

import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff

from sklearn import preprocessing
import multiprocessing as mp

from utils import *

########## Global variables ##########
project_name = 'Analyse de données relatives à la qualité des eaux '
project_name += 'naturelles superficielles et souterraines en Nouvelle-Calédonie'

parametres_unite = pd.DataFrame(pd.read_csv("data/parametres_unite.csv", sep=";",
                                            encoding="utf-8", keep_default_na=False))
if "Azote total dissous" in list(parametres_unite["Parametre"]):
    parametres_unite.loc[parametres_unite["Parametre"] == "Azote total dissous", "Parametre"] = "Azote dissous"
PARAMETRES = list(parametres_unite["Parametre"])

VOYELLE = ("a", "e", "i", "o", "u", "y")

FILTER1 = "RegionHydro"
FILTER2 = "Riviere"

sign = lambda x: (1, -1)[x < 0]

help_tukey = ["Le filtre de Tukey permet de considérer un résultat comme",
              html.Br(),
              "étant une valeur extrême (ou non). Si un résultat est supérieur",
              html.Br(),
              "à Q3 + 1.5xIQR ou inférieur à Q1 - 1.5xIQR, on considérera",
              html.Br(),
              "ce résultat comme étant une valeur extrême (IQR = Q3 - Q1)."]

help_wmw = ["Le test de Wilcoxon-Mann-Whitney est un test statistique (non paramétrique)",
            html.Br(),
            "permettant de tester l'hypothèse selon laquelle la médiane de deux",
            html.Br(),
            "groupes de données sont proches. On pose alors comme hypothèse",
            html.Br(),
            "H0 : Med(Site_A) = Med(Site_B); et H1 : Med(Site_A) ≠ Med(Site_B).",
            html.Br(),
            "Ci-dessous est affichée la matrice des p-value obtenue en effectuant",
            html.Br(),
            "le test de Wilcoxon pour chaque site par rapport aux autres sites.",
            html.Br(),
            "Si la p-value ≤ 0.05, on rejette H0. Sinon on ne rejette pas H0."]

tab_style = {
    'borderBottom': '1px solid #d6d6d6',
    'padding': '6px',
    'vertical-align':'baseline'
}

tab_selected_style = {
    'borderTop': '1px solid #d6d6d6',
    'borderBottom': '1px solid #d6d6d6',
    'backgroundColor': '#119DFF',
    'vertical-align':'baseline',
    'fontWeight': 'bold',
    'color': 'white',
    'padding': '10px',
    'width':'100%'
}

#RH_layer = gpd.GeoDataFrame.from_file("xn--Rgions_hydrographiques-shp-blc/1add3d37-6b03-443b-9409-5b0e12837bae2020330-1-5yz4ny.akm7k.shp")
#RH_layer = RH_layer.to_crs("epsg:4326")

########## Layout ##########
app = dash.Dash(__name__)
app.title = "Dashboard ISEA"
server = app.server

app.layout = html.Div(
###################### UPLOAD & INFORMATIONS ######################
    [########## Header ##########
        html.Div([], id="data_loaded", style={'display': 'none'}),
        #dcc.Store(id='data_loaded'),
        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            project_name,
                            style={"font-variant": "small-caps"}
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
                                        html.P("données absentes")
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
###################### VISUALISATION PAR SITE ######################
        html.Div([
        html.H3("Visualisation par site", style={"font-variant": "small-caps"}),
        html.Div(
            [########## Filters ##########
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
                    className='pretty_container six columns',
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
                    className='pretty_container eight columns',
                ),
                html.Div(
                    [
                        dcc.Checklist(
                            id='apply_tukey',
                            options=[
                                {'label': '  Appliquer le filtre de Tukey', 'value': 'oui'}
                            ],
                            value=['oui'],
                            style={"margin-top":"5px",
                                   "display":"inline-block"}
                        ),
                        html.Span("i",
                                  id="tooltip-tukey",
                                  style={"textAlign": "center",
                                         "margin-left":"15px",
                                         "color": "black",
                                         'height': '25px',
                                         'width': '25px',
                                         'background-color': '#ddd',
                                         'border-radius': '50%',
                                         'display': 'inline-block'}),
                         dbc.Tooltip(html.P(help_tukey,
                                            style={'padding':'15px'}),
                                     target="tooltip-tukey",
                                     placement="left",
                                     style={'background-color':'#ddd',
                                            'border-radius': '2.5px',
                                            'opacity':'0.95'})
                    ],
                    className='pretty_container three columns',
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
                    className='pretty_container seven columns',
                ),
                html.Div(id='map_div', style={'vertical-align':'middle'},
                    #[
                    #    dt.DataTable(id='map_table')
                    #],
                    className='pretty_container five columns',
                ),
            ],
            className='row'
        ),
        ], className='pretty_container'),
###################### VISUALISATION PAR ELEMENT ######################
        html.Div([
        html.H3("Visualisation par élément", style={"font-variant": "small-caps"}),
        html.Div(
            [########## Filters ##########
                html.Div(
                    [
                        dcc.Dropdown(id="elem1",
                                     options=[{'label': 'Éléments dissous', 'value':'dissous'},
                                              {'label': 'Éléments totaux', 'value':'tota'}],
                                     value=None,
                                     clearable=True,
                                     searchable=True,
                                     multi=False,
                                     placeholder="Filtre par élément")
                    ],
                    className='pretty_container five columns',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="elem2",
                                     options=[],
                                     value=None,
                                     clearable=True,
                                     searchable=True,
                                     multi=False,
                                     placeholder="Choisissez un élément")
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
                        dcc.Graph(id='elemBoxplot', style={'height':'calc(80vh)',
                                                           'width':'100%'})
                    ],
                ),
            ],
            className='pretty_container'
        ),
        ], className='pretty_container'),

        html.Footer(html.Div(["© %s, ISEA. Tous droits réservés. "
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
@app.callback(Output('data_loaded', 'children'),
              [Input('upload_file', 'contents'),
              Input('upload_file', 'filename')])
def load_csv_file(contents, filename): ########## Parse the data ##########
    global df
    df = None
    if (contents != None) and (len(filename) == 1):
        if filename[0].split('.')[-1] != "csv":
            return []
        children = [parse_contents(c, n) for c, n in zip(contents, filename)]
        df = children[0]
        # fusion de Chrome dissous et Chrome VI dissous
        if ("Chrome dissous" in df.columns) and ("Chrome VI dissous" in df.columns):
            df.loc[(df["Chrome dissous"] == "") & (df["Chrome VI dissous"] != ""), "Chrome dissous"] = df.loc[(df["Chrome dissous"] == "") & (df["Chrome VI dissous"] != ""), "Chrome VI dissous"]
            df = df.drop(["Chrome VI dissous"], axis=1)
        # fusion de Silice et Silice total
        if ("Silice" in df.columns) and ("Silice total" in df.columns):
            df.loc[(df["Silice"] != "") & (df["Silice total"] == ""), "Silice total"] = df.loc[(df["Silice"] != "") & (df["Silice total"] == ""), "Silice"]
            df = df.drop(["Silice"], axis=1)
        # fusion de Nickel et Nickel total
        if ("Nickel" in df.columns) and ("Nickel total" in df.columns):
            df.loc[(df["Nickel"] != "") & (df["Nickel total"] == ""), "Nickel total"] = df.loc[(df["Nickel"] != "") & (df["Nickel total"] == ""), "Nickel"]
            df = df.drop(["Nickel"], axis=1)
        # fusion de Nitrates et Nitrates totaux
        if ("Nitrates" in df.columns) and ("Nitrates totaux" in df.columns):
            df.loc[(df["Nitrates"] != "") & (df["Nitrates totaux"] == ""), "Nitrates totaux"] = df.loc[(df["Nitrates"] != "") & (df["Nitrates totaux"] == ""), "Nitrates"]
            df = df.drop(["Nitrates"], axis=1)
        # suppression des échantillons avec des pH (et pH in situ) > 14
        if "pH" in df.columns:
            df = df.drop(df.loc[df["pH"].apply(pd.to_numeric) > 14].index, axis=0)
        if "pH in situ" in df.columns:
            df = df.drop(df.loc[df["pH in situ"].apply(pd.to_numeric) > 14].index, axis=0)
        # renommer Azote total dissous en Azote dissous (Azote total déjà existant)
        if "Azote total dissous" in df.columns:
            df = df.rename(columns={"Azote total dissous":"Azote dissous"})

        to_return = ["data loaded"]
        return to_return
    else:
        return []

@app.callback([Output('ech_text', 'children'),
               Output('param_text', 'children'),
               Output('dp_text', 'children'),
               Output('dm_text', 'children'),
               Output('dd1', 'options')],
              [Input('data_loaded', 'children')])
def update_well_text(df_loaded): ########## Informations ##########

    if df_loaded != []:
        #df = pd.read_json(dfjson, orient="split")
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
              [Input('data_loaded', 'children'),
               Input('dd1', 'value')])
def update_dd2(data, selected_rh):
    if (selected_rh != []) and (data != []):
        #df = pd.read_json(data, orient="split")
        if "all" in selected_rh:
            tmp = df.loc[:, FILTER2].unique()
        else:
            tmp = tmp.loc[tmp[FILTER1].isin(selected_rh), FILTER2].unique()
        return [{"label":"Sélectionner tout", "value":"all"}] + [{'label': i, 'value': i} for i in sorted(tmp)]
    else:
        return []

@app.callback(Output('myBoxplot', 'figure'),
              [Input('dd1', 'value'),
               Input('dd2', 'value'),
               Input('data_loaded', 'children'),
              Input('apply_tukey', 'value')])
def update_graph(selected_dd1, selected_dd2, data, tukey): ########## Generate the boxplots ##########
    if (selected_dd1 != []) and (selected_dd2 != []) and (data != []):
        #df = pd.read_json(data, orient="split")
        parametres = sorted(list(df.columns[df.columns.isin(PARAMETRES)]), key=lambda x:x.lower())
        tmp = df
        if "all" not in selected_dd1:
              tmp = tmp.loc[(tmp[FILTER1].isin(selected_dd1)), :]
        if "all" not in selected_dd2:
              tmp = tmp.loc[(tmp[FILTER2].isin(selected_dd2)), :]
        tmp = tmp.loc[:, parametres]

        data, labs, param, filter = load_data_points_parametres(tmp, tukey, parametres_unite)

        fig = go.Figure()
        for i in range(len(data)):
            fig.add_trace(go.Box(y=data[i], name=labs[i], x0=param[i]))
        parametres_affiches = "paramètres affichés" if len(param) > 1 else "paramètre affiché"
        fig.update_layout(
            title={"text":"Paramètres analysés%s - %s/%s %s"
                   %(" (avec filtre)" if (tukey == ["oui"]) else " (sans filtre)",
                     len(data), len(tmp.columns), parametres_affiches),
                   "x":0.5,
           "font":{"size": 25}},
            legend_title="Légende",
            paper_bgcolor='rgba(0,0,0,0)')
        fig.update_layout(margin={"r":10,"l":2.5})

        return fig
    else:
        return {}

@app.callback(Output('map', 'figure'),
              Input('data_loaded', 'children'))
def make_main_figure(data): ########## Generate the map ##########
    global df
    if data == []: return {}

    #df = pd.read_json(data, orient="split")
    df["Latitude"] = pd.to_numeric(df["Latitude"])
    df["Longitude"] = pd.to_numeric(df["Longitude"])

    fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name=FILTER1,
                            hover_data=["IDPrelevement"],
                            color_discrete_sequence=["cornflowerblue"], opacity=0.75, zoom=7)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig

@app.callback(Output('map_div', 'children'),
              [Input('data_loaded', 'children'),
               Input('map', 'clickData'),
               Input('map', 'figure')])
def update_map_table(data, cData, fig):
    if cData is not None: ########## Generate the list from the map ##########
        #df = pd.read_json(data, orient="split")
        tmp = df.loc[df["IDPrelevement"] == cData['points'][0]['customdata'][0]].replace("", np.nan, regex=True)
        tmp = tmp.dropna(axis=1,how='all')

        carac = list(tmp.loc[:, ~tmp.columns.isin(PARAMETRES)].columns)
        param = sorted(list(tmp.loc[:, tmp.columns.isin(PARAMETRES)].columns), key=lambda x:x.lower())

        variable = carac + param
        tmp = tmp.T.rename(columns=lambda x:"Attribut")
        tmp["Variable"] = variable
        tmp["Unite"] = "-"
        for p in tmp.loc[tmp["Variable"].isin(PARAMETRES), "Variable"]:
            tmp.loc[tmp["Variable"] == p, "Unite"] = parametres_unite.loc[parametres_unite["Parametre"] == p, "Unite"].unique()[0]
        tmp = tmp.reindex(columns=["Variable", "Attribut", "Unite"])
        to_return = dt.DataTable(id='map_table',
                                 columns=[{"name": i, "id": i} for i in tmp.columns],
                                 data=tmp.to_dict('records'),
                                 fixed_rows={'headers': True},
                                 style_table={'height': '400px'},
                                 style_data_conditional=[{'if': {'row_index': 'odd'},
                                                          'backgroundColor': 'rgb(248, 248, 248)'}])
        return to_return
    elif (fig != {}) and (data != []):
        return html.H6("Sélectionnez un échantillon pour visualiser ses paramètres analysés")

@app.callback(Output('elem2', 'options'),
              [Input('data_loaded', 'children'),
               Input('elem1', 'value')])
def update_element_dropdown(data, elem1):
    if (elem1 != None) and (data != []):
        #df = pd.read_json(data, orient="split")
        elements = list(df.loc[:, df.columns.str.contains(elem1)].columns)
        if elem1 == "tota":
            dissous = list(df.loc[:, df.columns.str.contains(" dissous")].columns)
            total = [d.replace(" dissous", "") for d in dissous if d.replace(" dissous", "") in df.columns]
            elements += total
        return [{'label': '%s (%s)' %(i, str(parametres_unite.loc[parametres_unite["Parametre"] == i, "Unite"].unique()[0])), 'value': i} for i in sorted(elements)]
    else:
        return []

@app.callback(Output("elemBoxplot", "figure"),
              [Input("data_loaded", "children"),
               Input("elem2", "value")])
def update_elem_boxplot(data_loaded, elem2):
    if (data_loaded != []) and (elem2 != None):
        #df = pd.read_json(data_loaded, orient="split")
        tmp = df.loc[:, ["Riviere", elem2]]

        data, labs, sites = load_data_points_sites(tmp, elem2)
        fig = go.Figure()

        element = elem2.split(" (")[0].lower()
        nb_sites = "sites" if len(sites) > 1 else "site"
        title = "Résultats %s%s par site (%s %s)" % ("d'" if element[0] in VOYELLE else "de ",
                                                            element, len(sites), nb_sites)

        for i in range(len(data)):
            fig.add_trace(go.Box(y=data[i], name=labs[i], x0=sites[i]))
        fig.update_layout(title={"text":title,
                                 "x":0.5,
                                 "font":{"size": 25}},
                          legend_title="Sites",
                          paper_bgcolor='rgba(0,0,0,0)')
        fig.update_layout(margin={"r":10,"l":2.5})
        return fig
    else:
        return {}

########## Launching ##########
if __name__ == '__main__':
    app.run_server(debug=True)
