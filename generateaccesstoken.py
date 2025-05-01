from flask import Flask, request
from kiteconnect import KiteConnect
import configparser
import webbrowser
import threading

# --- Setup Configuration ---
config = configparser.ConfigParser()
config.read('kiteconfig.ini')

api_key = config['API']['api_key']
api_secret = config['API']['api_secret']

kite = KiteConnect(api_key=api_key)

app = Flask(__name__)

# --- Home Route to catch redirected URL ---
@app.route('/')
def catch_request_token():
    request_token = request.args.get('request_token')
    status = request.args.get('status')

    if status != "success" or request_token is None:
        return "Login Failed or Request Token Missing."

    try:
        print(f"Received Request Token: {request_token}")
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data['access_token']
        print(f"Access token generated successfully: {access_token}")

        # Update kiteconfig.ini
        config['API']['access_token'] = access_token
        with open('kiteconfig.ini', 'w') as configfile:
            config.write(configfile)

        print("Access token saved to kiteconfig.ini ✅")
        return "Access Token Generated and Saved Successfully! You can close this tab."

    except Exception as e:
        print(f"Error generating access token: {e}")
        return f"Error: {e}"

# --- Start Local Server and Open Kite Login ---
def start_server():
    app.run(port=5000)

def access_token_flow():
    threading.Thread(target=start_server).start()
    login_url = kite.login_url()
    print(f"Opening Kite login URL: {login_url}")
    webbrowser.open(login_url)

if __name__ == "__main__":
    access_token_flow()
