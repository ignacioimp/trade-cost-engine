# Trade Cost Engine

Offline, dependency-free Python prototype for estimating and reconciling landed-cost records. Designed for transparent review of forecast, invoiced and paid costs, without exposing company-specific calculations.

## Quick start

Python 3.10+; no network or API credentials required. From the repository root:

```sh
python engine.py examples/synthetic.json
python -m unittest discover -s tests -v
```

## Input contract

See [synthetic example](examples/synthetic.json). `base_currency`, `quantity` and `fx_to_base` are required; FX means base currency per one unit of source currency. Amounts and rates should be decimal strings. `forecast` holds one row per `cost_id`; `actual` holds invoice lines keyed by vendor, invoice and line; `payments` holds globally unique payment IDs allocated to one invoice line each. Each row has a currency and amount. Optional `recoverable` is explicitly supplied in that row's currency (not inferred). All amounts must be nonnegative. Include goods, freight, insurance, duties, local transport or other categories as separate IDs as applicable; avoid double counting included Incoterm components.

## Output and boundaries

Gross, recoverable and economic costs are distinct. Unit costs divide economic totals by the supplied quantity. Actual totals are recorded amounts, not guaranteed final cost. Exact repeated invoice lines/payment IDs are deduplicated; conflicting duplicates are rejected. Missing actuals have null values, not zero. Unplanned actuals and overpayments are flagged. Variances are only calculated when both forecast and actual exist. Payment balance is gross invoiced less recorded payment.

This is not a customs or tax calculator: no live rates, classification, duties, Incoterm allocation, credits, tax eligibility, bank fees, partial-payment FX gains, or credit notes are determined automatically. Use verified inputs and professional review. No real customer data included.

See [architecture](docs/architecture.md) and [test results](docs/test_results.md). Portfolio prototype by Ignacio Imperatrice. No open-source license is granted by this repository.
