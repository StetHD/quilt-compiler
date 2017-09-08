import re
import pandas as pd
from pandas import DataFrame as df
import numpy

# these are defined as globals so importing the library results in clean syntax
# like this:  qc.data[colname], qc.env, qc.filename, etc.
filename = None                 # pylint:disable=C0103
data = None                     # pylint:disable=C0103
env = 'default'                 # pylint:disable=C0103
seed = 0  # for reproducibility             # pylint:disable=C0103

class CheckFunctionsReturn(Exception):
    def __init__(self, result):
        super(CheckFunctionsReturn, self).__init__()
        self.result = result

class CheckFunctionsException(Exception):
    def __init__(self, result):
        super(CheckFunctionsException, self).__init__()
        self.result = result

def check(expr, envs=None):
    global env                  # pylint:disable=C0103
    if envs is not None:
        override = envs.get(env)
        if override:
            expr = override
        # TODO: error if env is missing?
    raise CheckFunctionsReturn(expr)

def print_recnums(msg, expr, maxrecs=30):
    matching_recs = [str(i) for i, val in enumerate(expr) if val]
    print('{}: {}{}'.format(msg, ",".join(matching_recs[0:maxrecs]),
                            "" if len(matching_recs) < maxrecs else ",..."))

def data_sample(*args, **kwargs):
    global data, seed           # pylint:disable=C0103
    if 'seed' in args:
        seed = kwargs['seed']
    if 'random_state' not in args:
        kwargs['random_state'] = numpy.random.random_sample # pylint:disable=E1101
    data = data.sample(*args, **kwargs)

def check_column_enum(colrx, lambda_or_listexpr, envs=None):
    if envs not in [None, 'default']:
        check_column_regexp(colrx, envs[env])
    for colname in list(data):
        if re.search(colrx, colname):
            if callable(lambda_or_listexpr):
                check(lambda_or_listexpr(data[colname]))
            else:
                check(df.all(data[colname].isin(lambda_or_listexpr)))

VALRANGE_FUNCS = {
    'mean':     lambda col, minval, maxval: check(minval <= col.mean() <= maxval),
    'mode':     lambda col, minval, maxval: check(minval <= col.mode() <= maxval),
    'stddev':   lambda col, minval, maxval: check(minval <= col.std() <= maxval),
    'variance': lambda col, minval, maxval: check(minval <= col.var() <= maxval),
    'median':   lambda col, minval, maxval: check(minval <= col.median() <= maxval),
    'sum':      lambda col, minval, maxval: check(minval <= col.sum() <= maxval),
    'count':    lambda col, minval, maxval: check(minval <= col.count() <= maxval),
    'abs':      lambda col, minval, maxval: check(
        df.all(col.between(minval, maxval, inclusive=True))),
}
VALRANGE_FUNCS['avg'] = VALRANGE_FUNCS['mean']
VALRANGE_FUNCS['std'] = VALRANGE_FUNCS['stdev'] = VALRANGE_FUNCS['stddev']
VALRANGE_FUNCS['var'] = VALRANGE_FUNCS['variance']
                
def check_column_valrange(colrx, minval=None, maxval=None, lambda_or_name=None, envs=None):
    if envs not in [None, 'default']:
        check_column_regexp(colrx, envs[env])
    for colname in list(data):
        if re.search(colrx, colname):
            col = data[colname]
            if callable(lambda_or_name):
                col = lambda_or_name(col)
            if minval is None and maxval is None:
                raise CheckFunctionsException(
                    'check_column_valrange() requires minval or maxval')
            minval = col.min() if minval is None else minval
            maxval = col.max() if maxval is None else maxval
            if lambda_or_name in VALRANGE_FUNCS:
                return VALRANGE_FUNCS[col]
            raise CheckFunctionsException(
                'check_column_valrange(): unknown func: %s' % (lambda_or_name))

def check_column_regexp(colrx, regexp, envs=None):
    if envs not in [None, 'default']:
        check_column_regexp(colrx, envs[env])
    for colname in list(data):
        if re.search(colrx, colname):
            check(df.all(data[colname].str.match(regexp)))

def check_column_substr(colrx, substr, envs=None):
    if envs not in [None, 'default']:
        check_column_regexp(colrx, envs[env])
    for colname in list(data):
        if re.search(colrx, colname):
            check(df.all(data[colname].str.index(substr) != -1))

def check_column_datetime(colrx, fmt, envs=None):
    if envs not in [None, 'default']:
        check_column_regexp(colrx, envs[env])
    for colname in list(data):
        if re.search(colrx, colname):
            try:
                pd.to_datetime(data[colname], format=fmt, errors='raise')
            except Exception as ex:
                raise CheckFunctionsReturn(str(ex))