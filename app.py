"""The WACC card.

Run from the repo root:   streamlit run app.py

Owner: the product manager. This works today on the FAKE numbers, so you can build
the page before the real numbers exist. When the developer's pull request is merged,
outputs/wacc.csv appears and the app switches to it automatically.

The app only reads outputs/ and inputs/. The what-if section is arithmetic on those
numbers (no downloads, no re-estimation). Row 1 of wacc.csv is the client; any extra
rows the developer adds are shown as competitors.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title='WACC card', layout='centered')

real = Path('outputs/wacc.csv')
rows = pd.read_csv(real if real.exists() else 'outputs/wacc_FAKE.csv')
card = rows.iloc[0]
peers = rows.iloc[1:]
inputs = pd.read_csv('inputs/assumptions.csv', index_col='item')

assert abs(card['w_e'] + card['w_d'] - 1) < 1e-6, 'weights in wacc.csv must sum to 1'
assert 0 < card['wacc'] < 0.25, 'WACC outside 0-25%: check outputs/wacc.csv'

if not real.exists():
    st.warning('Showing FAKE numbers. Run `python code/wacc.py` to make outputs/wacc.csv.')

ticker, wacc = card['ticker'], card['wacc']
rd_after_tax = card['rd'] * (1 - card['tax'])

# --- The answer ---------------------------------------------------------------
st.title(f'{ticker}: hurdle rate for new projects')
st.markdown(f'## New projects should earn at least **{wacc:.1%}** a year.')
st.write(
    f"That is {ticker}'s weighted average cost of capital (WACC): the return its "
    'shareholders and lenders require, blended. A project as risky as the existing '
    'business that earns less than this destroys value. Riskier projects need a higher bar.'
)

c1, c2, c3, c4 = st.columns(4)
c1.metric('WACC (hurdle rate)', f'{wacc:.1%}')
c2.metric('Cost of equity', f"{card['cost_of_equity']:.1%}")
c3.metric('Cost of debt, after tax', f'{rd_after_tax:.1%}')
c4.metric('Beta vs. market', f"{card['beta']:.2f}")

st.caption(
    f"How it adds up: {card['w_e']:.0%} equity at {card['cost_of_equity']:.1%} "
    f"+ {card['w_d']:.0%} debt at {rd_after_tax:.1%} after tax = {wacc:.1%}. "
    f"Beta from 5 years of daily returns through {card['asof']}."
)

# --- What if ------------------------------------------------------------------
st.subheader('What if?')
s1, s2 = st.columns(2)
w_d = s1.slider('Debt share of capital', 0, 60, round(card['w_d'] * 100), 5, format='%d%%') / 100
mrp = s2.slider('Market risk premium', 3.0, 8.0, round(card['mrp'] * 100, 1), 0.5, format='%.1f%%') / 100

# More debt makes the equity riskier: unlever beta at today's mix, relever at the new one.
beta_u = card['beta'] / (1 + (1 - card['tax']) * card['w_d'] / card['w_e'])
beta_new = beta_u * (1 + (1 - card['tax']) * w_d / (1 - w_d))
ke_new = card['rf'] + beta_new * mrp
wacc_new = (1 - w_d) * ke_new + w_d * rd_after_tax

st.metric('WACC under these assumptions', f'{wacc_new:.1%}',
          delta=f'{(wacc_new - wacc) * 100:+.2f} pts vs. base case', delta_color='off')
st.caption(
    f'Debt share {w_d:.0%}, market risk premium {mrp:.1%}, beta relevered to {beta_new:.2f}. '
    'Cost of debt held at today\'s rate; in practice it rises as leverage grows.'
)

# --- Competitors (only if the developer adds rows to wacc.csv) ----------------
if not peers.empty:
    st.subheader('Against competitors')
    table = pd.DataFrame({
        'Company': rows['ticker'],
        'WACC': rows['wacc'].map('{:.1%}'.format),
        'Cost of equity': rows['cost_of_equity'].map('{:.1%}'.format),
        'Beta': rows['beta'].map('{:.2f}'.format),
        'Debt share': rows['w_d'].map('{:.0%}'.format),
    })
    st.dataframe(table, hide_index=True, width='stretch')

# --- Inputs and sources -------------------------------------------------------
with st.expander('Inputs and sources'):
    labels = {
        'rf': 'Risk-free rate', 'mrp': 'Market risk premium', 'rd': 'Cost of debt (pre-tax)',
        'tax': 'Tax rate', 'w_e': 'Equity share of capital', 'w_d': 'Debt share of capital',
    }
    used = pd.DataFrame({
        'Input': ['Beta', *labels.values()],
        'Value': [f"{card['beta']:.2f}", *(f'{card[k]:.1%}' for k in labels)],
        'Source': ['5y daily returns vs. SPY (code/wacc.py)', *inputs.loc[list(labels), 'source']],
    })
    st.dataframe(used, hide_index=True, width='stretch')

    stale = [labels[k] for k in labels if abs(inputs.loc[k, 'value'] - card[k]) > 1e-9]
    if stale:
        st.warning(f"inputs/assumptions.csv changed since wacc.csv was made ({', '.join(stale)}). "
                   'Rerun `python code/wacc.py`.')
