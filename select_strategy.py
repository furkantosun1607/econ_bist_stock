"""Reproduce the frozen, small development-only strategy comparison.

All candidates share their rules across the six stocks. Development ends on
2025-12-31; this script never evaluates 2026 prices. Rank candidates that have
at least three completed trades per stock by worst-stock return, median return,
then worst drawdown. This conservative proxy is not proof of challenge success
or a global optimum. The candidate family was designed using development data.
"""
import argparse
import hashlib
from pathlib import Path
import json
import numpy as np
import pandas as pd
from backtester import Backtester
from strategies.adaptive_regime import AdaptiveRegimeStrategy

DEVELOPMENT_END_EXCLUSIVE = "2026-01-01"
STOCK_NAMES = ("AKBNK", "ASELS", "EREGL", "FROTO", "TCELL", "TUPRS")

def inputs(df):
    c = df.Close
    for n in (5,10,20,40,50,60):
        df[f'e{n}'] = c.ewm(span=n,adjust=False,min_periods=min(n,20)).mean()
    tr = pd.concat([df.High-df.Low,(df.High-c.shift()).abs(),(df.Low-c.shift()).abs()],axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    diff=c.diff(); up=diff.clip(lower=0).ewm(alpha=1/3,adjust=False,min_periods=3).mean(); down=(-diff.clip(upper=0)).ewm(alpha=1/3,adjust=False,min_periods=3).mean()
    df['rsi'] = (100*up/(up+down)).fillna(50)
    df['er'] = (c-c.shift(20))/c.diff().abs().rolling(20).sum()
    df['roc20'] = c.pct_change(20)
    for n in (10,20):
        df[f'hi{n}']=df.High.rolling(n).max().shift()
        df[f'lo{n}']=df.Low.rolling(n).min().shift()
    return df

def signals(df, kind, fast=10, slow=40, trail=4, threshold=20, warmup=None):
    out = df.copy(); sig=np.zeros(len(df),dtype=int)
    held=False; pending=0; entry=peak=0; age=0
    for i,row in enumerate(df.itertuples()):
        if pending == 1:
            held=True; entry=peak=row.Open; age=0
        elif pending == -1:
            held=False
        pending=0
        if held:
            peak=max(peak,row.Close); age+=1
        if kind != 'hold' and i < (warmup or max(20,slow))-1: continue
        f=getattr(row,f'e{fast}'); s=getattr(row,f'e{slow}')
        trend = f>s and row.Close>s
        if kind=='hold': buy=True; sell=False
        elif kind=='ema': buy=trend; sell=f<s
        elif kind=='donchian': buy=row.Close>row.hi20; sell=row.Close<row.lo10
        elif kind=='hybrid':
            buy=trend or row.rsi<threshold
            sell=(not trend) and (row.rsi>70 or row.Close>=row.e10)
        elif kind=='hybrid_rebound':
            buy=trend or (df.rsi.iloc[i-1]<threshold and row.Close>df.Close.iloc[i-1])
            sell=(not trend) and (row.rsi>70 or row.Close>=row.e10)
        elif kind=='pullback':
            buy=(trend and row.rsi<50) or row.rsi<threshold
            sell=(not trend) and (row.rsi>70 or row.Close>=row.e10)
        elif kind in ('strong_er','strong_roc','reversion'):
            trend = trend and ((row.er>0.35) if kind=='strong_er' else (row.roc20>0.1) if kind=='strong_roc' else False)
            buy=trend or row.rsi<threshold
            sell=(not trend) and (row.rsi>70 or row.Close>=row.e10)
        else: raise ValueError(kind)
        stop=held and trail and row.Close < peak-trail*row.atr
        if held and (sell or stop): sig[i]=-1; pending=-1
        elif not held and buy: sig[i]=1; pending=1
    out['Signal']=sig
    return out

def candidate_specs():
    candidates=[dict(kind='hold',trail=0),dict(kind='ema',fast=10,slow=40,trail=4),dict(kind='ema',fast=20,slow=60,trail=4),dict(kind='donchian',trail=4)]
    for kind in ('hybrid','hybrid_rebound','pullback'):
        for fast,slow in ((10,40),(20,60)):
            for trail in (3,5):
                candidates.append(dict(kind=kind,fast=fast,slow=slow,trail=trail,threshold=20))
    for kind in ('pullback','strong_er','strong_roc','reversion'):
        for trail in (3,5):
            candidates.append(dict(kind=kind,fast=20,slow=60,trail=trail,threshold=20,warmup=20))
    return candidates


def evaluate_candidates(data_dir=Path("data")):
    data = {}
    fingerprints = {}
    for stock in STOCK_NAMES:
        raw = pd.read_csv(Path(data_dir) / f"{stock}_ohlcv.csv", index_col=0, parse_dates=True)
        development = raw.loc[raw.index < DEVELOPMENT_END_EXCLUSIVE].copy()
        if development.empty or not development.index.is_monotonic_increasing or not development.index.is_unique:
            raise ValueError(f"{stock}: development data must be nonempty, ordered, unique")
        fingerprints[stock] = hashlib.sha256(development.to_csv().encode("utf-8")).hexdigest()
        data[stock] = inputs(development)
    rows=[]
    for params in candidate_specs():
        row={'params':params}; rets=[]; dds=[]; counts=[]
        for ticker,df in data.items():
            result=Backtester().run(signals(df,**params),ticker)
            ret=result.final_capital/100000-1
            dd=float((result.equity_curve/result.equity_curve.cummax()-1).min())
            row[ticker]={'return':round(ret,4),'dd':round(dd,4),'trades':len(result.trades)}
            rets.append(ret); dds.append(dd); counts.append(len(result.trades))
        row.update(worst=round(min(rets),4),median=round(float(np.median(rets)),4),mean=round(float(np.mean(rets)),4),worst_dd=round(min(dds),4),min_trades=min(counts),eligible=min(counts)>=3)
        rows.append(row)
    rows.sort(key=lambda r:(r['eligible'],r['worst'],r['median'],r['worst_dd']),reverse=True)
    return rows, data, fingerprints


def write_artifacts(data_dir=Path("data"), output_dir=Path("results/validation")):
    rows, data, fingerprints = evaluate_candidates(data_dir)
    selected = rows[0]
    frozen = dict(kind="pullback", fast=20, slow=60, trail=5, threshold=20)
    if selected["params"] != frozen:
        raise ValueError("This data selects a different candidate; refusing to overwrite the frozen selection")

    # Confirm that persistent product signals preserve the research trade fills.
    strategy = AdaptiveRegimeStrategy()
    for stock, development in data.items():
        reference = Backtester().run(signals(development, **frozen), stock)
        product = Backtester().run(strategy.run(development[["Open", "High", "Low", "Close", "Volume"]]), stock)
        if not np.isclose(reference.final_capital, product.final_capital, atol=1e-7, rtol=0):
            raise AssertionError(f"{stock}: research/product execution mismatch")
        if [t.to_dict() for t in reference.trades] != [t.to_dict() for t in product.trades]:
            raise AssertionError(f"{stock}: research/product trade mismatch")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    flattened = []
    for rank, row in enumerate(rows, 1):
        record = {"rank": rank, "parameters": json.dumps(row["params"], sort_keys=True),
                  **{k: row[k] for k in ("eligible", "worst", "median", "mean", "worst_dd", "min_trades")}}
        for stock in STOCK_NAMES:
            for metric, value in row[stock].items():
                record[f"{stock}_{metric}"] = value
        flattened.append(record)
    pd.DataFrame(flattened).to_csv(output_dir / "development_candidates.csv", index=False)
    selection = {
        "strategy": strategy.get_name(),
        "class": "strategies.adaptive_regime.AdaptiveRegimeStrategy",
        "parameters": strategy.get_params(),
        "research_parameters": selected["params"],
        "development_start": str(next(iter(data.values())).index[0].date()),
        "development_end": str(next(iter(data.values())).index[-1].date()),
        "holdout_start": DEVELOPMENT_END_EXCLUSIVE,
        "candidate_count": len(rows),
        "development_bars": {stock: len(frame) for stock, frame in data.items()},
        "development_sha256": fingerprints,
        "selection_rule": "At least 3 completed trades per stock; maximize worst stock return, then median return, then worst drawdown (four decimal reporting precision)",
        "scope": "Development-selected experimental model; not global optimum or a guarantee of any benchmark",
        "execution": "next_open; full capital integer lots; zero commission/slippage; close-based ATR risk; no external intraday stops",
        "holdout_used_for_selection": False,
        "development_metrics": {k: v for k, v in selected.items() if k != "params"},
    }
    (output_dir / "strategy_selection.json").write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    return selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/validation"))
    args = parser.parse_args()
    selected = write_artifacts(args.data_dir, args.output_dir)
    print(json.dumps(selected, indent=2))

if __name__=='__main__': main()
