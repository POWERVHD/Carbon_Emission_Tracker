import serial
import pandas as pd
from datetime import datetime

# Arduino serial port configuration
SERIAL_PORT = 'COM5'  # Replace with your Arduino's port (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)
BAUD_RATE = 9600

# CSV file to store data
CSV_FILE = 'sensor_data.csv'

# Initialize serial connection
arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Create CSV file with headers if it doesn't exist
headers = ['Timestamp', 'MQ135', 'Vibration', 'Temperature', 'Humidity', 'Latitude', 'Longitude', 'AngleX', 'AngleY']
try:
    pd.read_csv(CSV_FILE)  # Check if file exists
except FileNotFoundError:
    pd.DataFrame(columns=headers).to_csv(CSV_FILE, index=False)

print("Listening for data from Arduino...")

while True:
    try:
        # Read data from Arduino
        line = arduino.readline().decode('utf-8').strip()
        if line:
            # Append timestamp to the data
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data = [timestamp] + line.split(',')

            # Append data to CSV
            df = pd.DataFrame([data], columns=headers)
            df.to_csv(CSV_FILE, mode='a', index=False, header=False)
            print(f"Data logged: {data}")
    except KeyboardInterrupt:
        print("Stopping data collection.")
        break
    except Exception as e:
        print(f"Error: {e}")
        continue
