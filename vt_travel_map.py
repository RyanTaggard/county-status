import pandas as pd  # Version 1.1.1

# %%
region = ['Vermont', 'New Hampshire', 'Maine', 'Rhode Island', 'Massachusetts',
          'Connecticut', 'New Jersey', 'Pennsylvania', 'Ohio', 'Maryland',
          'District of Columbia', 'Delaware', 'Virginia', 'West Virginia',
          'New York']

undetected_factor = 2.4

green = 1
yellow = 2
red = 3

# %% Defines the active case calculation
prop = [1, 0.94594234, 0.8585381, 0.76322904, 0.66938185,
        0.58139261, 0.50124929, 0.42963663, 0.36651186, 0.31143254,
        0.26375154, 0.22273485, 0.18763259, 0.15772068, 0.1323241,
        0.11082822, 0.09268291, 0.077402, 0.06456005, 0.0537877,
        0.04476636, 0.03722264, 0.03092299, 0.02566868, 0.02129114,
        0.0176478, 0.01461838, 0.01210161, 0.01001242, 0.00827947]
prop = prop[::-1]


def active_cases(x):
    tmp = []
    for i, j in zip(prop, x):
        tmp.append(i * j)
    return sum(tmp) * undetected_factor


def status_num(x):
    if x <= 400:
        return green
    elif x <= 800:
        return yellow
    else:
        return red


# %% Takes population values from JHU, which in turn come from US Census
# estimates for 2019
pops_url = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/'\
    'csse_covid_19_data/csse_covid_19_time_series/'\
    'time_series_covid19_deaths_US.csv'
county_pops = pd.read_csv(pops_url)
county_pops = county_pops[county_pops.Province_State.isin(region)]
county_pops = county_pops[['FIPS', 'Population']]

county_pops.FIPS = county_pops.FIPS.astype('str')
county_pops.FIPS = county_pops.FIPS.str[:-2]
county_pops.loc[county_pops.FIPS.str.len() == 4, 'FIPS'] =\
    '0' + county_pops.loc[county_pops.FIPS.str.len() == 4, 'FIPS']

# %% Takes county level infection data from JHU
hopkinsurl = 'https://raw.githubusercontent.com/CSSEGISandData/'\
    'COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/'\
    'time_series_covid19_confirmed_US.csv'
hopkins = pd.io.parsers.read_csv(hopkinsurl, dtype={'FIPS': 'str'})

hopkins.FIPS = hopkins.FIPS.str[:-2]
tmp = hopkins.loc[hopkins.FIPS.str.len() == 4, 'FIPS'].copy()
hopkins.loc[hopkins.FIPS.str.len() == 4, 'FIPS'] = '0' + tmp
hopkins = hopkins[hopkins.FIPS < '70000']

hop_ne = hopkins[hopkins.Province_State.isin(region)]

# %% Takes county level infection data for Dukes, MA and Nantucket, MA from
# the New York Times
ny_times_path = 'https://raw.githubusercontent.com/nytimes/covid-19-data/'\
    'master/us-counties.csv'
times = pd.read_csv(ny_times_path, dtype={'fips': 'str'})
times.date = pd.to_datetime(times.date)
ma_islands = times[times.county.isin(['Dukes', 'Nantucket'])]
ma_islands = ma_islands.pivot(columns='date', index='county', values='cases')
ma_islands = ma_islands.iloc[:, -31:].diff(axis=1).dropna(axis=1)
ma_islands = ma_islands.clip(lower=0)

# %% Applies the VT DFR's active case algorithm
hop_ne = hop_ne.assign(active_cases=0)

for i in range(hop_ne.shape[0]):
    tmp = hop_ne.iloc[i, -32:-1].diff().clip(lower=0).dropna()
    hop_ne.iloc[i, -1] = active_cases(tmp)
hop_ne.loc[hop_ne.Admin2 == 'Dukes', 'active_cases'] =\
    active_cases(ma_islands.loc['Dukes'].clip(lower=0))
hop_ne.loc[hop_ne.Admin2 == 'Nantucket', 'active_cases'] =\
    active_cases(ma_islands.loc['Nantucket'].clip(lower=0))

# %% Normalizes the estimated active case counts based on population
df = hop_ne[['FIPS', 'Admin2', 'Province_State', 'active_cases']]
df = pd.merge(df, county_pops, on='FIPS')

df = df.assign(case_rate=0)
df.case_rate = df.active_cases / df.Population * 1e6

# %% Creates a numerical category formerly used to make the map
# and now useful for historical analysis
df = df.assign(status=0)
df.status = df.case_rate.apply(status_num)

# %% Renames columns, rounds values, and saves table
df = df.rename(columns={'Admin2': 'County',
                        'Province_State': 'State',
                        'active_cases': 'Active Cases',
                        'case_rate': 'Active Cases per Million',
                        'status': 'Status_num'})
df['Active Cases'] = df['Active Cases'].astype('int')
df['Active Cases per Million'] = df['Active Cases per Million'].astype('int')

df.to_csv('Step 1 Counties.csv')
