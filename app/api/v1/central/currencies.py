import json
import requests
from flask import Flask, jsonify, Blueprint

currency_bp = Blueprint('currency_bp', __name__)

# External API URL for currencies (Open Exchange Rates API)
API_URL = "https://openexchangerates.org/api/currencies.json"  # Example API that returns currency names and codes

@currency_bp.route('/api/save_currencies', methods=['GET'])
def save_currencies_to_json():
    try:
        # Step 1: Fetch data from the currency API
        response = requests.get(API_URL)
        
        # Check if the request was successful
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch currency data from API"}), 500
        
        data = response.json()

        # Step 2: Extract relevant permanent currency data (name, symbol, code)
        currencies = {
            code: {"name": name, "symbol": get_currency_symbol(code), "code": code}
            for code, name in data.items()
        }

        # Step 3: Define the path where the JSON file will be saved
        json_file_path = 'currencies.json'

        # Step 4: Save the fetched data into a JSON file
        with open(json_file_path, 'w') as json_file:
            json.dump(currencies, json_file, indent=4)

        # Step 5: Return success message
        return jsonify({
            "message": "Currencies saved successfully to JSON file",
            "currency_count": len(currencies)
        }), 200

    except Exception as e:
        
        return jsonify({"error": str(e)}), 500

def get_currency_symbol(code):
    # Static mapping of currency codes to symbols
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "AUD": "$",
        "CAD": "$",
        "CHF": "Fr",
        "CNY": "¥",
        "INR": "₹",
        "MXN": "$",
        "BRL": "R$",
        "CNY": "¥",
        "SEK": "kr",
        "NOK": "kr",
        "DKK": "kr",
        "SGD": "$",
        "HKD": "$",
        "NZD": "$",
        "ZAR": "R",
        "RUB": "₽",
        "TRY": "₺",
        "KRW": "₩",
        "AED": "د.إ",
        "SAR": "﷼",
        "PLN": "zł",
        "THB": "฿",
        "IDR": "Rp",
        "ILS": "₪",
        "MYR": "RM",
        "PHP": "₱",
        "HUF": "Ft",
        "CZK": "Kč",
        "CLP": "$",
        "COP": "$",
        "ARS": "$",
        "VND": "₫",
        "KES": "KSh",
        "TWD": "NT$",
        "RON": "lei",
        "BGN": "лв",
        "NGN": "₦",
        "PKR": "₨",
        "BDT": "৳",
        "EGP": "E£",
        "UAH": "₴",
    }
    return currency_symbols.get(code, "")  # Default to empty string if symbol not found

