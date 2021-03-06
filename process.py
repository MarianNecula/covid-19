from dataflows import Flow, load, unpivot, find_replace, set_type, dump_to_path, update_package, update_resource, join, join_with_self, add_computed_field, delete_fields, checkpoint, duplicate

BASE_URL = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/'
CONFIRMED = 'time_series_19-covid-Confirmed.csv'
DEATH = 'time_series_19-covid-Deaths.csv'
RECOVERED = 'time_series_19-covid-Recovered.csv'

def to_normal_date(row):
    old_date = row['Date']
    month, day, year = row['Date'].split('-')
    day = f'0{day}' if len(day) == 1 else day
    month = f'0{month}' if len(month) == 1 else month
    row['Date'] = '-'.join([day, month, year])

unpivoting_fields = [
    { 'name': '([0-9]+\/[0-9]+\/[0-9]+)', 'keys': {'Date': r'\1'} }
]

extra_keys = [{'name': 'Date', 'type': 'string'} ]
extra_value = {'name': 'Case', 'type': 'number'}

Flow(
      load(f'{BASE_URL}{CONFIRMED}'),
      load(f'{BASE_URL}{RECOVERED}'),
      load(f'{BASE_URL}{DEATH}'),
      checkpoint('load_data'),
      unpivot(unpivoting_fields, extra_keys, extra_value),
      find_replace([{'name': 'Date', 'patterns': [{'find': '/', 'replace': '-'}]}]),
      to_normal_date,
      set_type('Date', type='date', format='%d-%m-%y', resources=None),
      set_type('Case', type='number', resources=None),
      join(
        source_name='time_series_19-covid-Confirmed',
        source_key=['Province/State', 'Country/Region', 'Date'],
        source_delete=True,
        target_name='time_series_19-covid-Deaths',
        target_key=['Province/State', 'Country/Region', 'Date'],
        fields=dict(Confirmed={
            'name': 'Case',
            'aggregate': 'first'
        })
      ),
      join(
        source_name='time_series_19-covid-Recovered',
        source_key=['Province/State', 'Country/Region', 'Date'],
        source_delete=True,
        target_name='time_series_19-covid-Deaths',
        target_key=['Province/State', 'Country/Region', 'Date'],
        fields=dict(Recovered={
            'name': 'Case',
            'aggregate': 'first'
        })
      ),
      add_computed_field(
        target={'name': 'Deaths', 'type': 'number'},
        operation='format',
        with_='{Case}'
      ),
      delete_fields(['Case']),
      update_resource('time_series_19-covid-Deaths', name='time-series-19-covid-combined', path='data/time-series-19-covid-combined.csv'),
      update_package(name='covid-19', title='Novel Coronavirus 2019'),
      dump_to_path(),
      checkpoint('processed_data'),
      # Duplicate the stream to create aggregated data
      duplicate(
        source='time-series-19-covid-combined',
        target_name='worldwide-aggregated',
        target_path='worldwide-aggregated.csv'
      ),
      join_with_self(
        resource_name='worldwide-aggregated',
        join_key=['Date'],
        fields=dict(
            Date={
                'name': 'Date'
            },
            Confirmed={
                'name': 'Confirmed',
                'aggregate': 'sum'
            },
            Recovered={
                'name': 'Recovered',
                'aggregate': 'sum'
            },
            Deaths={
                'name': 'Deaths',
                'aggregate': 'sum'
            }
        )
      ),
      dump_to_path()
).results()[0]
