import json
import requests
from flask import Flask, jsonify, Blueprint, request
from app.models.central.central import Currency
from flask import current_app


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


@currency_bp.route('/api/currencies', methods=['POST'])
def send_currencies_from_file_to_db():
    try:
        with open('currencies.json', 'r') as json_file:
            currencies = json.load(json_file)

        if not currencies:
            return jsonify({"status": "error", "message": "No currencies found in JSON file"}), 400



        try:
            for code, info in currencies.items():
                if Currency.get_currency_by_code(code):
                    current_app.logger.info(f"Currency already exists: {info['name']} ({code})")
                    return jsonify({"status": "error", "message": f"Currency already exists: {info['name']} ({code})"}), 400
                else:
                    created_currency = Currency.create_currency(
                        name=info['name'],
                        symbol=info['symbol'],
                        code=code
                )
                if not created_currency:
                    return jsonify({"status": "error", "message": f"Failed to add currency: {info['name']} ({code})"}), 500
                
            current_app.logger.info(f"Currency to be added: {info['name']} ({code})")

            return jsonify({
                "status": "success",
                "message": "Currencies imported successfully"
            }), 201
        except Exception as e:
            current_app.logger.error(f"Error importing currencies: {str(e)}")
            return jsonify({"status": "error", "message": "An error occurred while importing currencies"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@currency_bp.route('/api/currencies', methods=['GET'])
def get_currencies():
    try:
        currencies = Currency.get_all_currencies()
        if not currencies:
            return jsonify({"status": "success", "data": [], "message": "No currencies found"}), 200
        return jsonify({"status": "success", "data": [currency.to_dict() for currency in currencies]}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching currencies: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while fetching currencies"}), 500
    
@currency_bp.route('/api/currencies/<uuid:currency_id>', methods=['GET'])
def get_currency(currency_id):
    try:
        currency = Currency.get_currency_by_id(currency_id)
        if not currency:
            return jsonify({"status": "error", "message": "Currency not found"}), 404
        return jsonify({"status": "success", "data": currency.to_dict(), "message": "Currency fetched successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching currency: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while fetching the currency"}), 500
    

@currency_bp.route('/api/currencies/<uuid:currency_id>', methods=['DELETE'])
def delete_currency(currency_id):
    try:
        currency = Currency.get_currency_by_id(currency_id)
        if not currency:
            return jsonify({"status": "error", "message": "Currency not found"}), 404
        
        Currency.delete_currency(currency_id)
        return jsonify({"status": "success", "message": "Currency deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Error deleting currency: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while deleting the currency"}), 500
    
@currency_bp.route('/api/currency/update/<uuid:currency_id>', methods=['PUT'])
def update_currency(currency_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        currency = Currency.get_currency_by_id(currency_id)
        if not currency:
            return jsonify({"status": "error", "message": "Currency not found"}), 404
        
        updated_currency = Currency.update_currency(
            currency_id,
            name=data.get('name', currency.name),
            symbol=data.get('symbol', currency.symbol),
            code=data.get('code', currency.code)
        )
        
        if not updated_currency:
            return jsonify({"status": "error", "message": "Failed to update currency"}), 500
        
        return jsonify({"status": "success", "data": updated_currency.to_dict(), "message": "Currency updated successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Error updating currency: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while updating the currency"}), 500
    
@currency_bp.route('/api/currency/create', methods=['POST'])
def create_currency():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'code' not in data:
            return jsonify({"status": "error", "message": "Name and code are required"}), 400
        
        if Currency.get_currency_by_code(data['code']):
            return jsonify({"status": "error", "message": "Currency with this code already exists"}), 400
        
        new_currency = Currency.create_currency(
            name=data['name'],
            symbol=data.get('symbol', ''),
            code=data['code']
        )
        
        if not new_currency:
            return jsonify({"status": "error", "message": "Failed to create currency"}), 500
        
        return jsonify({"status": "success", "data": new_currency.to_dict(), "message": "Currency created successfully"}), 201
    except Exception as e:
        current_app.logger.error(f"Error creating currency: {str(e)}")
        return jsonify({"status": "error", "message": "An error occurred while creating the currency"}), 500