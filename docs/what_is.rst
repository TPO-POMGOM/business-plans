.. |bp| replace:: ``business_plans``

What is |bp| ?
==============

|bp| is a package for modeling and managing business plans in Python.

Modeling a business case in Python is quite straightforward, using the `pandas`
library and the ``pandas.Series`` abstraction, as illustrated in Stefan
Thelin's excellent article `Python and Finance – Power Up Your Spreadsheets
<https://www.toptal.com/finance/financial-modeling/python-and-finance>`_.

Thelin undertakes to model the following business case:

  .. figure:: what_is_fig1.jpg

    Figure 1 -- The business case to be modelled

He proposes the following code:

.. code-block:: python

    import pandas as pd

    years = ['2018A', '2019B', '2020P', '2021P', '2022P', '2023P']
    sales = pd.Series(index=years)
    sales['2018A'] = 31.0
    growth_rate = 0.1
    for year in range(1, 6):
        sales[year] = sales[year - 1] * (1 + growth_rate)
    print("Sales")
    print(sales)
    ebitda_margin = 0.14
    depr_percent = 0.032
    ebitda = sales * ebitda_margin
    depreciation = sales * depr_percent
    ebit = ebitda - depreciation
    nwc_percent = 0.24
    nwc = sales * nwc_percent
    change_in_nwc = nwc.shift(1) - nwc
    capex_percent = depr_percent
    capex = -(sales * capex_percent)
    tax_rate = 0.25
    tax_payment = -ebit * tax_rate
    tax_payment = tax_payment.apply(lambda x: min(x, 0))
    free_cash_flow = ebit + depreciation + tax_payment + capex + change_in_nwc
    print("\nFree cash flow")
    print(free_cash_flow)

The code produces the expected output::

    Sales
    2018A    31.00000
    2019B    34.10000
    2020P    37.51000
    2021P    41.26100
    2022P    45.38710
    2023P    49.92581
    dtype: float64

    Free cash flow
    2018A         NaN
    2019B    2.018100
    2020P    2.219910
    2021P    2.441901
    2022P    2.686091
    2023P    2.954700
    dtype: float64

While this approach works fine for a quick simulation, package |bp| provides
several features which more significant projects would require. These features
are described in the following sections.


Mixing historical data and simulations
--------------------------------------

Most of the time, the lines in a business plan are composed of:

    - Historical data ("actuals" in the example above, i. e. years 2016 --
      2018)

    - Values which are the outcome of a simulation ("projections" in the
      example above, i. e. years 2019 -- 2023)

Let's illustrate this by modelling sales in the example above using package
|bp|:

.. code-block:: python
    :linenos:

    from business_plans.bp import actualise, BP

    sample_bp = BP("Sample", start=2016, end=2023)
    growth_rate = 0.1
    sample_bp.bp.line(name="Sales",
                      history=[25.6, 28.1, 31.0],
                      simulation=actualise(percent=growth_rate))
    print(sample_bp["Sales"])

Here is the output::

    2016    25.60000
    2017    28.10000
    2018    31.00000
    2019    34.10000
    2020    37.51000
    2021    41.26100
    2022    45.38710
    2023    49.92581
    Name: Sales, dtype: float64

One obvious difference with the first approach is that the business plan line
modelling sales now
covers *all* years in the business plan, i. e. both the history
period and the simulated period. This will come in handy when building graphs
to show the results of the business plan, as we will see later.

Lines 5 to 8 are where the business plan line is setup. We can specify in one
method call: a name for the business plan line, history values, and how to
simulate future values. Note that line 8 only specifies the method used for the
simulation, and need not specify explicitely a start year, which is deduced
from history data, or an end year, which is specified only once when creating
the business plan object, on line 3 (more on that later).


lines are named

- **Feature 2 -- The most common simulation cases are built-in** and need not
  be developped from scratch for each business case. Such common simulations
  include:

    - x% growth YoY (`sales` in the example above)

    - x% actualisation of the value for a reference year

    - actualise by x% and cumulate values from a business plan line into
      another (typically: compute the balance of a fixed rate deposit account
      from the yearly deposits)

- **Feature 3 -- All the lines in a business plan can be groupe into one
  'business plan' object** and manipulated as a whole.

- **Feature 4 -- scenarios can be explored, by applying different assumptions
  to the same model**, each set of assumptions generating a different 'business
  plan' object.

- There must be an easy way of comparing the outcome of several scenarios