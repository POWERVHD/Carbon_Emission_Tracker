import serial
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request
import threading
import time
import os
import atexit
import requests

app = Flask(__name__)

# Arduino serial port configuration
SERIAL_PORT = 'COM5'  # Replace with your Arduino's port
BAUD_RATE = 9600

# CSV file to store sensor data
CSV_FILE = 'sensor_data.csv'

# Emission factors (in kg CO2 per unit of activity)
EMISSION_FACTORS = {
    "electricity": 0.92,  # per kWh (global average)
    "car": 0.21,         # per km for an average gasoline car
    "bus": 0.05,         # per km
    "train": 0.03,       # per km
    "flight": 0.254,     # per km per passenger (short haul)
    "deforestation": 50  # per tree cut down
}

HEADERS = ['Timestamp', 'MQ135', 'Vibration', 'Temperature', 'Humidity', 'Latitude', 'Longitude', 'AngleX', 'AngleY']

trees_cut = 0

def create_new_csv():
    pd.DataFrame(columns=HEADERS).to_csv(CSV_FILE, index=False)
    print("New CSV file created.")


def delete_csv_file():
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
        print("CSV file deleted.")


def log_sensor_data():
    """Continuously logging data from Arduino to CSV file."""
    global trees_cut
    try:
        # Initialize serial connection
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

        print("Listening for data from Arduino...")

        while True:
            try:
                # Data from Arduino
                line = arduino.readline().decode('utf-8').strip()
                if line:
                    #timestamp 
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data = [timestamp] + line.split(',')

                    try:
                        angle_x = float(data[7])  # AngleX = index 7
                        if angle_x >= 110:
                            trees_cut = 1    #For Multiple tree +=1 
                            print(f"Tree cut detected! Total trees cut: {trees_cut}")
                    except (IndexError, ValueError):
                        print("Error reading AngleX value.")

                    # Adding data to CSV
                    df = pd.DataFrame([data], columns=HEADERS)
                    df.to_csv(CSV_FILE, mode='a', index=False, header=False)
                    print(f"Data logged: {data}")
            except Exception as e:
                print(f"Error reading data: {e}")
                continue
    except Exception as e:
        print(f"Error initializing serial connection: {e}")


def send_suggestions_to_callmebot(user, message):
    """
    Send suggestions to CallMeBot's API.

    Args:
        user (str): @username.
        message (str): The message to send.
    """
    try:
        # CallMeBot API URL
        url = f"https://api.callmebot.com/text.php?user=@Kshitij1980&text={message}&html=yes&links=yes"

        # Make the GET request
        response = requests.get(url)

        # Checking response status
        if response.status_code == 200:
            print("Suggestions sent successfully via CallMeBot.")
        else:
            print(f"Failed to send suggestions. Status code: {response.status_code}, Response: {response.text}")
    except Exception as e:
        print(f"Error sending suggestions to CallMeBot: {e}")


@app.route('/')
def home():
    global trees_cut
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    """Process user inputs, calculate carbon emissions, and provide suggestions."""
    global trees_cut

    try:
        # Reading latest data from the CSV file
        try:
            sensor_data = pd.read_csv(CSV_FILE).tail(1).iloc[0]
            mq135_value = float(sensor_data['MQ135'])
        except (FileNotFoundError, IndexError):
            mq135_value = 0  # Default if no data available

        # Get inputs from the form with default fallback to 0
        electricity = float(request.form.get('electricity', 0))
        car = float(request.form.get('car', 0))
        bus = float(request.form.get('bus', 0))
        train = float(request.form.get('train', 0))
        flight = float(request.form.get('flight', 0))
        deforestation = float(request.form.get('deforestation', 0))

        total_emissions = (
            electricity * EMISSION_FACTORS["electricity"] +
            car * EMISSION_FACTORS["car"] * mq135_value +
            bus * EMISSION_FACTORS["bus"] +
            train * EMISSION_FACTORS["train"] +
            flight * EMISSION_FACTORS["flight"] * mq135_value +
            deforestation * EMISSION_FACTORS["deforestation"] +
            mq135_value * 0.5 
        )

        # suggestions based on user inputs
        suggestions = []
        if car > 50:
            suggestions.append("Consider using public transport or carpooling to reduce emissions.")
        if flight > 100:
            suggestions.append("Reducing frequent short-haul flights can lower your footprint.")
        if electricity > 500:
            suggestions.append("Switching to renewable energy sources could help reduce emissions.")
        if deforestation > 0:
            suggestions.append("Planting new trees can help offset emissions from deforestation.")
        if bus == 0 and train == 0:
            suggestions.append("Incorporating more public transport can significantly lower emissions.")

        # Combine suggestions into a single message
        message = f"Total Emissions: {round(total_emissions, 2)} kg CO2\nSuggestions:\n" + "\n".join(suggestions)

        send_suggestions_to_callmebot("@Kshitij1980", message)

        return render_template(
            'result.html',
            total_emissions=round(total_emissions, 2),
            suggestions=suggestions,
            trees_cut=trees_cut  
        )

    except ValueError:

        return "Invalid input. Please ensure all values are numeric."


if __name__ == '__main__':
    # Start the sensor data logging in a separate thread
    create_new_csv()  # Ensure a new CSV file is created when the app starts
    atexit.register(delete_csv_file)  # Delete the CSV file when the app stops

    sensor_thread = threading.Thread(target=log_sensor_data, daemon=True)
    sensor_thread.start()

    app.run(debug=True)
