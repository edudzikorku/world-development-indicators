
# imports

# data management
import re
import numpy as np
import pandas as pd
from unicodedata import lookup
from urllib.parse import unquote


# data visualization
from plotly import express as px
import plotly.graph_objects as go
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash import Dash, html, dcc, Output, Input, callback

# cell management
import warnings
warnings.filterwarnings("ignore")

data = pd.read_csv('data/PovStatsData.csv')

country = pd.read_csv('data/PovStatsCountry.csv', na_values = '', keep_default_na = False)

series = pd.read_csv("data/PovStatsSeries.csv")

poverty_indicator = pd.read_csv('data/poverty.csv', low_memory = False)

# create list of regions in dataframe
regions = ['East Asia & Pacific', 'Europe & Central Asia',
           'Fragile and conflict affected situations', 'High income',
           'IDA countries classified as fragile situations', 'IDA total',
           'Latin America & Caribbean', 'Low & middle income', 'Low income',
           'Lower middle income', 'Middle East & North Africa', 'Middle income',
           'South Asia', 'Sub-Saharan Africa', 'Upper middle income', 'World']

# create subset of original dataframe
# remove the region names and maintain the country names
data_sub = data[~data["Country Name"].isin(regions) & (data["Indicator Name"] == "Population, total")].reset_index()

# slice columns, starting from 1994
year_list = data_sub.columns[5:51].values.tolist()

# convert column names (strings) to integers
year_list = [int(year) for year in year_list]

# get information on Gini coefficient
gini = "GINI index (World Bank estimate)"

# separate regions from non-regions
country['is_country'] = country['Region'].notna()

# create country flag emojis
# get list of country codes
country_code_list = country[country['is_country']]['2-alpha code'].dropna().str.lower().tolist()

# create function for country flags
def country_flag(alpha_code):
    # handle the situation where the provided letters are either NaN or not part of the country code list
    if pd.isna(alpha_code) or (alpha_code.lower() not in country_code_list):
        return ''
    # create emoji if alpha code is part of country code list
    code_a = lookup(f'REGIONAL INDICATOR SYMBOL LETTER {alpha_code[0]}')
    code_b = lookup(f'REGIONAL INDICATOR SYMBOL LETTER {alpha_code[1]}')
    # concatenate alpha codes
    return code_a + code_b

    # # alternative approach
    # code_a = f"{alpha_code[0]}"
    # code_b = f"{alpha_code[1]}"
    # return flag(code_a + code_b)

# add country flags to dataframe
country['flag'] = [country_flag(code) for code in country['2-alpha code']]

# drop irrelevant column
data = data.drop(columns = ['Unnamed: 50'], axis = 1)
# melt data dataframe. melting involves coverting columns into rows
# convert all years into one column
# set id variables. keep these as rows and duplicate them as needed to keep the mapping in place
id_vars = [col for col in data.columns[:4]]
data_melt = data.melt(
    id_vars = id_vars,
    var_name = "Year"
).dropna(subset = ['value'])

# convert year column to integer
data_melt['Year'] = data_melt['Year'].astype(int)

# pivot data dataframe. pivoting involves converting rows into columns
data_melt_pivot = data_melt.pivot(
    index = ['Country Name', 'Country Code', 'Year'],
    columns = 'Indicator Name',
    values = 'value'
).reset_index()


# merge dataframes
# pivot data and country data
poverty = pd.merge(
    left = data_melt_pivot,
    right = country,
    left_on = "Country Code",
    right_on = "Country Code",
    how = 'left'
)

# select income shares within countries, for all years, with a focus on 20%
income_share_df = poverty.filter(regex = "Country Name|^Year$|Income share.*?20" ).dropna()

# rearrange columns
income_share_df_sorted = income_share_df.rename(columns = {
    'Income share held by lowest 20%': '1 Income share held by lowest 20%',
    'Income share held by second 20%': '2 Income share held by second 20%',
    'Income share held by third 20%': '3 Income share held by third 20%',
    'Income share held by fourth 20%': '4 Income share held by fourth 20%',
    'Income share held by highest 20%': '5 Income share held by highest 20%',
}).sort_index(axis = 1)

