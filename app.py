from flask import Flask, render_template, request, Markup, json, redirect, url_for, session
from wtforms import SubmitField
import datetime
import csv
from io import TextIOWrapper
import itertools

import pandas as pd
import sqlalchemy as sql
from src.form import *

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secretkey'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

connect_string = 'mysql://root:kuroko32!@localhost:3306/libsat'
sql_engine = sql.create_engine(connect_string)

startProgram = False

@app.route('/', methods=['GET','POST'])
def index():
    return render_template('home.html')

@app.route('/remote', methods=['GET','POST'])
def remote():
    # global variable initialization
    global startProgram
    # Form initialzation
    form = runForm()

    # Run Checkbox Logic
    checkbox = request.args.get('start_program')
    if checkbox is None:
        startProgram = False
    else:
        startProgram = True

    return render_template('remote.html', form=form, value=startProgram)

@app.route('/results', methods=['GET','POST'])
def results():
    # global variable initialization
    global sql_engine
    global startProgram
    # Form initialization
    queryForm = inputQueryForm()
    # Variable initialization
    timeNow = datetime.datetime.now()
    nextDay = timeNow + datetime.timedelta(days=1)
    queryInput = {}
    output = {}

    # Try to query and plot data
    try:
        # Populate form fields
        getStart = request.args.get('start_time')
        getEnd = request.args.get('end_time')
        if getStart is None and getEnd is None:
            queryInput['Start Time:'] = timeNow.strftime('%Y-%m-%d %H:%M:%S')
            queryInput['End Time:'] = nextDay.strftime('%Y-%m-%d %H:%M:%S')
        else:
            queryInput['Start Time:'] = str(getStart)
            queryInput['End Time:'] = str(getEnd)
         
        # MySQL Query Statement
        query = "select * from sensor_data where date between '" + queryInput['Start Time:'] + "' and '" + queryInput['End Time:'] +"' order by date"
        # Pulls the Query Information
        df = pd.read_sql_query(query, sql_engine).dropna()
        print(query)

        ### Data Cleaning ###

        # unique list of sensor names
        sensorNames = list(df['name'].unique())
        sensorNames.sort()

        # for each sensor
        for i in range(0,len(sensorNames)):
            # name of the sensor
            name = sensorNames[i].replace('\n','').replace(' ','')

            # calibration offset data
            query = "select * from sensor_calibration where name='" + name +"' and concentration=0 order by date desc limit 1"
            calib_df = pd.read_sql_query(query, sql_engine)
            calib_offset = float(calib_df['value'][0])
            # calibration slope data
            query = "select * from sensor_calibration where name='" + name +"' and concentration=1 order by date desc limit 1"
            calib_df = pd.read_sql_query(query, sql_engine)
            calib_slope = float(calib_df['value'][0])

            # raw sensor data -> calibrated data
            tempdf = df[df['name'] == name].reset_index(drop=True)
            calib_data = tempdf['data'].apply(lambda x: (x-calib_offset)/(calib_slope-calib_offset) )

            # convert each sensor data to js chart notation
            for j in range(0,len(calib_data)):
                date = tempdf['date'][j]
                data = calib_data[j]
                
                try:
                    output[name].append({'x':date,'y':data})
                except:
                    output[name] = [{'x':date,'y':data}]
            
    except:
        print('Query Input Error')

    return render_template(
        'results.html', 
        output=output,
        queryInput=queryInput,
        queryForm=queryForm, 
        submit=submitForm()
    )

@app.route('/raspi', methods=['GET','POST'])
def raspi():
    global sql_engine

    # Retrieve request arguments
    rasp = request.args.get('rasp').replace('\n','')
    methane = request.args.get('methane')
    now = request.args.get('now')
    now = datetime.datetime.now().replace(microsecond=0)

    print('RASP: ',rasp)
    print('METHANE: ',methane)
    print('NOW: ',now)

    # Store data onto local database
    df = pd.DataFrame({'name':[str(rasp)],'data':[float(methane)],'date':[str(now)]})
    df.to_sql('sensor_data', con=sql_engine, if_exists='append', index=False)

    return 'ok'

