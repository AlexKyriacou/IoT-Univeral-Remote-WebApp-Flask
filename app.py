from datetime import datetime
import sqlite3
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from threading import Lock
import serial
import json
import db.utils as DBUtils

app = Flask(__name__)
socketio = SocketIO(app, async_mode=None)
current_json_data = ""


def getProtocolString(rawProtocol: int):
    PROTOCOL_LIST = [
        'UNKNOWN',
        'PULSE_WIDTH',
        'PULSE_DISTANCE',
        'APPLE',
        'DENON',
        'JVC',
        'LG',
        'LG2',
        'NEC',
        'NEC2',
        'ONKYO',
        'PANASONIC',
        'KASEIKYO',
        'KASEIKYO_DENON',
        'KASEIKYO_SHARP',
        'KASEIKYO_JVC',
        'KASEIKYO_MITSUBISHI',
        'RC5',
        'RC6',
        'SAMSUNG',
        'SAMSUNGLG',
        'SAMSUNG48',
        'SHARP',
        'SONY',
        'BANG_OLUFSEN',
        'BOSEWAVE',
        'LEGO_PF',
        'MAGIQUEST',
        'WHYNTER',
        'FAST']
    return PROTOCOL_LIST[rawProtocol]


def retrieve_serial_data():
    global current_json_data
    while True:
        while ser.in_waiting:
            line = ser.readline().decode('utf-8').rstrip()
            try:
                jsonObject = json.loads(line)
                current_json_data = line
                if jsonObject['PROTOCOL'] is not None:
                    protocolString = getProtocolString(
                        jsonObject['PROTOCOL'])
                socketio.emit('json_data', {'protocol': protocolString, 'address': jsonObject['ADDRESS'],
                              'command': jsonObject['COMMAND']})
            except json.JSONDecodeError:
                pass
            time = datetime.now().strftime('%H:%M:%S')
            socketio.emit('serial_data', {'data': line, 'time': time})


@app.route("/")
def hello_world():
    return render_template('app.html')


@app.route("/create_button", methods=['GET', 'POST'])
def create_button():
    if request.method == 'POST':
        return render_template('app.html')
        
    return render_template('create-button.html')


@socketio.event
def connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(retrieve_serial_data)
    emit('connection_status', {'status': 'Connected 🟢'})
    conn = sqlite3.connect('stored-options.db')
    try:
        with conn:
            emit('update_options', {
                 'options': DBUtils.retrieve_all_ir_names(conn)})
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        pass
    if conn:
        conn.close()


# Receive the test request from client and send back a test response
@socketio.on('send_message')
def handle_message(msg):
    if msg['button'] is None or msg['button'] == "":
        return
    print('received message: ' + str(msg))
    conn = sqlite3.connect('stored-options.db')
    try:
        with conn:
            irJSONData = DBUtils.retrieve_ir_data_by_name(conn, msg['button'])
            irJSONDataOneLine = DBUtils.reconstruct_json_string_from_db_row(
                irJSONData)
            irJSONDataOneLine += '\n'
            ser.write(irJSONDataOneLine.encode('utf-8'))
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        pass
    if conn:
        conn.close()


@socketio.on('add_button')
def handle_add_button(msg):
    global current_json_data
    if current_json_data == "":
        return
    conn = sqlite3.connect('stored-options.db')
    try:
        with conn:
            print('received message: ' + str(msg))
            jsonData = json.loads(current_json_data)
            insertSuccessful = DBUtils.insert_ir_data(
                conn, jsonData, msg['buttonName'])
    except sqlite3.Error as e:
        print(f"Error retrieving data: {e}")
        pass
    if insertSuccessful:
        print('Data inserted successfully')
        # TODO: capture this on client
        emit('add_button_response', {'status': 'success'})
        emit('update_options', {
             'options': DBUtils.retrieve_all_ir_names(conn)})
    if conn:
        conn.close()


if __name__ == "__main__":
    thread = None
    thread_lock = Lock()
    ser = serial.Serial('COM3', 115200)
    ser.flush()
    conn = sqlite3.connect('stored-options.db')
    DBUtils.initialise_ir_data_tables(conn)
    socketio.run(app, host='0.0.0.0')
    if conn:
        conn.close()