# remove redundant parts of the column names
income_share_df_sorted.columns = [re.sub('\d Income share held by ', '', col).title() for col in income_share_df_sorted.columns]

# setup tabss
tab1 = dbc.Tab([
            html.Ul([
                html.Br(),
                html.Li("Number of Economies: 70"),
                html.Li("Temporal Coverage: 1974 - 2019"),
                html.Li("Update Frequency: Quarterly"),
                html.Li("Last Updated: August 03, 2023"),
                html.Li([
                    "Source:", html.A(
                        'The World Bank',  href ='https://datacatalog.worldbank.org/dataset/poverty-and-equity-database'
                    )
                ])
            ], style = {
                'fontFamily': 'sans-serif',

            }),
        ], label = "Key Facts")

tab2 = dbc.Tab([
            html.Ul([
                html.Br(),
                html.Li(' Goal: Build a data-driven Dash app that transforms raw World Bank data into meaningful insights, enabling users to identify trends and patterns crucial for sustainable development strategies.'),
                html.Li([
                    'Github repo: ',
                    html.A('https://github.com/edudzikorku/global-development-indicators',
                          href = 'https://github.com/edudzikorku/global-development-indicators')
        ])
            ])
        ], label = 'Project Info')

def initial_fig():
    fig = go.Figure()
    fig.layout.paper_bgcolor = '#2C3E50'
    fig.layout.plot_bgcolor = '#2C3E50'
    return fig

# create a function to wrap indicator names
def wrap_indicator_names(indicator_name):
    # create list to contain wraped name
    wraped_name = []
    # split indicator name into words
    name_split = indicator_name.split()
    # group every three words together
    for word in range(0, len(name_split), 3):
        wraped_name.append(' '.join(name_split[word:word + 3]))
    return '<br>'.join(wraped_name)

# get country names
countries = data['Country Name'].unique()
# create dataframe for gini index, eliminating rows with missing values
gini_df = poverty[poverty[gini].notna()]
gini_years = gini_df["Year"].drop_duplicates().sort_values()
gini_countries = gini_df["Country Name"].unique()
# select columns to be ploted
income_share_df_sorted_col = income_share_df_sorted.columns[:-2]
countries_income_share_df_sorted = income_share_df_sorted["Country Name"].unique()
country_list = gini_df["Country Name"].unique().tolist()
# create first column
col1 = dbc.Col([
            dbc.Label("Year", className = "mx-2"),

            html.Br(),
            dcc.Dropdown(id = 'gini_year_dropdown',
                         placeholder = "Select a year",
                         options = [{'label': year,
                                     'value': year} for year in gini_years],
   style = {
'color': '#2C3E50'}),
            dcc.Graph(id = 'gini_year_barcharts', figure = initial_fig())
])

# create second column
col2 = dbc.Col([
            dbc.Label("Country"),

            html.Br(),
            dcc.Dropdown(id = 'gini_country_dropdown',
                         multi = True,
                         placeholder = "Select one or more countries",
                         options = [{'label': country,
                                     'value': country} for country in gini_countries],
   style = {
'color': '#2C3E50'},
                        ),
            dcc.Graph(id = 'gini_country_barcharts', figure = initial_fig())
        ])

col3 = dbc.Col(lg = 1)
col4 = dbc.Col([
        html.H3("Income Share Distribution", style = {
        'fontFamily': 'sans-serif',
        'textAlign': 'center',
            }),
        html.Br(),
        dbc.Label("Country"),
        dcc.Dropdown(id = 'income_level_country',
                         placeholder = "Select a country",
                         options = [{'label': country,
                                   'value': country} for country in countries_income_share_df_sorted],
   style = {
'color': '#2C3E50'}),

        dcc.Graph(id = 'income_level_country_barchart', figure = initial_fig()),
])

# filter poverty indicator dataset
poverty_gap_cols = poverty_indicator.filter(regex = 'Poverty gap').columns
 # create three variables, one for each poverty level
