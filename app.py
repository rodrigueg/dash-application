########## Imports ##########

import os, copy, datetime, math, io, json, base64, warnings, time

import numpy as np
import pandas as pd
#import geopandas as gpd

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

from threading import Timer
import webbrowser

warnings.filterwarnings("ignore")

external_stylesheets =['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP]

hyperlink_github = '<a href="https://github.com/rodrigueg/dash-application">Github</a>'

########## Global variables ##########
#from flag import flag

#nc_ = flag("NC")
#fr_ = flag("FR")

project_name = 'Analyse de données relatives à la qualité des eaux '
project_name += 'naturelles superficielles et souterraines en Nouvelle-Calédonie'
#C:/Users/Administrateur/Desktop/Rodrigue Govan/DAVAR/dash-application/

cwd = os.getcwd()
cwd = cwd.replace("\\", "/")
cwd += "/"

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
    'backgroundColor': '#70A1D7',
    'vertical-align':'baseline',
    'fontWeight': 'bold',
    'color': 'white',
    'padding': '10px',
    'width':'100%'
}

#RH_layer = gpd.GeoDataFrame.from_file("xn--Rgions_hydrographiques-shp-blc/1add3d37-6b03-443b-9409-5b0e12837bae2020330-1-5yz4ny.akm7k.shp")
#RH_layer = RH_layer.to_crs("epsg:4326")

########## Layout ##########
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Dashboard ISEA"
server = app.server

