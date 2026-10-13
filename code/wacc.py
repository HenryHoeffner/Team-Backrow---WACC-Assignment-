"""Estimate the client's WACC.

Run from the repo root:   python code/wacc.py
Reads:  inputs/assumptions.csv
Writes: outputs/wacc.csv (one row; the columns are listed in README.md)

Owner: the developer. Fill in the three TODO functions (your agent can help),
then run it and check the numbers make sense before you open a pull request.
"""
import pandas as pd
import yfinance as yf

CLIENT = 'EMN'  # Eastman Chemical Co. (the CEO picked it in README.md)
MKT = 'SPY'
YEARS = 5


def get_returns(ticker, mkt=MKT, years=YEARS):
    """Daily returns for the client and the market over the last `years` years.
    Returns a DataFrame with two columns, named ticker and mkt, and no missing values."""
    start = pd.Timestamp.today().normalize() - pd.DateOffset(years=years)
    px = yf.download([ticker, mkt], start=start, auto_adjust=True, progress=False)['Close']
    assert not px.empty, f'no prices downloaded for {ticker} and {mkt}'
    rets = px[[ticker, mkt]].pct_change().dropna()
    assert not rets.isna().any().any(), 'returns contain missing values'
    return rets


def estimate_beta(rets, ticker, mkt=MKT):
    """Equity beta: cov(stock, market) / var(market)."""
    beta = rets[ticker].cov(rets[mkt]) / rets[mkt].var()
    assert pd.notna(beta), 'beta is missing: check the returns'
    return float(beta)


def compute_wacc(beta, a):
    """a is a dict of assumptions: rf, mrp, rd, tax, w_e, w_d.
    Returns a dict with cost_of_equity and wacc (and the inputs), matching the README's columns."""
    cost_of_equity = a['rf'] + beta * a['mrp']
    wacc = a['w_e'] * cost_of_equity + a['w_d'] * a['rd'] * (1 - a['tax'])
    return {'rf': a['rf'], 'mrp': a['mrp'], 'cost_of_equity': cost_of_equity,
            'rd': a['rd'], 'tax': a['tax'], 'w_e': a['w_e'], 'w_d': a['w_d'], 'wacc': wacc}


if __name__ == '__main__':
    a = pd.read_csv('inputs/assumptions.csv', index_col='item')['value'].to_dict()
    assert abs(a['w_e'] + a['w_d'] - 1) < 1e-6, 'weights must sum to 1'

    rets = get_returns(CLIENT)
    assert len(rets) > 1000, 'expected about 5 years of daily returns'

    beta = estimate_beta(rets, CLIENT)
    out = compute_wacc(beta, a)
    out = {'ticker': CLIENT, 'asof': rets.index.max().date(), 'beta': beta, **out}

    assert 0 < out['wacc'] < 0.25, 'WACC outside 0-25%: check the inputs'
    cols = ['ticker', 'asof', 'beta', 'rf', 'mrp', 'cost_of_equity', 'rd', 'tax', 'w_e', 'w_d', 'wacc']
    pd.DataFrame([out])[cols].to_csv('outputs/wacc.csv', index=False)
    print(pd.DataFrame([out])[cols].T)