perc_pov_19 = poverty_gap_cols[0]
perc_pov_32 = poverty_gap_cols[1]
perc_pov_55 = poverty_gap_cols[2]

# get colors for marks for the slider
cividis0 = px.colors.sequential.Cividis[0]
indicator_marks = {
    0: {
        'label': '$1.9', 'style': {'color': 'white', 'fontWeight': 'bold'}
    },
    1: {
        'label': '$3.2', 'style': {'color': 'white', 'fontWeight': 'bold'}
    },
    2: {
        'label': '$5.5', 'style': {'color': 'white', 'fontWeight': 'bold'}
    },
}

# create dataframe for percentage poverty
perc_pov_df = poverty_indicator[poverty_indicator['is_country']].dropna(subset = poverty_gap_cols)
perc_pov_years = sorted(set(perc_pov_df['year']))
year_marks = {year: {'label': str(year), 'style': {'color': 'white'}} for year in perc_pov_years[::5]}  # slicing the year list with a step of five

poverty_indicator_slider = dbc.Col([
                   dbc.Label("Select poverty level: ", style = {'fontFamily': 'sans-serif', 'paddingRight': '10px'}),
                   dcc.Slider(id = 'porverty_indicator_slider',
                   min = 0,
                   max = 2,
                   step = 1,
                   value = 0,
                   included = False,
                   marks = indicator_marks
              )], lg = 2)
year_slider =    dbc.Col([dbc.Label("Select a year: ",  style = {'fontFamily': 'sans-serif', 'marginRight': '10px'}),
                  dcc.Slider(id = 'percentage_poverty_year_slider',
                  min = perc_pov_years[0],
                  max = perc_pov_years[-1],
                  step = 1,
                  included = False,
                  value = 2018,
                  marks = year_marks
                        )], lg = 5)

poverty_graph_col = dbc.Col([dcc.Graph(id = 'percentage_poverty__scatter_chart', figure = initial_fig())], lg = 10)

# get indicators
indicator_list = poverty_indicator.columns[3:54]

# get countries
country_sub = poverty_indicator[poverty_indicator['is_country']]

"""#### Main Layout"""

app = Dash(__name__, external_stylesheets = [dbc.themes.DARKLY])
# get list of indicators
indicator_list = poverty_indicator.columns[3:54]
# get list of countries
country_list = poverty_indicator[poverty_indicator['is_country']]["Country Name"].drop_duplicates().sort_values().tolist()

main_layout = html.Div([
    html.Div([
        dbc.NavbarSimple([
                    dbc.DropdownMenu([
                        dbc.DropdownMenuItem(country, href = country) for country in country_list
                    ], label = "Select a country")
                    ], brand = 'Home', brand_href = '/', light = True
                    ),
        dbc.Row([
            dbc.Col(lg = 1, md = 1, sm = 1),
            dbc.Col([
                dcc.Location(id = 'location'),
                html.Div(id = 'main_content'),
            ], lg = 10),
        ])
    ], style = {'fontFamily': 'sans-serif', 'fontSize': '14px',
            'backgroundColor': '#2C3E50'})
])

"""#### Indicators Dashboard"""

