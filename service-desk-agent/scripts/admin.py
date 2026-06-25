import os
from flask import Blueprint, request, jsonify
from utils import verify_key

admin_bp = Blueprint('admin', __name__)

# Shared mode state — module level dict
mode_state = {"value": os.getenv("MODE", "test")}

@admin_bp.route('/admin/mode', methods=['GET'])
def get_mode():
    """Returns current mode."""
    verify_key(request)
    return jsonify({"mode": mode_state["value"]})

@admin_bp.route('/admin/mode', methods=['POST'])
def set_mode():
    """Updates current mode."""
    verify_key(request)
    data = request.json
    new_mode = data.get("mode")
    
    if new_mode in ["on", "test", "off"]:
        mode_state["value"] = new_mode
        return jsonify({"mode": mode_state["value"], "status": "updated"})
    
    return jsonify({"error": "invalid_mode"}), 400

@admin_bp.route('/admin/health', methods=['GET'])
def health():
    """Health check endpoint."""
    verify_key(request)
    return jsonify({
        "status": "ok",
        "mode": mode_state["value"],
        "version": "1.0.0"
    })
