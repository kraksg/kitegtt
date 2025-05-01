import configparser
import webbrowser
import threading
import time
import pandas as pd
from flask import Flask, request
from kiteconnect import KiteConnect
import os

# Load config
config = configparser.ConfigParser()
config.read('kiteconfig.ini')

kite_api_key = config['kite']['api_key']
kite_api_secret = config['kite']['api_secret']
sheet_url = config['google']['sheet_url']
redirect_uri = config['kite'].get('redirect_uri', 'http://127.0.0.1:5000')
chrome_path = config['browser'].get('chrome_path', None)

# New control configs
allow_new_stocks = config['controls'].getboolean('allow_new_stocks', fallback=True)
min_downside_diff = config['controls'].getfloat('min_downside_diff_percent', fallback=-3.12)
max_upside_diff = config['controls'].getfloat('max_upside_diff_percent', fallback=3.12)
max_holding_value = config['controls'].getfloat('max_holding_value', fallback=50000)

kite = KiteConnect(api_key=kite_api_key)
access_token_file = 'access_token.txt'

# Flask App
app = Flask(__name__)
request_token_global = None

@app.route('/')
def get_request_token():
    global request_token_global
    request_token_global = request.args.get('request_token')
    return "✅ Request token received! You can close this tab."

def start_flask():
    app.run(host='127.0.0.1', port=5000)

def save_access_token(token):
    with open(access_token_file, 'w') as f:
        f.write(token)

def load_access_token():
    if os.path.exists(access_token_file):
        with open(access_token_file, 'r') as f:
            return f.read().strip()
    return None

def generate_access_token():
    global request_token_global
    print("Launching login flow...")
    auth_url = kite.login_url()

    if chrome_path:
        webbrowser.get(f'"{chrome_path}" %s').open(auth_url)
    else:
        webbrowser.open(auth_url)

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    while request_token_global is None:
        time.sleep(1)

    data = kite.generate_session(request_token_global, api_secret=kite_api_secret)
    access_token = data["access_token"]
    save_access_token(access_token)
    kite.set_access_token(access_token)
    print("✅ Access token generated and saved.")
    os._exit(0)

def is_access_token_valid():
    try:
        kite.margins()
        return True
    except:
        return False

def open_google_sheet_for_refresh():
    print("Opening Google Sheet view link...")
    if chrome_path:
        webbrowser.get(f'"{chrome_path}" %s').open(sheet_url)
    else:
        webbrowser.open(sheet_url)
    time.sleep(12)

def fetch_gtts():
    print("Fetching all GTT orders...")
    try:
        return kite.get_gtts()
    except Exception as e:
        print(f"❌ Error fetching GTTs: {e}")
        return []

def delete_buy_gtts():
    gtts = fetch_gtts()
    for gtt in gtts:
        try:
            if gtt['condition']['trigger_values'][0] > gtt['condition']['last_price']:
                kite.delete_gtt(gtt['id'])
                print(f"🗑️ Deleted BUY GTT ID: {gtt['id']}")
        except Exception as e:
            print(f"❌ Error deleting GTT ID {gtt['id']}: {e}")

def read_google_sheet_data():
    print("Reading Google Sheet data...")
    try:
        # Handle both /edit#gid= and /edit?gid= formats
        if '/edit' in sheet_url:
            csv_url = (sheet_url
                       .replace('/edit#gid=', '/export?format=csv&gid=')
                       .replace('/edit?gid=', '/export?format=csv&gid='))
        else:
            csv_url = sheet_url

        print("Final CSV URL:", csv_url)  # For debugging if needed
        df = pd.read_csv(csv_url, header=0, on_bad_lines='warn')
        print("✅ Columns read from sheet:", df.columns.tolist())

        # Sanitize column names
        df.columns = df.columns.str.strip().str.lower()
        return df
    except Exception as e:
        print(f"❌ Error reading Google Sheet: {e}")
        return None


def fetch_holdings():
    try:
        return kite.holdings()
    except Exception as e:
        print(f"❌ Error fetching holdings: {e}")
        return []

def place_gtt(tradingsymbol, trigger_price, qty, cmp_price):
    tradingsymbol = tradingsymbol.replace('NSE:', '').strip()
    try:
        gtt_data = {
            "tradingsymbol": tradingsymbol,
            "exchange": "NSE",
            "trigger_type": "single",
            "trigger_values": [trigger_price],
            "last_price": cmp_price,
            "orders": [{
                "transaction_type": kite.TRANSACTION_TYPE_BUY,
                "quantity": int(qty),
                "price": trigger_price,
                "order_type": kite.ORDER_TYPE_LIMIT,
                "product": kite.PRODUCT_CNC
            }]
        }
        resp = kite.place_gtt(**gtt_data)
        print(f"✅ GTT placed for {tradingsymbol}. GTT ID: {resp['trigger_id']}")
    except Exception as e:
        print(f"❌ Error placing GTT for {tradingsymbol}: {e}")