indicators_dashboard = html.Div([
    html.Meta(charSet="UTF-8"),
    html.Meta(name='viewport', content='width=device-width,initial-scale=1'),
    dbc.Col([
             html.Br(),
             html.H3("Poverty and Equity Database"),
             html.H4("The World Bank"),
             ], style = {'textAlign': 'center'}),
    html.Br(),
    dbc.Row([
             # dbc.Col(lg = 1, md = 1, sm = 1),
             dbc.Col([
                     dcc.Dropdown(id = 'indicator_dropdown',
                                  value = 'GINI index (World Bank estimate)',
                                  options = [{'label': indicator, 'value': indicator} for indicator in indicator_list],
                                  style = {'fontFamily': 'sans-serif','color': 'black'}),
                     dcc.Loading(
                                 id = 'loading',
                                 type = 'default',
                                 fullscreen = False,
                                 children = [
                                             # create graph component
                                             dcc.Graph(id = 'indicator_map_chart'),
                                             dcc.Markdown(id = 'indicator_details', style = {'backgroundColor': '#e5ecf6',
                                                            'fontFamily': 'sans-serif',
                                                            'color': 'black'})])])
           ]),
    html.Br(),
    dbc.Row([
        dbc.Col(width = {"size": 1, "order": 1}, lg = {"size": 1, "order": 1}),
        dbc.Col([
            dbc.Label("Indicator: ", style = {'fontFamily': 'sans-serif', 'color': 'white', 'whiteSpace': 'normal'}),
            dcc.Dropdown(id = 'indicator_histogram_dropdown',
                        value = gini,
                        options = [{'label': indicator ,
                                       'value': indicator} for indicator in indicator_list],
                        style = {'fontSize': 12, 'fontFamily': 'sans-serif', 'color': 'black'}),

            ], width = {"size": 5, "order": 2}, lg = {"size": 6, "order": 2}),
        dbc.Col([
            dbc.Label("Years: ", style = {'fontFamily': 'sans-serif', 'color': 'white'}),
            html.Br(),
            dcc.Dropdown(id = 'indicator_year_dropdown',
                            placeholder = "Select one or more years",
                            multi = True,
                            value = [2015],
                            options = [{'label': year,
                                       'value': year} for year in year_list],
                            style = {'fontFamily': 'sans-serif', 'color': 'black'})
            ], width = {"size": 4, "order": 3}, lg = {"size": 4, "order": 3}),
        ]),
    html.Br(),
    dbc.Row([
        dbc.Col(width = {"size": 2, "order": 1}, lg = {"size": 2, "order": 1}),
        dbc.Col([
            dbc.Label("Modify number of bins: ", style = {'fontFamily': 'sans-serif', 'color': 'white'}),
            html.Br(),
            dcc.Slider(id = 'bin_slider',
                       dots = True,
                       min = 0,
                       step = 5,
                       included = False,
                       marks = {num: str(num) for num in range(0, 105, 5)}
                      ),
                ], width = {"size": 7, "order": 2}, lg = {"size": 6, "order": 2})
    ]),
    html.Br(),
    dcc.Graph(id = 'indicator_histogram'),
    html.Br(),
    dbc.Row([
        # dbc.Col(width = {"size": 2, "order": 1}, lg = {"size": 2, "order": 1}),
        dbc.Col([
            html.Div(id = 'histogram_table', style = {'fontFamily': 'sans-serif', 'color': 'black'})
        ])
    ]),
    html.Br(),
    html.H3("Gini Index", style = {
        'fontFamily': 'sans-serif',
        'textAlign': 'center',
    }),
    html.Br(),
    dbc.Row([col1, col2]),
    html.Br(),
    dbc.Row([col3, col4]),
    html.Br(),
    html.H3("Poverty Gap", style = {'fontFamily': 'sans-serif', 'textAlign': 'center'}),
    html.H5("(at $1.9, $3.2, and 5.5 (% of total population))", style = {'fontFamily': 'sans-serif', 'textAlign': 'center'}),
    html.Br(), html.Br(),
    dbc.Row([
        dbc.Col(lg=2),  # Spacer column
        dbc.Col([  # Col for the sliders
            dbc.Row([  # Nested row for the sliders
                dbc.Col([
                    dbc.Label("Select poverty level:", style={'fontFamily': 'sans-serif', 'paddingRight': '10px'}),
                    dcc.Slider(
                    id='poverty_indicator_slider',
                    min=0,
                    max=2,
                    step=1,
                    value=0,
                    included=False,
                    marks=indicator_marks
                ),
            ]),
                dbc.Col([
                    dbc.Label("Select a year:", style={'fontFamily': 'sans-serif', 'marginRight': '10px'}),
                    dcc.Slider(
                    id='percentage_poverty_year_slider',
                    min=perc_pov_years[0],
                    max=perc_pov_years[-1],
                    step=1,
                    included=False,
                    value=2018,
                    marks=year_marks
                ),
            ]),
        ]),
    ], lg=5),
    dbc.Col(lg=5),
    dcc.Graph(id = 'percentage_poverty__scatter_chart'),
]),
    html.Br(),
    dbc.Tabs([tab1, tab2]),
], style = {'fontFamily': 'sans-serif',
            'backgroundColor': '#2C3E50'})

