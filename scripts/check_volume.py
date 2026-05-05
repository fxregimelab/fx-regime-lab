import yfinance as yf
import pandas as pd

def check_volume(ticker):
    print(f"Checking volume for {ticker}...")
    try:
        data = yf.download(ticker, period="30d", progress=False)
        print(data.tail())
        if "Volume" in data.columns:
            non_zero = (data["Volume"] > 0).sum()
            print(f"Non-zero volume count: {non_zero}/{len(data)}")
        else:
            print("Volume column missing")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Check FX spot tickers
    check_volume("EURUSD=X")
    check_volume("USDJPY=X")
    check_volume("USDINR=X")
    # Check CME Futures tickers (common symbols used for volume proxies)
    check_volume("6E=F") # EUR/USD Futures
    check_volume("6J=F") # JPY/USD Futures
    check_volume("6I=F") # INR/USD Futures (if available)