app.layout = html.Div(
###################### UPLOAD & INFORMATIONS ######################
    [########## Header ##########
        html.Div([], id="data_loaded", style={'display': 'none'}),
        #dcc.Store(id='data_loaded'),
        html.Div(
            [
            html.H3(project_name,
                    style={"font-variant": "small-caps"},
                    className='col-sm-12'
                ),
            ],
            id="header",
            className='row',
        ),
        html.P(""),
        html.Div(
            [########## Upload & Informations ##########
                html.Div(
                    [
                        dcc.Upload(id='upload_file',
                                   children=html.Div(['Insérez le fichier .csv']),
                                   style={'height': '100%',
                                          'lineHeight': '60px',
                                          'borderWidth': '1px',
                                          'borderStyle': 'dashed',
                                          'borderRadius': '1px',
                                          'textAlign': 'center',
                                          'margin': '10px',
                                          "background-color":"#F9F9F9",
                                          'font-style':'bold'
                                          },
                                   multiple=True),
                    ],
                    className="col-sm-6",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
                html.Div(
                    [
                        html.P("aucun contenu chargé",
                            id="content_loaded",
                            style={#'height': '100%',
                                   'lineHeight': '60px',
                                   'borderWidth': '1px',
                                   'borderStyle': 'solid',
                                   'borderRadius': '1px',
                                   'textAlign': 'center',
                                   'margin': '10px',
                                   'font-style':'bold'
                                   })
                    ],
                    id="div_content",
                    className="col-sm-6",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
                ], className="row"),
        html.Div([
                html.Div(
                    [
                        html.H6(0,
                            id="ech_text"
                            ),
                        html.P("échantillons prélevés")
                    ],
                    id="ech",
                    className="col-sm-3",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
                html.Div(
                    [
                        html.H6(0,
                            id="param_text"
                        ),
                        html.P("paramètres")
                    ],
                    id="param",
                    className="col-sm-3",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
                html.Div(
                    [
                        html.H6(0,
                            id="dp_text"
                        ),
                        html.P("données présentes")
                    ],
                    id="dp",
                    className="col-sm-3",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
                html.Div(
                    [
                        html.H6(0,
                            id="dm_text"
                        ),
                        html.P("données absentes")
                    ],
                    id="dm",
                    className="col-sm-3",
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9"}
                ),
            ],
            className="row"
        ),

###################### VISUALISATION PAR SITE ######################
        html.P(""), html.P(""),
        html.Div(
            [
            html.H4("Visualisation par site",
                    style={"font-variant": "small-caps"},
                    className='col-sm-12'
                ),
            ],
            className='row',
        ),
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
                                     placeholder="Filtre par %s" %FILTER1,
                                     style={"border-radius":"1px",})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-4',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="dd2",
                                     options=[],
                                     value=[],
                                     clearable=True,
                                     searchable=True,
                                     multi=True,
                                     placeholder="Filtre par %s" %FILTER2,
                                     style={"border-radius":"1px",})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-5',
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
                                   "display":"inline-block",
                                   "padding-top":"10px",
                                   "padding-bottom":"10px"}
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
                                     style={'background-color':'black',
                                            'border-radius': '2.5px',
                                            'opacity':'1'})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-left":"10px"},
                    className='col-sm-3',
                ),
            ],
            className='row'
        ),
        html.Div(
            [########## Boxplots ##########
                html.Div(
                    [
                        dcc.Loading(children=[dcc.Graph(id='myBoxplot', style={'height':'calc(80vh)', 'width':'100%'})], type="default", color="#70A1D7")
                    ], className="col-sm-12"
                ),
            ],
            style={"border-radius":"1px",
            "background-color":"#F9F9F9",
            "padding-top":"10px",
            "padding-bottom":"10px"},
            className='row'
        ),
        html.Div(
            [########## Map ##########
                html.Div(
                    [
                        dcc.Loading(children=[dcc.Graph(id='map', style={'height': '400px'})], type="default", color="#70A1D7")
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-7',
                ),
                html.Div(id='map_div', #style={'vertical-align':'middle'},
                    #[
                    #    dt.DataTable(id='map_table')
                    #],
                    style={
                    "border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-5',
                ),
            ],
            className='row'
        ),

###################### VISUALISATION PAR ELEMENT ######################
        html.P(""), html.P(""),

        html.Div([

        html.H4("Visualisation par élément", style={"font-variant": "small-caps"},
        className="col-sm-12")

        ],

        className="row"),

        html.Div([

            html.Div(
                [
                    dcc.Dropdown(id="elem1",
                                 options=[{'label': 'Éléments dissous', 'value':'dissous'},
                                          {'label': 'Éléments totaux', 'value':'tota'}],
                                 value=None,
                                 clearable=True,
                                 searchable=True,
                                 multi=False,
                                 placeholder="Filtre par élément",
                                 style={"border-radius":"1px",})
                ],
                style={"border-radius":"1px",
                "background-color":"#F9F9F9",
                "padding-top":"10px",
                "padding-bottom":"10px"},
                className='col-sm-5',
            ),
            html.Div(
                [
                    dcc.Dropdown(id="elem2",
                                 options=[],
                                 value=None,
                                 clearable=True,
                                 searchable=True,
                                 multi=False,
                                 placeholder="Choisissez un élément",
                                 style={"border-radius":"1px",})
                ],
                style={"border-radius":"1px",
                "background-color":"#F9F9F9",
                "padding-top":"10px",
                "padding-bottom":"10px"},
                className='col-sm-7',
            ),

        ],
        className="row"),

        html.Div(
            [########## Boxplots ##########
                html.Div(
                    [
                        dcc.Loading(children=[dcc.Graph(id='elemBoxplot', style={'height':'calc(80vh)', 'width':'100%'})], type="default", color="#70A1D7")
                    ], className="col-sm-12"
                ),
        ],
        style={"border-radius":"1px",
        "background-color":"#F9F9F9",
        "padding-top":"10px",
        "padding-bottom":"10px"},
        className='row'),

###################### ANALYSE DES SCENARIOS ######################
        html.P(""), html.P(""),
        html.Div([
            html.H4("Analyse des scénarios", style={"font-variant": "small-caps"}),
            ], className="col-sm-12"),
            html.Div([
            html.Div([
                html.Div(
                    [
                        dcc.Dropdown(id="type_eau",
                                     options=[{'label':'Eau souterraine', 'value':'Eau souterraine'},
                                              {'label':'Eau superficielle', 'value':'Eau superficielle'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'eau",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-6',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="periode",
                                     options=[{'label':'Crue', 'value':'crue'},
                                              {'label':'Décrue', 'value':'decrue'},
                                              {'label':'Étiage', 'value':'etiage'},
                                              {'label':'Moyennes eaux', 'value':'moyenne eau'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez la période",
                                     style={'display':'none'})
                    ],
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="elements",
                                     options=[{'label': 'Éléments dissous', 'value':'dissous'},
                                              {'label': 'Éléments totaux', 'value':'tota'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'éléments (dissous ou totaux)",
                                     style={"border-radius":"1px"}
                                     )
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-6',
                )
            ], className="row", id='scenario_dropdown'),
            html.Div([], id='disp_tabs')]),
            dcc.Store(id='data_scenario'),
            html.Div([], id="disp_clustering"),
            html.Div([], id="clustering_parElement"),


        html.Footer(html.Div(["© %s, Rodrigue GOVAN - ISEA. Tous droits réservés. "
                % (datetime.datetime.now().year), html.A("Github", href="https://github.com/rodrigueg/dash-application", target="_blank"), "."]),
                style={'font-style':'italic', "padding-top":"25px"})
    ],
    id="mainContainer"
)

########## Callbacks ##########
@app.callback(Output("disp_clustering", "children"),
              Input("data_scenario", "data"))
def update_clustering_table(data_acp):
    if data_acp == []:
        return []

    tmp = pd.read_json(data_acp, orient="split")
    param = list(tmp.loc[:, tmp.columns.isin(PARAMETRES)].columns)
    df_clusters2 = make_kmeans(tmp, param, 2)
    df_clusters3 = make_kmeans(tmp, param, 3)

    # création des onglets pour les matrices de p-value
    myTabs = []
    for i, dfclust in zip((2,3), (df_clusters2,df_clusters3)):
        myTabs.append(dcc.Tab(label="K-means (k = %s)" %i, style=tab_style, selected_style=tab_selected_style,
                              children=[dt.DataTable(columns=[{"name": i, "id": i} for i in dfclust.columns],
                                                               data=dfclust.to_dict('records'),
                                                     style_cell={'overflow': 'hidden',
                                                                 'textOverflow': 'ellipsis',
                                                                 'minWidth': '80px'},
                                                               fixed_rows={'headers': True},
                                                     style_data_conditional=[{'if': {'row_index': 'odd'},
                                                                              'backgroundColor': 'rgb(248, 248, 248)'}],
                                                     )]))

    return [html.Div([html.H6("Résultats du clustering (méthode des K-means)",
                              style={"border-radius":"1px",
                              "background-color":"#F9F9F9",
                              "padding-top":"10px",
                              "padding-bottom":"10px",
                              "margin-top":"-10px",
                              "margin-bottom":"-10px"},
                              className="col-sm-12")],
                    className="row"),
            html.Div([
            html.Div([
                      dcc.Tabs(myTabs)],
                      style={#"border-radius":"1px",
                             "background-color":"#F9F9F9",
                             "width":"100%",
                             "padding-top":"10px",
                             "padding-bottom":"10px"},
                      className="col-sm-12")], className="row")
            ]



@app.callback([Output("disp_tabs", "children"),
               Output("data_scenario", "data"),
               Output("clustering_parElement", "children")],
              [Input("type_eau", "value"),
               Input("periode", "value"),
               Input("elements", "value"),
               Input("data_loaded", "children")])
def update_tabs(type_eau, periode, elements, data_loaded):
    if data_loaded == []:
        return [], [], []
    if type_eau == None:
        return [], [], []
    elif type_eau == "Eau souterraine":
        if elements == None:
            return [], [], []
    elif type_eau == "Eau superficielle":
        if periode == None:
            return [], [], []
        elif elements == None:
            return [], [], []

    #df = pd.read_json(data_loaded, orient="split")
    tmp = df
    if type_eau == "Eau souterraine":
        tmp = tmp.loc[(tmp["Type"] == type_eau)]
    else:
        tmp = tmp.loc[(tmp["Type"] == type_eau) & (tmp["Periode"] == periode)]

    caracteristiques = list(tmp.loc[:, ~tmp.columns.isin(PARAMETRES)].columns)

    # récupération des éléments (selon le scénario choisi)
    param_to_add = []#"pH", "pH in situ",
                    #"Turbidité", "Turbidité in situ",
                    #"Conductivité", "Conductivité in situ",
                    #"Température", "Température in situ"]
    if elements == "dissous":
        sel_elements = list(tmp.loc[:, tmp.columns.str.contains(" dissous")].columns)
    else:
        sel_elements = list(df.loc[:, tmp.columns.str.contains(" tota")].columns)
        dissous = list(df.loc[:, tmp.columns.str.contains(" dissous")].columns)
        total = [d.replace(" dissous", "") for d in dissous if d.replace(" dissous", "") in tmp.columns]
        sel_elements += total

    sel_elements = param_to_add + sel_elements
    sel_elements = sorted(sel_elements, key=lambda x:x.lower())

    tmp[sel_elements] = tmp[sel_elements].apply(pd.to_numeric)

    infos_data = pd.DataFrame(data={"Parametre":sel_elements, "Variabilité":0, "Données présentes":""})
    # verification des éléments avec une variabilité nulle (drop it like it's hot)
    elements_to_keep = []
    for el in sel_elements:
        infos_data.loc[infos_data["Parametre"] == el, "Données présentes"] = "%.2f%%" % (round(100*len(tmp.loc[(~tmp[el].isna()), el])/len(tmp[el]), 2))
        if len(tmp[el].unique()) > 2:
            elements_to_keep.append(el)
            infos_data.loc[infos_data["Parametre"] == el, "Variabilité"] = round(np.var(tmp[el]),2)
    sel_elements = elements_to_keep

    df_corr = tmp.loc[:, list(infos_data.loc[infos_data["Variabilité"] > 0, "Parametre"])]
    df_corr = df_corr.apply(pd.to_numeric)
    df_corr = df_corr.corr()

    # colorscale: rouge (-1), noir (0), vert (1)
    fig_corr = go.Figure(data=go.Heatmap(z = np.array(df_corr),
                                         x = df_corr.columns,
                                         y = df_corr.columns,
                                         zmin=-1, zmax=1,
                                         colorscale=["rgb(244,124,124)", "rgb(195,99,99)", "rgb(0,0,0)", "rgb(129,178,118)", "rgb(161,222,147)"],
                                         xgap=1, ygap=1,
                                         hovertemplate='X: %{x}<br>Y: %{y}<br>Corr(X,Y) = %{z}<extra></extra>',
                                         colorbar={"thickness":15,
                                                   "tickvals":[-1, -0.5,  0, 0.5, 1]}))
    fig_corr['layout']['yaxis']['autorange'] = "reversed"
    fig_corr.update_layout(title="Matrice des corrélations",
                           paper_bgcolor='rgba(0,0,0,0)',
                           xaxis = dict(tickangle = 45))
    #fig_corr['layout']['yaxis']['scaleanchor']='x'
    fig_corr.update_layout(plot_bgcolor='rgba(0,0,0,0)')

    infos_data = dt.DataTable(columns=[{"name": i, "id": i} for i in infos_data.columns],
                              data=infos_data.to_dict('records'),
                              style_cell={'overflow': 'hidden',
                                          'textOverflow': 'ellipsis',
                                          'minWidth': '125px'},
                              fixed_rows={'headers': True},
                              style_data_conditional=[{'if': {'row_index': 'odd'},
                                                       'backgroundColor': 'rgb(248, 248, 248)'}],
                              )#export_format="csv")

    # verif s'il y a au moins 50% de résultats
    to_delete = []
    for d in sel_elements:
        if round(100*len(tmp.loc[(~tmp[d].isna()), d])/len(tmp[d]), 2) < 50:
            to_delete.append(d)
    for d in to_delete:
        sel_elements.remove(d)

    df_clustering1D = {se:[] for se in sel_elements}
    k_el = None
    for k in df_clustering1D.keys():
        # IDPrelevement, Riviere, Element
        df_clustering1D_tmp = tmp.loc[(~tmp[k].isna()), ["IDPrelevement", "Riviere", k]]
        df_clustering1D[k] = [make_kmeans_1D(df_clustering1D_tmp, k, 2), make_kmeans_1D(df_clustering1D_tmp, k, 3)]

    clustering1D_tabs = []
    for k in df_clustering1D.keys():
        clustering1D_tabs.append(dcc.Tab(label=k, style=tab_style, selected_style=tab_selected_style,
                                         children=[dcc.Tabs(children=[
                                                    dcc.Tab(label="K-means (k = %s)" % kclust, style=tab_style, selected_style=tab_selected_style,
                                                    children = [dt.DataTable(columns=[{"name": i, "id": i} for i in df_clustering1D[k][k_i].columns],
                                                                data=df_clustering1D[k][k_i].to_dict('records'),
                                                                export_format = "xlsx",
                                                                style_cell={'overflow': 'hidden',
                                                                            'textOverflow': 'ellipsis',
                                                                            'minWidth': '80px'},
                                                                fixed_rows={'headers': True},
                                                                style_data_conditional=[{'if': {'row_index': 'odd'},
                                                                                         'backgroundColor': 'rgb(248, 248, 248)'}]
                                                                )]) for k_i, kclust in enumerate((2,3))])]))

    # acp possible lorsque len(sel_elements) >= 3 !!

    res_pv = {}
    for d in sel_elements:
        df2 = tmp.groupby(['Riviere'])[d].count().reset_index()
        df2 = df2.drop(df2[(df2[d] < 10)].index)
        res_pv[d] = wmw(d, tmp, df2)

    # création des onglets pour les matrices de p-value
    myTabs = []
    for k in res_pv.keys():
        if res_pv[k].shape[0] == 0: # pas assez de données
            continue
        myTabs.append(dcc.Tab(label=k, style=tab_style, selected_style=tab_selected_style,
                              children=[dt.DataTable(columns=[{"name": i, "id": i} for i in res_pv[k].columns],
                                                     tooltip_header={i: i for i in res_pv[k].columns[1:]},
                                                     style_header_conditional=[{'if': {'column_id': col},
                                                                               'textDecoration': 'underline',
                                                                               'textDecorationStyle': 'dotted'} for col in res_pv[k].columns[1:]],
                                                     export_format = "xlsx",
                                                     data=res_pv[k].to_dict('records'),
                                                     style_cell={'overflow': 'hidden',
                                                                 'textOverflow': 'ellipsis',
                                                                 'minWidth': '80px'},
                                                    fixed_rows={'headers': True},
                                                    style_data_conditional=[{'if': {'filter_query': '{{{col}}} <= 0.05'.format(col=col), 'column_id': col},
                                                                            'backgroundColor': '#F8B0B0'} for col in res_pv[k].columns[1:]],
                                                    tooltip_conditional=[{'if': {'filter_query': '{{{col}}} <= 0.05'.format(col=col), 'column_id': col},
                                                                         'type': 'markdown',
                                                                         'value': "L'hypothèse d'égalité des médianes est rejetée."} for col in res_pv[k].columns[1:]],
                                                    tooltip_delay=0,
                                                    tooltip_duration=None
                                                     )]))

    if len(sel_elements) >= 3:
        df_acp = tmp.loc[:, caracteristiques + sel_elements]
        df_acp["Riviere"].replace({"": " "}, inplace=True)

        # imputation des données
        ncomp = estim_ncpPCA(df_acp.loc[:, sel_elements], verbose=False)
        data_imputed = imputePCA(df_acp.loc[:, sel_elements], ncp=ncomp[0])[0]
        df_acp.loc[:, sel_elements] = data_imputed
        # acp (make_pca func from utils.py)
        coord, corvar, expl_var, n, p = make_pca(df_acp, sel_elements)

        # graphique du nuage des individus
        fig_indiv = px.scatter(x=coord[:,0], y=coord[:,1], #z=coord[:,2],
                               color=df_acp["Riviere"], labels={"color": "Site"})
        fig_indiv.update_layout(title="Nuage des individus",
                                xaxis_title="Dim 1 (%s%%)" % round(expl_var[0],2),
                                yaxis_title="Dim 2 (%s%%)" % round(expl_var[1],2),
                                #scene=go.Scene(xaxis=go.XAxis(title="Dim 1 (%s%%)" % round(expl_var[0],2)),
                                #yaxis=go.YAxis(title="Dim 2 (%s%%)" % round(expl_var[1],2)),
                                #zaxis=go.ZAxis(title="Dim 3 (%s%%)" % round(expl_var[2],2))),
                                legend_title="Site (%s)" % len(df_acp["Riviere"].unique()),
                                legend_traceorder='normal',
                                paper_bgcolor='rgba(0,0,0,0)',)
        fig_indiv.update_layout(shapes=[
            # adds line at y=0
            dict(type= 'line',
                 xref= 'paper', x0=0, x1=1,
                 yref= 'y', y0= 0, y1= 0,
                 line=dict(color="grey", width=1)
                 ),
            dict(type= 'line',
                 xref= 'x', x0=0, x1=0,
                 yref= 'paper', y0= 0, y1= 1,
                 line=dict(color="grey", width=1)
                 )
            ])
        #fig_indiv.update_scenes(xaxis_autorange="reversed",
        #                        yaxis_autorange="reversed")

        # graphique du cercle des corrélations des variables
        layout = go.Layout(xaxis=dict(title="Dim 1 (%s%%)" % round(expl_var[0],2)),
                           yaxis=dict(title="Dim 2 (%s%%)" % round(expl_var[1],2)),
                           paper_bgcolor='rgba(0,0,0,0)')
        fig_corvar = go.Figure(layout=layout)
        fig_corvar.add_shape(type="circle",
                      xref="x", yref="y",
                      x0=-1, y0=-1, x1=1, y1=1,
                      line=dict(color="grey", width=1.5))
        fig_corvar.add_shape(type="line",
                      xref="x", yref="y",
                      x0=-1, y0=0, x1=1, y1=0,
                      line=dict(color="grey", width=1.5))
        fig_corvar.add_shape(type="line",
                      xref="x", yref="y",
                      x0=0, y0=-1, x1=0, y1=1,
                      line=dict(color="grey", width=1.5))
        annot = []
        for cv in range(p):
            text = go.layout.Annotation(dict(x=(corvar[cv,0]+(sign(corvar[cv,0])*0.025)),
                                             y=(corvar[cv,1]+(sign(corvar[cv,1])*0.025)),
                                             text=sel_elements[cv],
                                             showarrow=True,
                                             ax=0, ay=0, arrowcolor='black',
                                             arrowhead=3, arrowwidth=1.5))
            arrow = go.layout.Annotation(dict(x=corvar[cv,0], y=corvar[cv,1],
                                             text="",
                                             axref="x", ayref="y",
                                             showarrow=True,
                                             ax=0, ay=0, arrowcolor='black',
                                             arrowhead=3, arrowwidth=1.5))
            annot.append(text)
            annot.append(arrow)
        fig_corvar.update_layout(annotations=annot)
        fig_corvar.update_xaxes(range=[-1.05, 1.05], zeroline=True)
        fig_corvar.update_yaxes(range=[-1.05, 1.05], zeroline=True)
        fig_corvar.update_layout(title={"text":"Corrélations des variables"})

    if len(myTabs) == 0:
        if len(sel_elements) >= 3:
            #print("aquii1") #done
            return [html.Div([html.H6("Informations sur les paramètres pour ce scénario : %s échantillons" % tmp.shape[0],
                                      style={#"border-radius":"1px",
                                             "background-color":"#F9F9F9",
                                             "padding-top":"10px",
                                             "padding-bottom":"10px"},
                                      className="col-sm-12")],
                             style={"margin-top":"-10px",
                                    "margin-bottom":"-10px"},
                             className="row"),
                    html.Div([html.Div([infos_data], className="col-sm-6"),
                              dcc.Graph(figure=fig_corr, className="col-sm-6"),
                             ],
                             style={"border-radius":"1px",
                                    "background-color":"#F9F9F9",
                                    "padding-top":"10px",
                                    "padding-bottom":"10px"},
                            className="row"),
                    html.Div([html.H6("Test de comparaison des médianes (test de Wilcoxon-Mann-Whitney)", className="col-sm-12")],
                              style={#"border-radius":"1px",
                                     "background-color":"#F9F9F9",
                                     "padding-top":"10px",
                                     "padding-bottom":"10px"},
                              className='row'),
                             html.P("Il n'y a pas assez de résultats par site pour ce scénario."
                                     + " Le test de comparaison des médianes n'est donc pas réalisable.",
                                     style={#"border-radius":"1px",
                                            "background-color":"#F9F9F9",
                                            "padding-top":"10px",
                                            "padding-bottom":"10px",
                                            "padding-left":"20px"},
                                    className="row"),
                    html.Div([
                    html.H6("Résultats de l'ACP", className="col-sm-12")],
                    style={"border-radius":"1px",
                           "background-color":"#F9F9F9",
                           "padding-top":"10px",
                           "padding-bottom":"10px",
                           "margin-top":"-10px"},
                    className="row"),
                    html.Div([
                    html.P("Pour effectuer l'ACP ci-dessous, une simulation de données absentes a dû être réalisée au préalable, par la méthode de l'ACP itérative.",
                            style={"border-radius":"1px",
                                   "background-color":"#F9F9F9",
                                   "margin-top":"-10px",
                                   "margin-bottom":"-10px"}, className="col-sm-12")], className="row"),
                    html.Div([dcc.Graph(figure=fig_indiv, style={"height":"37.5vw"}, className="col-sm-7"),
                              dcc.Graph(figure=fig_corvar, style={"width":"100vw", "height":"37.5vw"}, className="col-sm-5")],
                              style={"border-radius":"1px",
                                     "background-color":"#F9F9F9",
                                     "padding-top":"10px",
                                     "padding-bottom":"10px"},
                              className="row")
                             ], \
                    df_acp.to_json(orient="split"), \
                    html.Div([html.H6("Résultats du clustering par élement", style={#"border-radius":"1px",
                           "background-color":"#F9F9F9",
                           "padding-top":"10px",
                           "padding-bottom":"10px",
                           "margin-top":"-10px",
                           "margin-bottom":"-10px"},
                    className="col-sm-12"),
                    html.Div([
                              dcc.Tabs(clustering1D_tabs)],
                              style={#"border-radius":"1px",
                                     "background-color":"#F9F9F9",
                                     "width":"100%",
                                     "padding-top":"10px",
                                     "padding-bottom":"10px"},
                              className="col-sm-12")], className="row")
        #print("aquii2")#done
        return [html.Div([html.H6("Informations sur les paramètres pour ce scénario : %s échantillons" % tmp.shape[0],
                                  style={#"border-radius":"1px",
                                         "background-color":"#F9F9F9",
                                         "padding-top":"10px",
                                         "padding-bottom":"10px"},
                                  className="col-sm-12")],
                         style={"margin-top":"-10px",
                                "margin-bottom":"-10px"},
                         className="row"),
                html.Div([html.Div([infos_data], className="col-sm-6"),
                          dcc.Graph(figure=fig_corr, className="col-sm-6"),
                         ],
                         style={"border-radius":"1px",
                                "background-color":"#F9F9F9",
                                "padding-top":"10px",
                                "padding-bottom":"10px"},
                        className="row"),
                html.Div([html.H6("Test de comparaison des médianes (test de Wilcoxon-Mann-Whitney)", className="col-sm-12")],
                          style={#"border-radius":"1px",
                                 "background-color":"#F9F9F9",
                                 "padding-top":"10px",
                                 "padding-bottom":"10px"},
                          className='row'),
                         html.P("Il n'y a pas assez de résultats par site pour ce scénario."
                                 + " Le test de comparaison des médianes n'est donc pas réalisable.",
                                 style={#"border-radius":"1px",
                                        "background-color":"#F9F9F9",
                                        "padding-top":"10px",
                                        "padding-bottom":"10px",
                                        "padding-left":"10px"},
                                className="row"),
                html.Div([html.H6("Il n'y a pas assez de paramètres retenus pour pouvoir effectuer une ACP (et un clustering) sur les paramètres retenus.",
                        style={#"border-radius":"1px",
                               "background-color":"#F9F9F9",
                               "padding-top":"10px",
                               "padding-bottom":"10px"
                               },
                        className="col-sm-12")],
                        style={#"border-radius":"1px",
                               "background-color":"#F9F9F9",
                               "margin-top":"-10px",
                               "margin-bottom":"-10px"
                               },
                        className="row")], \
                [], []

    if len(sel_elements) >= 3:
        #print("aquii3") #done
        return [html.Div([html.H6("Informations sur les paramètres pour ce scénario : %s échantillons" % tmp.shape[0],
                                  style={#"border-radius":"1px",
                                         "background-color":"#F9F9F9",
                                         "padding-top":"10px",
                                         "padding-bottom":"10px"},
                                  className="col-sm-12")],
                         style={"margin-top":"-10px",
                                "margin-bottom":"-10px"},
                         className="row"),
                html.Div([html.Div([infos_data], className="col-sm-6"),
                          dcc.Graph(figure=fig_corr, className="col-sm-6"),
                         ],
                         style={"border-radius":"1px",
                                "background-color":"#F9F9F9",
                                "padding-top":"10px",
                                "padding-bottom":"10px"},
                        className="row"),
                html.Div([
                          html.Div([html.H6("Test de comparaison des médianes (test de Wilcoxon-Mann-Whitney)", style={"display":"inline"}),
                          html.Span("i", id="tooltip-wmw",
                                    style={"textAlign": "center", "margin-left":"15px",
                                           "color": "black", 'height': '25px', 'width': '25px',
                                           'background-color': '#ddd', 'border-radius': '50%',
                                           'display': 'inline-block'}),
                          dbc.Tooltip(html.P(help_wmw,
                                             style={'padding':'15px'}),
                                             target="tooltip-wmw",
                                             placement="right",
                                             style={'background-color':'black',
                                                    'border-radius': '2.5px',
                                                    'opacity':'1'})], className='col-sm-12'),],
                        style={"border-radius":"1px",
                               "background-color":"#F9F9F9",
                               "padding-top":"10px",
                               "padding-bottom":"10px"},
                        className="row"),
                html.P("Nous avons choisi de ne retenir que les sites qui ont au minimum 10 résultats afin d'effectuer le test de comparaison.",
                        style={"border-radius":"1px",
                               "background-color":"#F9F9F9",
                               "padding-top":"10px",
                               "padding-bottom":"10px",
                               "padding-left":"10px"},
                        className="row"),
                html.Div([
                html.Div([
                          dcc.Tabs(myTabs)],
                          style={#"border-radius":"1px",
                                 "background-color":"#F9F9F9",
                                 "width":"100%",
                                 "padding-top":"10px",
                                 "padding-bottom":"10px",
                                 "margin-top":"-10px",
                                 "margin-bottom":"-10px"},
                          className="col-sm-12")], className="row"),
            html.Div([
            html.H6("Résultats de l'ACP", className="col-sm-12")],
            style={"border-radius":"1px",
                   "background-color":"#F9F9F9",
                   "padding-top":"10px",
                   "padding-bottom":"10px",
                   "margin-top":"-10px"},
            className="row"),
            html.Div([
            html.P("Pour effectuer l'ACP ci-dessous, une simulation de données absentes a dû être réalisée au préalable, par la méthode de l'ACP itérative.",
                    style={"border-radius":"1px",
                           "background-color":"#F9F9F9",
                           "margin-top":"-10px",
                           "margin-bottom":"-10px"}, className="col-sm-12")], className="row"),
            html.Div([dcc.Graph(figure=fig_indiv, style={"height":"37.5vw"}, className="col-sm-7"),
                      dcc.Graph(figure=fig_corvar, style={"width":"100vw", "height":"37.5vw"}, className="col-sm-5")],
                      style={"border-radius":"1px",
                             "background-color":"#F9F9F9",
                             "padding-top":"10px",
                             "padding-bottom":"10px"},
                      className="row")], \
            df_acp.to_json(orient="split"), \
            html.Div([html.H6("Résultats du clustering par élement", style={#"border-radius":"1px",
                   "background-color":"#F9F9F9",
                   "padding-top":"10px",
                   "padding-bottom":"10px",
                   "margin-top":"-10px",
                   "margin-bottom":"-10px"},
            className="col-sm-12"),
            html.Div([
                      dcc.Tabs(clustering1D_tabs)],
                      style={#"border-radius":"1px",
                             "background-color":"#F9F9F9",
                             "width":"100%",
                             "padding-top":"10px",
                             "padding-bottom":"10px"},
                      className="col-sm-12")], className="row")

    #print("aquii4") #done
    return [html.Div([html.H6("Informations sur les paramètres pour ce scénario : %s échantillons" % tmp.shape[0],
                              style={#"border-radius":"1px",
                                     "background-color":"#F9F9F9",
                                     "padding-top":"10px",
                                     "padding-bottom":"10px"},
                              className="col-sm-12")],
                     style={"margin-top":"-10px",
                            "margin-bottom":"-10px"},
                     className="row"),
            html.Div([html.Div([infos_data], className="col-sm-6"),
                      dcc.Graph(figure=fig_corr, className="col-sm-6"),
                     ],
                     style={"border-radius":"1px",
                            "background-color":"#F9F9F9",
                            "padding-top":"10px",
                            "padding-bottom":"10px"},
                    className="row"),
            html.Div([
                      html.Div([html.H6("Test de comparaison des médianes (test de Wilcoxon-Mann-Whitney)", style={"display":"inline"}),
                      html.Span("i", id="tooltip-wmw",
                                style={"textAlign": "center", "margin-left":"15px",
                                       "color": "black", 'height': '25px', 'width': '25px',
                                       'background-color': '#ddd', 'border-radius': '50%',
                                       'display': 'inline-block'}),
                      dbc.Tooltip(html.P(help_wmw,
                                         style={'padding':'15px'}),
                                         target="tooltip-wmw",
                                         placement="right",
                                         style={'background-color':'black',
                                                'border-radius': '2.5px',
                                                'opacity':'1'})], className='col-sm-12'),],
                    style={"border-radius":"1px",
                           "background-color":"#F9F9F9",
                           "padding-top":"10px",
                           "padding-bottom":"10px"},
                    className="row"),
            html.P("Nous avons choisi de ne retenir que les sites qui ont au minimum 10 résultats afin d'effectuer le test de comparaison.",
                    style={"border-radius":"1px",
                           "background-color":"#F9F9F9",
                           "padding-top":"10px",
                           "padding-bottom":"10px",
                           "padding-left":"10px"},
                    className="row"),
            html.Div([
            html.Div([
                      dcc.Tabs(myTabs)],
                      style={#"border-radius":"1px",
                             "background-color":"#F9F9F9",
                             "width":"100%",
                             "padding-top":"10px",
                             "padding-bottom":"10px",
                             "margin-top":"-10px",
                             "margin-bottom":"-10px"},
                      className="col-sm-12")], className="row"),

            html.Div([html.P("Il n'y a pas assez de paramètres retenus pour pouvoir effectuer une ACP (et un clustering) sur les paramètres retenus.", style={#"border-radius":"1px",
                   "background-color":"#F9F9F9",
                   "padding-top":"10px",
                   "padding-bottom":"10px",
                   },
            className="col-sm-12")], className="row"),
            ], \
            [], \
            html.Div([html.H6("Résultats du clustering par élement", style={#"border-radius":"1px",
                   "background-color":"#F9F9F9",
                   "padding-top":"10px",
                   "padding-bottom":"10px",
                   "margin-top":"-10px",
                   "margin-bottom":"-10px"},
            className="col-sm-12"),
            html.Div([
                      dcc.Tabs(clustering1D_tabs)],
                      style={#"border-radius":"1px",
                             "background-color":"#F9F9F9",
                             "width":"100%",
                             "padding-top":"10px",
                             "padding-bottom":"10px"},
                      className="col-sm-12")], className="row")

@app.callback(Output("scenario_dropdown", "children"),
             Input("type_eau", "value"))
def update_scena_dropdown(type_eau):
    children = [html.Div(
                    [
                        dcc.Dropdown(id="type_eau",
                                     options=[{'label':'Eau souterraine', 'value':'Eau souterraine'},
                                              {'label':'Eau superficielle', 'value':'Eau superficielle'}],
                                     value=type_eau, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'eau",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-6',
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="periode",
                                     options=[{'label':'Crue', 'value':'crue'},
                                              #{'label':'Décrue', 'value':'decrue'},
                                              {'label':'Étiage', 'value':'etiage'}],
                                              #{'label':'Moyennes eaux', 'value':'moyenne eau'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez la période",
                                     style={'display':'none'})
                    ],
                ),
                html.Div(
                    [
                        dcc.Dropdown(id="elements",
                                     options=[],#{'label': 'Éléments dissous', 'value':'dissous'},
                                              #{'label': 'Éléments totaux', 'value':'tota'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'éléments (dissous ou totaux)",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className="col-sm-6"
                )]
    if type_eau == "Eau souterraine":
        children[0] = html.Div(
                    [
                        dcc.Dropdown(id="type_eau",
                                     options=[{'label':'Eau souterraine', 'value':'Eau souterraine'},
                                              {'label':'Eau superficielle', 'value':'Eau superficielle'}],
                                     value=type_eau, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'eau",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-6',
                )
        children[-1] = html.Div(
                    [
                        dcc.Dropdown(id="elements",
                                     options=[{'label': 'Éléments dissous', 'value':'dissous'},
                                              {'label': 'Éléments totaux', 'value':'tota'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'éléments (dissous ou totaux)",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-6',
                )
    elif type_eau == "Eau superficielle":
        children[0] = html.Div(
                        [
                            dcc.Dropdown(id="type_eau",
                                         options=[{'label':'Eau souterraine', 'value':'Eau souterraine'},
                                                  {'label':'Eau superficielle', 'value':'Eau superficielle'}],
                                         value=type_eau, clearable=True, searchable=True, multi=False,
                                         placeholder="Choisissez le type d'eau",
                                         style={"border-radius":"1px"})
                        ],
                        style={"border-radius":"1px",
                        "background-color":"#F9F9F9",
                        "padding-top":"10px",
                        "padding-bottom":"10px"},
                        className='col-sm-4',
                    )
        children[-1] = html.Div(
                    [
                        dcc.Dropdown(id="periode",
                                     options=[{'label':'Crue', 'value':'crue'},
                                              #{'label':'Décrue', 'value':'decrue'},
                                              {'label':'Étiage', 'value':'etiage'}],
                                              #{'label':'Moyennes eaux', 'value':'moyenne eau'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez la période",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-4',
                )
        children.append(html.Div(
                    [
                        dcc.Dropdown(id="elements",
                                     options=[{'label': 'Éléments dissous', 'value':'dissous'},
                                              {'label': 'Éléments totaux', 'value':'tota'}],
                                     value=None, clearable=True, searchable=True, multi=False,
                                     placeholder="Choisissez le type d'éléments (dissous ou totaux)",
                                     style={"border-radius":"1px"})
                    ],
                    style={"border-radius":"1px",
                    "background-color":"#F9F9F9",
                    "padding-top":"10px",
                    "padding-bottom":"10px"},
                    className='col-sm-4',
                ))
    return children

@app.callback([Output('data_loaded', 'children'),
               Output('content_loaded', 'children')],
              [Input('upload_file', 'contents'),
              Input('upload_file', 'filename')])
def load_csv_file(contents, filename): ########## Parse the data ##########
    global df
    df = None
    if (contents != None) and (len(filename) == 1):
        if filename[0].split('.')[-1] != "csv":
            return [], "veuillez charger un contenu au format csv"
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

        return ["data loaded"], filename[0]
    else:
        return [], "aucun contenu chargé"

@app.callback([Output('ech_text', 'children'),
               Output('param_text', 'children'),
               Output('dp_text', 'children'),
               Output('dm_text', 'children'),
               Output('dd1', 'options')],
              [Input('data_loaded', 'children')])
def update_well_text(df_loaded): ########## Informations ##########

    if df_loaded != []:
        dp, dm = get_dp_dm(df.loc[:,df.columns.isin(PARAMETRES)])

        choice = [{'label':'Sélectionner tout', 'value':'all'}]
        choice += [{'label':c, 'value':c} for c in sorted(df[FILTER1].unique())]
        return ('{:,}'.format(df.shape[0]).replace(',', ' '),
                '{:,}'.format(len(df.loc[:,df.columns.isin(PARAMETRES)].columns)).replace(',', ' '),
                '{:,}'.format(dp).replace(',', ' '),
                '{:,}'.format(dm).replace(',', ' '), choice)
    return ("0","0","0","0", [])

@app.callback(Output('dd2', 'options'),
              [Input('data_loaded', 'children'),
               Input('dd1', 'value')])
def update_dd2(data, selected_rh):
    if (selected_rh != []) and (data != []):
        tmp = df.copy()
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
        fig.update_layout(title={"text":"Paramètres analysés%s<br>%s/%s %s"
               %(" (avec filtre)" if (tukey == ["oui"]) else " (sans filtre)",
                 len(data), len(tmp.columns), parametres_affiches),
                                 "x":0.5,
                                 "font":{"size": 15}},
                          legend_title="Sites",
                          paper_bgcolor='rgba(0,0,0,0)')
        fig.update_layout(margin={"r":5,"l":2.5})

        return fig
    else:
        return {}

@app.callback(Output('map', 'figure'),
              Input('data_loaded', 'children'))
def make_main_figure(data): ########## Generate the map ##########
    global df
    if data == []: return {}

    df["Latitude"] = pd.to_numeric(df["Latitude"])
    df["Longitude"] = pd.to_numeric(df["Longitude"])

    fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name=FILTER1,
                            hover_data=["IDPrelevement"],
                            color_discrete_sequence=["#70A1D7"], opacity=0.75, zoom=7)
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig

@app.callback(Output('map_div', 'children'),
              [Input('data_loaded', 'children'),
               Input('map', 'clickData'),
               Input('map', 'figure')])
def update_map_table(data, cData, fig):
    if cData != None: ########## Generate the list from the map ##########
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
        tmp.loc[tmp["Variable"] == "Longitude", "Attribut"] = round(float(tmp.loc[tmp["Variable"] == "Longitude", "Attribut"]), 2)
        tmp.loc[tmp["Variable"] == "Latitude", "Attribut"] = round(float(tmp.loc[tmp["Variable"] == "Latitude", "Attribut"]), 2)
        to_return = dt.DataTable(id='map_table',
                                 columns=[{"name": i, "id": i} for i in tmp.columns],
                                 data=tmp.to_dict('records'),
                                 style_table={'overflowX': 'auto', 'height': '400px'},
                                 fixed_rows={'headers': True},
                                 style_data={'whiteSpace': 'normal',
                                             'height': 'auto',
                                             'lineHeight': '15px'},
                                 style_data_conditional=[{'if': {'row_index': 'odd'},
                                                          'backgroundColor': 'rgb(248, 248, 248)'}]
                                )
        return to_return
    elif (fig != {}) and (data != []):
        return html.H6("Sélectionnez un échantillon pour visualiser ses paramètres analysés")

@app.callback(Output('elem2', 'options'),
              [Input('data_loaded', 'children'),
               Input('elem1', 'value')])
def update_element_dropdown(data, elem1):
    if (elem1 != None) and (data != []):
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
                                 "font":{"size": 15}},
                          legend_title="Sites",
                          paper_bgcolor='rgba(0,0,0,0)')
        fig.update_layout(margin={"r":5,"l":2.5})
        return fig
    else:
        return {}

def open_browser():
	webbrowser.open_new("127.0.0.1:8050")

########## Launching ##########
if __name__ == '__main__':
    #Timer(1, open_browser).start()
    app.run_server(debug=True)
