# GTT Order Automation Bot for Zerodha (Kite Connect)

This Python-based automation tool places GTT (Good Till Triggered) BUY orders for stocks based on data from a shared Google Sheet. It supports features like avoiding new stocks, upward averaging logic, and holding value checks.

## 🔧 Features
- Reads a Google Sheet for GTT inputs (stock symbol, trigger price, etc.)
- Deletes old BUY GTTs before placing new ones(!!Deletes all existing buy GTT's, backup old gtt's or include them in the google sheet to avoid loss od data!!)
- Avoids new stocks if configured
- Applies configurable logic for upward averaging and holding value limits
- Generates and stores access token from Zerodha
- Optionally logs skipped stocks with reasons

---

## ✅ Requirements
- Python 3.8+
- Zerodha Kite Connect API key and secret
- Google Sheet in proper format
- `kiteconfig.ini` file for configuration

---

## 🛠 Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/gtt-bot.git
cd gtt-bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `kiteconfig.ini`
```ini
[kite]
api_key = your_api_key
api_secret = your_api_secret
redirect_uri = http://127.0.0.1:5000

[google]
sheet_url = https://docs.google.com/spreadsheets/d/your_sheet_id/edit#gid=0

[browser]
chrome_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"  ; optional

[controls]
; true or false
allow_new_stocks = false
; minimum % gap between holding avg and new trigger
min_downside_diff_percent = -3.12
max_upside_diff_percent = 3.12
; maximum INR value allowed per stock
max_holding_value = 50000
```

> 💡 You can get your API key and secret from https://kite.trade -> My Apps.
> Use http://127.0.0.1:5000 as your redirect URI.

### 4. First Time Run (Generates access token)
```bash
python kitegtt.py
```
It will:
- Open Zerodha login page in your browser
- Wait for the token
- Save the access token in `access_token.txt`

---

## 🕒 Scheduling (Windows)
You can schedule this script using **Windows Task Scheduler** to run every NSE working day at 8:00 AM.

### Steps:
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 8:00 AM
4. Action: Start a program
5. Program/script: `python`
6. Add arguments: `kitegtt.py`
7. Start in: `C:\path\to\gtt-bot`

---

## 📊 Google Sheet Format
Your sheet should have these columns:
- `tradingsymbol`
- `triggerprice`
- `qty`
- `cmp` (Current Market Price)

---

## 🚫 Skipped Stocks
If any stocks are skipped due to config logic, they will be logged in a file named `skipped_gtt.csv` with reasons.

---

## 📤 Extending for Others
To run this for another user:
1. Clone the repo
2. Create a new `kiteconfig.ini` with that user's API key, secret, and sheet
3. Run `python kitegtt.py` once to authorize
4. Schedule as per above

---

## 📬 Contact
Feel free to reach out via GitHub issues for enhancements or questions.
The code is free to use and me made every effort to document and people utilize it. Technical support can be extended for 210 INR, payable after successful run. This is supported by college interns and the amount goes to them.

---

Happy Trading! 🚀