@app.route('/calibrate', methods=['GET','POST'])
def calibrate():
    global sql_engine

    # get the arguments
    rasp = request.args.get('rasp')
    concentration = request.args.get('concentration')
    value = request.args.get('value')
    now = request.args.get('now')
    now = datetime.datetime.now().replace(microsecond=0)

    print('RASP: ',rasp)
    print('CONCENTRATION: ',concentration)
    print('VALUE: ',value)
    print('NOW: ',now)

    # Store data onto local database
    df = pd.DataFrame({'name':[str(rasp)],'concentration':[float(concentration)],'value':[float(value)],'date':[str(now)]})
    df.to_sql('sensor_calibration', con=sql_engine, if_exists='append', index=False)

    return 'ok'

@app.route('/readCalibration', methods=['GET','POST'])
def readCalibration():
    global sql_engine

    rasp = request.args.get('rasp')

    # The rasp argument was not found
    if rasp is None:
        return {'calibration':-100}

    # Looks in local database for calibration data
    query = "select * from sensor_calibration where name='" + str(rasp) +"' order by date desc limit 1"
    df = pd.read_sql_query(query, sql_engine)

    # Calibration data was not found
    if df.empty:
        return {'calibration':-100}

    return {'calibration':df['calibration'][0]}

@app.route('/getCalibration',methods=['GET','POST'])
def getCalibration():
    global sql_engine

    rasp = request.args.get('rasp')

    # The rasp argument was not found
    if rasp is None:
        print('RASP ARGUEMENT NOT FOUND')
        return {'voltage_offset':-100,'slope':-100}

    # Looks in local database for voltage offset calibration data
    query = "select * from sensor_calibration where name='" + str(rasp).replace('\n','') +"' and concentration=0 order by date desc limit 1"
    df = pd.read_sql_query(query, sql_engine)

    # Calibration data was not found
    if df.empty:
        print('QUERY ERROR - NO VOLTAGE OFFSET DATA FOUND')
        print(query)
        voltage_offset = 0
    else:
        voltage_offset = df['value'][0]
    
    # Looks in local database for slope calibration data
    query = "select * from sensor_calibration where name='" + str(rasp).replace('\n','') +"' and concentration=1 order by date desc limit 1"
    df = pd.read_sql_query(query, sql_engine)

    # Calibration data was not found
    if df.empty:
        print('QUERY ERROR - NO SLOPE DATA FOUND')
        print(query)
        slope = 1
    else:
        slope = df['value'][0]
    
    return {'voltage_offset':voltage_offset, 'slope':slope}

@app.route('/getColorThresh',methods=['GET','POST'])
def getColorThresh():
    global sql_engine

    # initialize variable
    data = {}

    # Looks in local database for color threshold data
    query = "select * from threshold where color is not null order by threshold;"
    df = pd.read_sql_query(query, sql_engine)
    
    # dictionary for colors and thresholds
    for i in df.to_dict('split')['data']:
        data[i[0]] = i[1]

    return data

@app.route('/getThreshold',methods=['GET','POST'])
def getThreshold():
    global sql_engine

    rasp = request.args.get('rasp')

    # The rasp argument was not found
    if rasp is None:
        return {'threshold':-5}

    # Looks in local database for calibration data
    query = "select * from threshold where name='" + str(rasp).replace('\n','') +"' limit 1"
    df = pd.read_sql_query(query, sql_engine)

    # Calibration data was not found
    if df.empty:
        return {'threshold':-5}

    return {'threshold':df['threshold'][0]}

@app.route('/runApp',methods=['GET','POST'])
def runApp():
    global startProgram
    return str(startProgram)

@app.route('/localStart',methods=['GET','POST'])
def localStart():
    global startProgram
    startProgram = True
    return 'ok'

if __name__ == '__main__':
    app.run(port=7000, debug=True)
    #flask run -h 192.168.43.175:5000/