# update callback function
@callback(Output('indicator_map_chart', 'figure'),
              Output('indicator_details', 'children'),
              Input('indicator_dropdown', 'value'))

# update the function that takes the selected indicator and returns the desired
# map chart
def display_indicator_map_chart(indicator):
    fig = px.choropleth(country_sub,
                       color = indicator,
                       locations = "Country Code",
                       color_continuous_scale = 'plotly3',
                       animation_frame = 'year',
                       hover_name = "Country Name",
                       title = indicator,
                       height = 650)
    # remove the rectangular frame around the map
    fig.layout.geo.showframe = False

    # show the country borders, even for countries without data
    fig.layout.geo.showcountries = True

    # sse a different projection of the earth
    fig.layout.geo.projection.type ='natural earth'

    # limit the vertical range of the chart to focus more on countries, by setting the
    # minimum and maximum latitude values that the map should show
    fig.layout.geo.lataxis.range = [-53, 76]

    # limit the horizontal range of the chart
    fig.layout.geo.lonaxis.range = [-137, 168]

    # change the color of the land to 'white' to make it clear which countries have
    # missing data
    fig.layout.geo.landcolor = 'white'

    # set the background color of the map (the color of the oceans), as well as the "paper"
    # background color of the figure as a whole
    fig.layout.geo.bgcolor = '#e5ecf6'
    fig.layout.paper_bgcolor = '#e5ecf6'

    # set the colors of the country borders as well as the coastlines
    fig.layout.geo.countrycolor = 'grey'
    fig.layout.geo.coastlinecolor = 'grey'

    # wrap the title of the colorbar
    fig.layout.coloraxis.colorbar.title = wrap_indicator_names(indicator)

    # subset indicator dataframe based on what a user selects
    series_subset = series[series['Indicator Name'].eq(indicator)]

    if series_subset.empty:
        markdown = "There is currently no information available on this indicator"
    else:
        # get the limitations column from the dataframe
        # replace empty rows with N/A
        # replace any instances of two newline characters, \n\n, with a single space, if any
        # extract the first element under its values attribute
        limitations = series_subset['Limitations and exceptions'].fillna('N/A').str.replace('\n\n', ' ').values[0]

        markdown = f"""
                    ### {series_subset["Indicator Name"].values[0]}
                    {series_subset["Long definition"].values[0]}

                    * **Unit of measure**: {series_subset['Unit of measure'].fillna("count").values[0]}
                    * **Periodicity**
                    {series_subset["Periodicity"].fillna("N/A").values[0]}
                    * **Source**: {series_subset["Source"].values[0]}
                    #### Limitations and exceptions
                    {limitations}
                """
    # display map and markdown
    return [fig, markdown]


# # create callbacks
@callback(Output('indicator_histogram', 'figure'),
          Output('histogram_table','children'),
          Input('indicator_histogram_dropdown', 'value'),
          Input('indicator_year_dropdown', 'value'),
          Input('bin_slider', 'value')
         )

