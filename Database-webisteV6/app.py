from flask import Flask, render_template, url_for
from matplotlib.figure import Figure
from datetime import datetime
import RPi.GPIO as GPIO
import sqlite3, io, base64, Adafruit_DHT, smbus, time


app = Flask (__name__)
GPIO.setmode(GPIO.BCM)
sensor = Adafruit_DHT.DHT11
DEVICE_ADDRESS = 0x49
DEVICE_CHANNEL = 0
dhtpin = 23
buzzerpin = 18
servo_pin = 12
bus = smbus.SMBus(1)
GPIO.setwarnings(False)
GPIO.setup(buzzerpin, GPIO.OUT)
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)

def read_adc():
    # Read the raw ADC value
    raw_value = bus.read_word_data(DEVICE_ADDRESS, DEVICE_CHANNEL)
    # Convert the raw value to a voltage (assuming VREF = 3.3V)
    real_raw_value = ((raw_value & 0xFF) << 8) + (raw_value >> 8) #Big endian conversion to little endian
    voltage = (real_raw_value / 4095.0) * 3.3
    return voltage

def read_co2():
    # Read the CO2 level from the MQ-135 sensor
    voltage = read_adc()
    co2 = 5000 * (voltage - 0.1) / 4.9
    return int(co2)

def buzz(noteFreq, duration):
    halveWaveTime = 1 / (noteFreq * 2 )
    waves = int(duration * noteFreq)
    for i in range(waves):
       GPIO.output(buzzerpin, True)
       time.sleep(halveWaveTime)
       GPIO.output(buzzerpin, False)
       time.sleep(halveWaveTime)

def play():
    t=0
    notes=[196,262,262,196,262]
    duration=[0.5,1,0.5,0.5,1]
    for n in notes:
        buzz(n, duration[t])
        time.sleep(duration[t] *0.1)
        t+=1

@app.route("/")
def get_data_and_graph():
    humidity, temperature = Adafruit_DHT.read_retry(sensor, dhtpin)
    co2_ppm = read_co2()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("tid: ", timestamp)
    # Get data from the database
    conn = sqlite3.connect('test.db')
    cur = conn.cursor()
    if humidity is not None and temperature is not None:
        cur.execute("INSERT INTO Mytable (CO2, Humidity, Temperature, timestamp) VALUES (?, ?, ?, ?)", (co2_ppm, humidity, temperature, timestamp))
    cur.execute('SELECT timestamp, Temperature, Humidity, CO2 FROM Mytable ORDER BY timestamp DESC LIMIT 5')
    data = cur.fetchall()
    conn.commit()
    conn.close()

    # Generate a line graph using Matplotlib
    x_values = [row[0] for row in data]
    x_values.reverse()
    if humidity is not None and temperature is not None:
        y_values_temp = [float(row[1]) for row in data]
        y_values_temp.reverse()
        y_values_hum = [float(row[2]) for row in data]
        y_values_hum.reverse()
    y_values_co2 = [float(row[3]) for row in data]
    y_values_co2.reverse()

    
    fig_temp = Figure()
    axis_temp = fig_temp.add_subplot(1, 1, 1)
    axis_temp.plot(x_values, y_values_temp, marker = "o")
    axis_temp.set_xlabel('Time and date')
    axis_temp.set_ylabel('Temperatur')
    axis_temp.set_title('Temperatur-niveau')
    axis_temp.set_xticklabels(x_values, rotation=10)
    

    fig_hum = Figure()
    axis_hum = fig_hum.add_subplot(1, 1, 1)
    axis_hum.plot(x_values, y_values_hum, marker = "o")
    axis_hum.set_xlabel('Time and date')
    axis_hum.set_ylabel('Fugtihed')
    axis_hum.set_title('Fugtiheds-niveau')
    axis_hum.set_xticklabels(x_values, rotation=10)

    fig_co2 = Figure()
    axis_co2 = fig_co2.add_subplot(1, 1, 1)
    axis_co2.plot(x_values, y_values_co2, marker = "o")
    axis_co2.set_xlabel('Time and date')
    axis_co2.set_ylabel('CO2')
    axis_co2.set_title('CO2-niveau')
    axis_co2.set_xticklabels(x_values, rotation=10)


    # Save the generated graphs to file buffers, and convert them to base64-encoded strings
    img_buffer_temp = io.BytesIO()
    fig_temp.savefig(img_buffer_temp, format='png')
    img_buffer_temp.seek(0)
    plot_data_temp = base64.b64encode(img_buffer_temp.getvalue()).decode('ascii')

    img_buffer_hum = io.BytesIO()
    fig_hum.savefig(img_buffer_hum, format='png')
    img_buffer_hum.seek(0)
    plot_data_hum = base64.b64encode(img_buffer_hum.getvalue()).decode('ascii')

    img_buffer_co2 = io.BytesIO()
    fig_co2.savefig(img_buffer_co2, format='png')
    img_buffer_co2.seek(0)
    plot_data_co2 = base64.b64encode(img_buffer_co2.getvalue()).decode('ascii')
    
    
    pwm.start(0)
    try:
        if co2_ppm >= 1000 or humidity >= 60 or humidity <= 20:
            play()
            pwm.ChangeDutyCycle(2.0)
            time.sleep(0.5)
        elif co2_ppm >= 900 or humidity >= 55 or humidity <= 22:
            play()
            pwm.ChangeDutyCycle(7.5)
            time.sleep(0.5)
        elif co2_ppm >= 800  or humidity >= 50 or humidity <= 24:
            pwm.ChangeDutyCycle(8.5)
            time.sleep(0.5)
        else:
            pwm.ChangeDutyCycle(12.0)
            time.sleep(0.5)
               
    except Exception as e:
        # Håndtering af alle andre fejl, der måtte opstå
        print("Der opstod en fejl:", e)
    time.sleep(1)
    
    pwm.ChangeDutyCycle(0)
    #pwm.stop()

    # Render the HTML template with the data and graphs
    return render_template('index.html', data=data, plot_data_temp=plot_data_temp, plot_data_hum=plot_data_hum, plot_data_co2=plot_data_co2)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8000)