def get_dynamic_min_price_diff_percent(tradingsymbol, holding, trigger_price):
    """Adjust min_price_diff_percent based on stock's momentum."""

    avg_price = holding['average_price']
    current_price = holding['last_price']

    # Calculate net change percentage
    net_change_percent = ((current_price - avg_price) / avg_price) * 100
    print(f"🧐 {tradingsymbol} - Net Change: {net_change_percent:.2f}%")

    if net_change_percent > 3.0:  # Stock is up by more than 3%
        # Higher threshold to follow the upward momentum
        adjusted_percent = min_price_diff_percent + 1.5  # Example: increase by 1.5%
        print(f"🔼 {tradingsymbol} - Stock is up, increasing min_price_diff_percent to {adjusted_percent:.2f}%")
        return adjusted_percent
    elif net_change_percent < -3.0:  # Stock is down by more than 3%
        # Lower threshold to be more cautious when averaging down
        adjusted_percent = max(min_price_diff_percent - 1.0, 1.0)  # Decrease by 1% but don't go below 1%
        print(f"🔽 {tradingsymbol} - Stock is down, decreasing min_price_diff_percent to {adjusted_percent:.2f}%")
        return adjusted_percent
    else:
        # No significant change, return the default min_price_diff_percent
        return min_price_diff_percent


def main():
    access_token = load_access_token()

    if access_token:
        kite.set_access_token(access_token)
        if not is_access_token_valid():
            generate_access_token()
    else:
        generate_access_token()

    open_google_sheet_for_refresh()
    delete_buy_gtts()

    df = read_google_sheet_data()
    required_cols = ['tradingsymbol', 'triggerprice', 'qty', 'cmp']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"❌ Missing columns: {missing}")
        return

    if df is None:
        print("❌ No data found.")
        return

    holdings = fetch_holdings()
    holding_symbols = {h['tradingsymbol']: h for h in holdings}

    skipped_rows = []

    for _, row in df.iterrows():
        tradingsymbol = row['tradingsymbol'].replace('NSE:', '').strip()
        trigger_price = float(row['triggerprice'])
        qty = int(row['qty'])
        cmp_price = float(row['cmp'])

        # Holding check
        if tradingsymbol not in holding_symbols:
            if not allow_new_stocks:
                reason = "No holding & new stocks not allowed"
                print(f"⛔ {tradingsymbol} skipped: {reason}")
                skipped_rows.append({
                    "tradingsymbol": tradingsymbol,
                    "trigger_price": trigger_price,
                    "cmp_price": cmp_price,
                    "qty": qty,
                    "reason": reason
                })
                continue
        else:
            holding = holding_symbols[tradingsymbol]
            avg_price = holding['average_price']
            holding_value = holding['quantity'] * holding['last_price']

            # Max holding value check
            if holding_value > max_holding_value:
                reason = f"Holding value {holding_value:.2f} > {max_holding_value}"
                print(f"⛔ {tradingsymbol} skipped: {reason}")
                skipped_rows.append({
                    "tradingsymbol": tradingsymbol,
                    "trigger_price": trigger_price,
                    "cmp_price": cmp_price,
                    "qty": qty,
                    "reason": reason
                })
                continue

            # Net change % = (CMP - Avg Buy Price) / Avg Buy Price * 100
            net_change_percent = ((cmp_price - avg_price) / avg_price) * 100

            # Apply downside and upside averaging logic
            if net_change_percent < min_downside_diff:
                print(f"🔽 {tradingsymbol} - Down {net_change_percent:.2f}%, qualifies for averaging.")
            elif net_change_percent > max_upside_diff:
                print(f"🔼 {tradingsymbol} - Up {net_change_percent:.2f}%, qualifies for momentum averaging.")
            else:
                reason = f"Net change {net_change_percent:.2f}% not in range [{min_downside_diff}%, {max_upside_diff}%]"
                print(f"⛔ {tradingsymbol} skipped: {reason}")
                skipped_rows.append({
                    "tradingsymbol": tradingsymbol,
                    "trigger_price": trigger_price,
                    "cmp_price": cmp_price,
                    "qty": qty,
                    "reason": reason
                })
                continue

        print(f"📈 Placing GTT: {tradingsymbol}, Trigger: {trigger_price}, Qty: {qty}")
        place_gtt(tradingsymbol, trigger_price, qty, cmp_price)

    if skipped_rows:
        pd.DataFrame(skipped_rows).to_csv("skipped_gtt.csv", index=False)
        print(f"\n📋 Skipped stocks logged to skipped_gtt.csv")

    print("\n🎯 All GTT orders placed successfully!")

if __name__ == "__main__":
    main()
