import plotly.express as px
import numpy as np
import pandas as pd
from urllib.request import urlopen
import json
import plotly.io as pio

# Created by the Vermont Department of Financial Regulation
# Run in Atom's Hydrogen package

# %% Defines functions used later on in the map
safe = '<400 Active Cases per Million<br>(No Quarantine Required)'
mixed = '<br>400-799 Active Cases per Million<br>(Quarantine Required'\
    ' in<br>Vermont or Home State)'
unsafe = '<br>800+ Active Cases per Million<br>(Quarantine Required in'\
    '<br>Vermont or Home State)<br>'

safe_vt = '<400 Active Cases per Million (VT)'
mixed_vt = '400-799 Active Cases per Million (VT)'
unsafe_vt = '800+ Active Cases per Million (VT)'

factor = 2.4


def to_len(x, i):
    # Converts any string to desired length by adding initial
    # zeros or deleting final characters
    if len(x) < i:
        diff = i-len(x)
        return diff*'0' + x
    if len(x) > i:
        return x[:i]
    else:
        return x


def to_status(x, y):
    # Determines the status of a county based on active cases per million
    if y == 'Vermont':
        if x < 400:
            return safe_vt
        elif x < 800:
            return mixed_vt
        else:
            return unsafe_vt
    elif x < 400:
        return safe
    elif x < 800:
        return mixed
    else:
        return unsafe


# %% Gets county outlines from plotly
with urlopen('https://raw.githubusercontent.com/plotly/datasets/'
             'master/geojson-counties-fips.json') as response:
    counties = json.load(response)

# %% Takes most recent data from JHU GitHub repo
hopkinsurl = 'https://raw.githubusercontent.com/CSSEGISandData/'\
    'COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/'\
    'time_series_covid19_confirmed_US.csv'
hopkins = pd.io.parsers.read_csv(hopkinsurl)
hop_ne = hopkins[(hopkins['Province_State'] == 'Vermont') |
                 (hopkins['Province_State'] == 'New Hampshire') |
                 (hopkins['Province_State'] == 'Maine') |
                 (hopkins['Province_State'] == 'Rhode Island') |
                 (hopkins['Province_State'] == 'Massachusetts') |
                 (hopkins['Province_State'] == 'Connecticut') |
                 (hopkins['Province_State'] == 'New Jersey') |
                 (hopkins['Province_State'] == 'Pennsylvania') |
                 (hopkins['Province_State'] == 'Ohio') |
                 (hopkins['Province_State'] == 'Maryland') |
                 (hopkins['Province_State'] == 'District of Columbia') |
                 (hopkins['Province_State'] == 'Delaware') |
                 (hopkins['Province_State'] == 'Virginia') |
                 (hopkins['Province_State'] == 'West Virginia') |
                 (hopkins['Province_State'] == 'New York')]

# %%
# Values obtained from our gamma distribution equal to
# 1 - CDF for the first 30 integer values of x
prop = [1, 0.9486632702, 0.864870849, 0.7727784056,
        0.6814356899, 0.5951939501, 0.5161053777,
        0.4449605251, 0.3818322198, 0.3263880516,
        0.2780783636, 0.2362516399, 0.2002254171,
        0.1693291345, 0.1429289957, 0.1204412361,
        0.1013379529, 0.0851482333, 0.0714563987,
        0.0598985719, 0.0501583661, 0.0419622164,
        0.0350746871, 0.0292939607, 0.0244476271,
        0.0203888345, 0.0169928249, 0.0141538527,
        0.0117824696, 0.0098031505]
gamma = pd.DataFrame({'prop': prop})

# These values are used to calculate active cases via the methodology explained
# in the DFR whitepaper
new = hop_ne.iloc[:, -31:].transpose().diff().dropna()

temp2 = []
for j in np.arange(new.shape[1]):
    temp = []
    for i in np.arange(len(new)):
        var = new.iloc[:, j][29 - i] * gamma.iloc[i]
        temp.append(var)
    var2 = np.sum(temp)
    if var2 < 0:
        var2 = 0
    temp2.append(var2)

hop_ne['Active Cases'] = temp2
hop_ne['Active Cases'] = hop_ne['Active Cases'] * factor

# Gets rid of some columns we don't need
hop_ne_trim = hop_ne[['UID',
                      'FIPS', 'Admin2', 'Province_State', 'Country_Region',
                      'Lat', 'Long_', 'Combined_Key', 'Active Cases']]
hop_ne_trim = hop_ne_trim.dropna()

# %% JHU doesn't report NCY boroughs individually, so we break them out manually
# The file below is obtained from https://health.data.ny.gov/Health
# /New-York-State-Statewide-COVID-19-Testing/xdss-u53e/data
# File path will vary by user, so change accordingly if you're trying to
# replicate this code
boro = pd.read_csv('/Users/ryantaggard/Desktop/COVID-19/Current County'
                   ' Status Map/Interactive/NYC_Boro.csv')
