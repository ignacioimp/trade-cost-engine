"""Offline cost reconciliation. Input amounts are explicit; no tax or FX estimates."""
import argparse, json
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ZERO = Decimal('0')

def dec(value):
    if isinstance(value, bool): raise ValueError('Boolean is not a number')
    try: n = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError): raise ValueError(f'Invalid decimal: {value!r}') from None
    if not n.is_finite() or n < ZERO: raise ValueError('Amounts must be finite and nonnegative')
    return n

def money(n): return str(n.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

def required(row, key):
    v = row.get(key)
    if not isinstance(v, str) or not v.strip(): raise ValueError(f'Missing {key}')
    return v.strip()

def reconcile(data):
    base = required(data, 'base_currency')
    if not isinstance(data.get('fx_to_base'), dict): raise ValueError('fx_to_base is required')
    fx = {k: dec(v) for k,v in data['fx_to_base'].items()}
    if base in fx and fx[base] != 1: raise ValueError('Base FX must equal 1')
    fx[base] = Decimal(1)
    if any(v <= ZERO for v in fx.values()): raise ValueError('FX rates must be positive')
    qty = dec(data['quantity'])
    if qty <= ZERO: raise ValueError('Quantity must be positive')
    def amount(row, field='amount'):
        currency=required(row,'currency')
        if currency not in fx: raise ValueError(f'Missing FX for {currency}')
        return dec(row[field])*fx[currency]
    def pair(row):
        gross=amount(row); rec=amount(row,'recoverable') if 'recoverable' in row else ZERO
        if rec>gross: raise ValueError('Recoverable amount exceeds gross')
        return gross,rec
    planned={}; actual={}; invoices={}; payments={}; duplicates=[]; flags=[]
    for row in data.get('forecast',[]):
        key=required(row,'cost_id')
        if key in planned: raise ValueError(f'Duplicate forecast cost_id: {key}')
        planned[key]=pair(row)
    for row in data.get('actual',[]):
        key=required(row,'cost_id'); identity=tuple(required(row,k) for k in ('vendor','invoice','line'))
        signature=(key,required(row,'currency'),dec(row['amount']),dec(row.get('recoverable',0)))
        if identity in invoices:
            if invoices[identity][0]!=signature: raise ValueError(f'Conflicting invoice line: {identity}')
            duplicates.append({'kind':'invoice_line','id':list(identity)}); continue
        gross,rec=pair(row); invoices[identity]=(signature,gross)
        g,r=actual.get(key,(ZERO,ZERO)); actual[key]=(g+gross,r+rec)
    paid=defaultdict(lambda:ZERO)
    for row in data.get('payments',[]):
        pid=required(row,'payment_id'); identity=tuple(required(row,k) for k in ('vendor','invoice','line'))
        signature=(identity,required(row,'currency'),dec(row['amount']))
        if pid in payments:
            if payments[pid]!=signature: raise ValueError(f'Conflicting payment ID: {pid}')
            duplicates.append({'kind':'payment','id':pid}); continue
        if identity not in invoices: raise ValueError(f'Payment references unknown invoice line: {identity}')
        payments[pid]=signature; paid[identity]+=amount(row)
    paid_by_cost=defaultdict(lambda:ZERO)
    for identity,(signature,gross) in invoices.items():
        p=paid[identity]; paid_by_cost[signature[0]]+=p
        if p>gross: flags.append({'kind':'overpayment','invoice_line':list(identity)})
    rows=[]
    for key in sorted(planned.keys()|actual.keys()):
        p=planned.get(key); a=actual.get(key); cash=paid_by_cost[key]
        if p is None: flags.append({'kind':'unplanned_actual','cost_id':key})
        if a is None: flags.append({'kind':'not_invoiced','cost_id':key})
        rows.append({'cost_id':key,'forecast_gross':money(p[0]) if p else None,'forecast_economic':money(p[0]-p[1]) if p else None,'actual_gross':money(a[0]) if a else None,'actual_economic':money(a[0]-a[1]) if a else None,'gross_variance':money(a[0]-p[0]) if a and p else None,'paid':money(cash) if a else None,'unpaid_balance':money(a[0]-cash) if a else None})
    def totals(values):
        g=sum((v[0] for v in values.values()),ZERO); r=sum((v[1] for v in values.values()),ZERO)
        return {'gross':money(g),'recoverable':money(r),'economic':money(g-r),'economic_per_unit':money((g-r)/qty)}
    return {'base_currency':base,'quantity':str(qty),'forecast_totals':totals(planned),'recorded_actual_totals':totals(actual),'recorded_paid':money(sum(paid.values(),ZERO)),'rows':rows,'duplicates_skipped':duplicates,'flags':flags,'actual_complete':False if any(k not in actual for k in planned) else None,'note':'Recorded actuals are not a final landed cost; completeness and recoverability require human verification.'}

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('input',type=Path); args=p.parse_args()
    try: print(json.dumps(reconcile(json.loads(args.input.read_text(encoding='utf-8'))),indent=2))
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as e: p.exit(2,f'Invalid input: {e}\n')
if __name__=='__main__': main()
