from flask import Blueprint, render_template, request, jsonify
import os
import database as db

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/ai_assistant')
def ai_assistant_page():
    return render_template('ai_assistant.html')

@ai_bp.route('/ai_chat', methods=['POST'])
def AI_Chat():
    try:
        # Move import here to avoid crash if package missing
        import groq
        data = request.get_json()
        user_query = data.get('query', '')
        if not user_query:
            return jsonify({"response": "I didn't hear anything. How can I help you today?"})

        # Fetch context
        inventory = db.get_all_items()
        customers = db.get_all_customers()
        expenses = db.get_all_expenses()

        # Simple mock response if Groq fails or key missing
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            return jsonify({"response": "AI Assistant is currently in offline mode (GROQ_API_KEY missing). Based on your inventory, you have " + str(len(inventory)) + " products."})

        # Real Groq logic would go here
        return jsonify({"response": f"I'm analyzing your {len(inventory)} products. You have {len(customers)} customers in your credit book. How can I assist further?"})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})

@ai_bp.route('/api/scan_invoice', methods=['POST'])
def scan_invoice_api():
    return jsonify({"success": True, "message": "OCR scanning is a premium feature. Please upgrade your plan.", "items": []})

@ai_bp.route('/api/generate_promo', methods=['POST'])
def generate_promo_api():
    return jsonify({"success": True, "promo": "Special Offer! Get 10% off on all items today at our store! 🏪✨"})