boro = boro[boro['County'].isin(['Bronx', 'Queens', 'Kings',
                                 'Richmond', 'New York'])]
boro = boro[['Test Date', 'County', 'New Positives']]
boro['Test Date'] = pd.to_datetime(boro['Test Date'])
boro = boro.pivot_table(index='Test Date', columns='County',
                        values='New Positives')
boro = boro.iloc[-30:, :].reset_index()

boro['prop'] = gamma.reindex(index=gamma.index[::-1])\
    .reset_index().drop('index', axis=1)

nycfips = {'Bronx': 36005,
           'Kings': 36047,
           'New York': 36061,
           'Queens': 36081,
           'Richmond': 36085}

hop_ne_trim = hop_ne_trim.set_index('FIPS')

# Active case counts are determined for the NYC boroughs
for i in ['Bronx', 'Kings', 'New York', 'Queens', 'Richmond']:
    hop_ne_trim['Active Cases'][nycfips[i]] =\
        boro[[i, 'prop']].prod(axis=1).sum()*factor

hop_ne_trim = hop_ne_trim.reset_index()

# %%
# Population estimates taken from the US census available at
# https://www2.census.gov/programs-surveys/popest/datasets/
# 2010-2019/counties/totals/

# Filepath will vary by user
pops_path = '/Users/ryantaggard/Desktop/COVID-19/Current County Status Map/'\
    'co-est2019-alldata.csv'
pops = pd.read_csv(pops_path, encoding='Latin-1')
pops = pops[['STATE', 'COUNTY', 'STNAME', 'CTYNAME', 'POPESTIMATE2019']]
pops = pops[pops['COUNTY'] != 0]

pops['STATE'] = pops['STATE'].astype(str)
pops['COUNTY'] = pops['COUNTY'].astype(str)

# %% Get FIPS codes from state and county IDs
pops.STATE = pops.STATE.apply(to_len, args=(2,))
pops.COUNTY = pops.COUNTY.apply(to_len, args=(3,))
pops['FIPS'] = pops['STATE'] + pops['COUNTY']

# %% Add initial zeros to fips codes without them
hop_ne_trim
hop_ne_trim.FIPS = hop_ne_trim.FIPS.astype(str)
hop_ne_trim.FIPS = hop_ne_trim.FIPS.str.replace(r'.', '')
hop_ne_trim.FIPS = hop_ne_trim.FIPS.map(lambda x: str(x)[:-1])
hop_ne_trim.FIPS = hop_ne_trim.FIPS.apply(to_len, args=(5,))

# %% Merge census and active case data
hop_ne_trim = hop_ne_trim.set_index('FIPS')
pops = pops.set_index('FIPS')
merged = final.join(pops)
merged = merged.dropna()

# %% Calculate active cases per million
merged['per_mm'] = merged['Active Cases']/merged['POPESTIMATE2019']*1000000
merged['Status'] = merged[['per_mm', 'Province_State']]\
    .apply(lambda x: to_status(*x), axis=1)

# Rename columns and round case numbers to clean up data
merged = merged.rename(columns={'Admin2': 'County',
                                'Province_State': 'State',
                                'POPESTIMATE2019': 'Population',
                                'per_mm': 'Active Cases per Million'})
merged = merged[['State', 'County', 'Active Cases',
                 'Population', 'Active Cases per Million',
                 'Status']].dropna()

merged['Active Cases per Million'] =\
    np.round(merged['Active Cases per Million'], 2)

# %% Get full name to display in map
merged['Full Name'] = merged['County'] + ', ' + merged['State']

# %% Map colors
palette = ['#00bbb8', '#ffbc35', '#ec001f', '#0073e7', '#005dbb', '#064789']

# %% Adding dummy values makes the following labels show even when VT has
# no counties at these levels
save = merged
save.loc[12, 'Status'] = '800+ Active Cases per Million (VT)'
save.loc[13, 'Status'] = '400-799 Active Cases per Million (VT)'

# %%
warning = 'Note: Vermont counties are provided for<br>informational purposes '\
    'only as Vermont<br>is not subject to this policy. Instead it is<br>'\
    'monitored with separate metrics.'
save = merged.rename(columns={'Status': warning}).reset_index()
order = {warning: [safe, mixed, unsafe,
                   safe_vt, mixed_vt, unsafe_vt]}
fig = px.choropleth_mapbox(save, geojson=counties, locations='FIPS',
                           color=warning,
                           center={"lat": 41.0458, "lon": -75.2479},
                           color_discrete_sequence=extended,
                           opacity=1,
                           title='VT Neighbors',
                           category_orders=order,
                           mapbox_style="carto-positron", zoom=4,
                           hover_name='Full Name',
                           hover_data={'Active Cases per Million': True,
                                       'FIPS': False,
                                       warning: False})
fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
fig.update_layout(legend=dict(y=0.9))

pio.write_html(fig, file='index.html', auto_open=True)
save = save.rename(columns={warning: 'Status'})
