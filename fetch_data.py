#!/usr/bin/env python3
"""tickers.txt에 적은 종목의 일봉을 야후 파이낸스에서 받아 data/ 폴더에 CSV로 저장합니다.

내 컴퓨터에서 실행:  pip install yfinance pandas   →   python fetch_data.py
"""
import json
import pathlib
import sys
import time

import pandas as pd
import yfinance as yf

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "data"
COLS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


def read_tickers():
    tickers = []
    for line in (ROOT / "tickers.txt").read_text(encoding="utf-8").splitlines():
        t = line.split("#")[0].strip()
        if t and t not in tickers:
            tickers.append(t)
    return tickers


def fetch(ticker):
    for attempt in range(3):
        try:
            df = yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=False)
            if df is not None and len(df) > 20 and "Close" in df.columns:
                return df
            print(f"  {ticker}: 데이터가 비어 있습니다 (시도 {attempt + 1}/3)")
        except Exception as exc:  # 네트워크·차단 등
            print(f"  {ticker}: {exc} (시도 {attempt + 1}/3)")
        time.sleep(4 * (attempt + 1))
    return None


def to_csv_frame(df):
    df = df.copy()
    idx = pd.to_datetime(df.index)
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    df.index = idx.strftime("%Y-%m-%d")
    df.index.name = "Date"
    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]
    df = df[COLS].dropna(subset=["Close"])
    df = df[~df.index.duplicated(keep="last")]
    return df.round(4)


def main():
    OUT.mkdir(exist_ok=True)
    idx_path = OUT / "index.json"
    old = {}
    if idx_path.exists():
        try:
            old = {e["t"]: e for e in json.loads(idx_path.read_text(encoding="utf-8"))}
        except Exception:
            old = {}
    entries, ok = [], 0
    for t in read_tickers():
        print(f"{t} 받는 중...")
        df = fetch(t)
        if df is None:
            print(f"  {t}: 실패했습니다. 이전 파일이 있으면 그대로 둡니다.")
            if t in old:
                entries.append(old[t])
            continue
        out = to_csv_frame(df)
        fname = f"{t}.csv"
        out.to_csv(OUT / fname, encoding="utf-8")
        entries.append({"t": t, "file": fname, "first": out.index[0], "last": out.index[-1], "n": int(len(out))})
        ok += 1
        print(f"  {t}: {len(out)}행 ({out.index[0]} ~ {out.index[-1]})")
        time.sleep(1)
    idx_path.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
