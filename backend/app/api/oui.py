"""OUI API endpoints - MAC manufacturer database."""
from flask import request, jsonify, current_app
from . import api_bp


@api_bp.route('/oui/search', methods=['POST'])
def search_oui():
    """Search OUI database."""
    data = request.json
    query = data.get('query', '').strip() if data else ''

    if not query:
        return jsonify({'status': 'error', 'message': 'Query required'}), 400

    oui_service = current_app.config['oui_service']
    results = oui_service.search(query)

    return jsonify({
        'status': 'success',
        'results': results,
        'count': len(results),
    })


@api_bp.route('/oui/all', methods=['GET'])
def get_all_oui():
    """Get all OUI entries."""
    oui_service = current_app.config['oui_service']
    results = oui_service.get_all()

    return jsonify({
        'status': 'success',
        'results': results,
        'count': len(results),
        'total': oui_service.count,
    })


@api_bp.route('/oui/refresh', methods=['POST'])
def refresh_oui():
    """Refresh OUI database from IEEE website."""
    oui_service = current_app.config['oui_service']
    result = oui_service.refresh()

    if result.get('success'):
        return jsonify({
            'status': 'success',
            'message': 'Database refreshed successfully',
            'count': result.get('count'),
        })
    else:
        status_code = 418 if '418' in str(result.get('error', '')) else 500
        return jsonify({
            'status': 'error',
            'message': result.get('error'),
        }), status_code