def display_histogram(indicator, years, bin):
    if not (indicator) or not (years):
        raise PreventUpdate
    # create subset of poverty dataframe
    poverty_subset = poverty_indicator[poverty_indicator['year'].isin(years) & poverty_indicator['is_country']]
    # create histogram object
    fig = px.histogram(
        poverty_subset,
        x = indicator,
        color = 'year',
        nbins = bin,
        facet_col = 'year',
        facet_col_wrap = 4,
        height = 700,
        title = " - ".join([indicator, 'Histogram'])
    )
    # eliminate overlaping a-axis labels
    fig.for_each_xaxis(lambda axis: axis.update(title = ''))
    fig.add_annotation(text = indicator,
                       x = 0.5,
                       y = -0.12,
                       xref = 'paper',
                       yref = 'paper',
                       showarrow = False)
    fig.layout.paper_bgcolor = '#e5ecf6'
    # filter poverty dataframe

    # get columns from dataframe
    df_columns = poverty_subset[['Country Name', 'year', indicator]].columns
    # create data table
    data_table = DataTable(
                             data = poverty_subset[['Country Name', 'year', indicator]].to_dict('records'),
                             columns = [{'name': column, 'id': column} for column in df_columns],
                             # allow text to overflow into multiple lines if needed
                             style_header = {'whiteSpace': 'normal'},
                             # ensure that while scrolling, the headers remain fixed in place
                             fixed_rows = {"headers": True},
                             # control the height of the table
                             style_table = {"height": '400px'},
                             # control the display of table rows
                             virtualization = True,
                              # add the ability to sort columns
                             sort_action = 'native',
                             # add the ability to filter columns
                             filter_action = 'native',
                             # set cell minimum width
                             style_cell = {'minWidth': '140px'},
                             # enable download of table as csv
                             export_format = 'csv',
                            )
    return fig, data_table

# create first callback function
@callback(Output('gini_year_barcharts', 'figure')
              ,Input('gini_year_dropdown', 'value')
             )
def plot_gini_chart_for_selected_year(selected_year):
    if not selected_year:
        raise PreventUpdate
    df = gini_df[gini_df["Year"].eq(selected_year)].sort_values(gini).dropna(subset = [gini])
    countries = len(df["Country Name"])
    fig = px.bar(data_frame = df,
      x = gini,
      y = "Country Name",
      orientation = 'h',
      height = 200 + (20 * countries),
      # template = "plotly_dark",
      title = gini + ' - ' + str(selected_year)
            )
    # # customize hover template to display the hover information in the desired format
    # fig.update_traces(hovertemplate = 'Country Name: %{customdata[0]}<br>GINI index: %{customdata[1]}',
    #               customdata = gini_df[["Country Name", gini]])
    # fig.layout.paper_bgcolor = '#2C3E50'
    return fig
# create second callback function
@callback(Output('gini_country_barcharts', 'figure'),
             Input('gini_country_dropdown', 'value'))


def plot_gini_bar_chart_for_selected_countries(selected_countries):
    # create of list of countries
    if not selected_countries:
        raise PreventUpdate
    df = gini_df[gini_df["Country Name"].isin(selected_countries)].dropna(subset = [gini])
    fig = px.bar(data_frame = df,
      x = 'Year',
      y = gini,
      # template = "plotly_dark",
      facet_row = 'Country Name',
      labels = {gini: "Gini Index"},
      height = 100 + 250 * len(selected_countries),
      title = '<br>'.join([gini, ', '.join(selected_countries)]),

            )
    # # customize hover template to display the hover information in the desired format
    # fig.update_traces(hovertemplate = 'Country Name: %{customdata[0]}<br>GINI index: %{customdata[1]}',
    #               customdata = gini_df[["Country Name", gini]])
    # fig.layout.paper_bgcolor = '#2C3E50'

    return fig

@callback(Output('income_level_country_barchart', 'figure'),
             Input('income_level_country', 'value'))
def plot_income_share_per_country(country):
    if country is None:
        raise PreventUpdate
    fig = px.bar(income_share_df_sorted[income_share_df_sorted["Country Name"] == country],
                 x = income_share_df_sorted_col,
                 y = "Year",
                 title = " - ".join(["Income Share Quintiles", country]),
                 height = 600,
                 hover_name = "Country Name",
                 # template = 'plotly_dark',
                 barmode = 'stack',
                 orientation = 'h')

    # customize figure
    fig.layout.legend.orientation = 'h'
    fig.layout.legend.x = 0
    fig.layout.legend.title = None
    fig.layout.xaxis.title = "Percent of Total Income"
    # fig.layout.paper_bgcolor = '#2C3E50'

    return fig

