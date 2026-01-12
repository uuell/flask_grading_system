from flask import Blueprint

ocr_bp = Blueprint('ocr', __name__)

@ocr_bp.route('/process')
def process():
    return "OCR Processing"