@callback(Output('percentage_poverty__scatter_chart', 'figure'),
             Input('percentage_poverty_year_slider', 'value'),
             Input('poverty_indicator_slider', 'value'))
def plot_poverty_and_year_chart(year, indicator):
    indicator = poverty_gap_cols[indicator]
    df = perc_pov_df[perc_pov_df['year'].eq(year)].dropna(subset = [indicator]).sort_values(indicator)
    # handle empty data
    if df.empty:
        raise PreventUpdate
    # create scatter plot to display parameters
    fig = px.scatter(df,
                    x = indicator,
                    y = 'Country Name',
                    color = 'Population, total',
                    size = [30] * len(df),
                    size_max = 15,
                    hover_name = 'Country Name',
                    height = 500, # 250 + (20 * len(df)),
                    color_continuous_scale = 'plasma',
                    title = indicator + '<b>: ' + f'{year}' + '</b>'
                    )
    fig.layout.paper_bgcolor = '#e5ecf6'
    fig.layout.xaxis.ticksuffix = '%'
    return fig

"""#### Country Dashboard"""

country_dashboard = html.Div([
    html.Br(),
    html.H4(id = 'country_main_page'),
    html.Br(),
    dbc.Row([
        dbc.Col(dcc.Graph(id = 'country_chart'))
    ]),
    html.Br(), html.Br(),
    dbc.Row([
        dbc.Col([
            dbc.Label('Select indicator: '),
            dcc.Dropdown(id = 'country_indicator_dropdown',
                        placeholder = 'Choose an indicator',
                        value = 'Population, total',
                        options = [{'label': indicator, 'value': indicator} for indicator in indicator_list],
                        style = {'color': 'blackk'}),
        ]),
        dbc.Col([
            dbc.Label("Select countries: "),
            dcc.Dropdown(id = 'country_page_country_dropdown',
                         placeholder = 'Select multiple countries to compare',
                         multi = True,
                         options = [{'label': country, 'value': country} for country in country_list],
                         style = {'color': 'black'}),

        ]),
    ]),
    html.Br(), html.Br(),
    html.Div(id = 'country_table')
])

"""#### Validation Layout"""

app.validation_layout = html.Div([
    main_layout,
    indicators_dashboard,
    country_dashboard
])

# set up app's layout
app.layout = main_layout

@callback(Output("main_content", "children"),
         Input("location", "pathname"))
def display_page(country_name):
    # deal with country names with spaces
    if unquote(country_name[1:]) in country_list:
        return country_dashboard
    else:
        return indicators_dashboard

@callback(Output('country_page_country_dropdown', 'value'),
         Input('location', 'pathname'))
def set_drop_down_countries(country_path):
    if unquote(country_path[1:]) in country_list:
        count = unquote(country_path[1:])
        return [count]

@callback(Output('country_main_page', 'children'),
          Output('country_chart', 'figure'),
          Output('country_table', 'children'),
          Input('location', 'pathname'),
          Input('country_page_country_dropdown', 'value'),
          Input('country_indicator_dropdown', 'value')
         )
def plot_country_graph(pathname, country_list, indicator):
    if (not country_list) or (not indicator):
        raise PreventUpdate
    if unquote(pathname[1:]) in country_list:
        count = unquote(pathname[1:])
    df = poverty_indicator[poverty_indicator['is_country'] & poverty_indicator['Country Name'].isin(country_list)]
    fig = px.line(df,
                 x = 'year',
                 y = indicator,
                 title = '<b>' + indicator + '</b><br />' + ','.join(country_list),
                 color = 'Country Name'
                 )
    fig.layout.paper_bgcolor = '#E5ECF6'
    table = country[country['Short Name'] == country_list[0]].T.reset_index()
    if table.shape[1] == 2:
        table.columns = [country_list[0] + ' info', '']
        table = dbc.Table.from_dataframe(table)
    else:
        table = html.Div()
    return count + ' Poverty Data', fig, table
if __name__ == '__main__':
    app.run()