from flask import Flask
from flask import jsonify
from flask import request
from flask_cors import CORS, cross_origin
import json
import pandas as pd
import sqlalchemy
import mysql.connector
import atexit
from apscheduler.schedulers.background import BackgroundScheduler



# I'm using mysql to store the data and I'm creating 3 different tables for each action
def create_database():
    # connecting to mysql
    mydb = mysql.connector.connect(
      host="localhost",
      user="root",
      password=""
    )

    # create database
    mycursor = mydb.cursor()
    mycursor.execute("CREATE DATABASE IF NOT EXISTS openhouseai")

    #Creating views table
    mycursor.execute("USE openhouseai;")
    mycursor.execute("CREATE TABLE IF NOT EXISTS views(userId VARCHAR(255) PRIMARY KEY, sessionId VARCHAR(255),"
                     " actionTime DATETIME NULL, actionType VARCHAR(255), viewedId VARCHAR(255));")

    #Creating clicks table
    mycursor.execute("CREATE TABLE IF NOT EXISTS clicks(userId VARCHAR(255) PRIMARY KEY, sessionId VARCHAR(255),"
                     " actionTime TIMESTAMP NULL , actionType VARCHAR(255), locationX INT, locationY INT);")

    #Creating navigates table
    mycursor.execute("CREATE TABLE IF NOT EXISTS navigates(userId VARCHAR(255) PRIMARY KEY, sessionId VARCHAR(255),"
                     " actionTime TIMESTAMP NULL , actionType VARCHAR(255), pageFrom VARCHAR(255), pageTo VARCHAR(255));")

# This function reads the data and provides 3 different dataframes based on the FE input(I'm assuming they provide a json file in the same folder and keep updating it every 5 minutes)
def get_data():
    # open the input file from FE
    with open('sample.json', 'r') as f:
        data = json.load(f)

    # Expand the data to create a DataFrame
    df= pd.concat([pd.DataFrame(data), pd.DataFrame(list(data['actions']))], axis=1).drop('actions', 1)
    df= pd.concat([pd.DataFrame(df), pd.DataFrame(list(df['properties']))], axis=1).drop('properties', 1)

    #change column names for less confusion
    df = df.rename(columns={"time": "actionTime", "type": "actionType"})

    # convert time to proper format
    df['actionTime'] =  df['actionTime'].astype('datetime64[ns]')

    #Create 3 different dataframes for each action

    #Creating view dataFrame
    view_df = df [df["actionType"]=="VIEW"]

    #Creating click dataFrame
    click_df = df [df["actionType"]=="CLICK"]

    #Creating navigate dataFrame
    navigate_df = df [df["actionType"]=="NAVIGATE"]

    #Deleting nan columns for each dataset
    view_df = view_df.drop(['locationX', 'locationY', 'pageFrom', 'pageTo'], axis=1).reset_index(drop=True)
    click_df = click_df.drop(['pageFrom', 'pageTo', 'viewedId'], axis=1).reset_index(drop=True)
    navigate_df = navigate_df.drop(['locationX', 'locationY', 'viewedId'], axis=1).reset_index(drop=True)

    #returning the data
    return view_df, click_df, navigate_df


#Inserting the FE logs into database
def insert_data(data):

    # set used Id as the index
    view_df = data[0].set_index("userId")
    click_df = data[1].set_index("userId")
    navigate_df = data[2].set_index("userId")



    # Insert each view log to the views table

    #Create engine to insert into the database
    cnx = sqlalchemy.create_engine('mysql://root:@localhost/openhouseai', echo=False)

    # Try to insert the data into database
    try:
        #Inserting into views
        view_df.to_sql('views', cnx, if_exists='append')

        #Inserting into clicks
        click_df.to_sql('clicks', cnx, if_exists='append')

        #Inserting into navigates
        navigate_df.to_sql('navigates', cnx, if_exists='append')
        print("database updated")
    # If unsucsseful, prompt an error message
    except:
        print("An error has occured (check the data for duplication)")

#Based on user's input we will retrieve the data from the database and create a csv file
def fetch_data(user_data):

    # Getting the data from server
    cnx = sqlalchemy.create_engine('mysql://root:@localhost/openhouseai', echo=False)
    view_df = pd.read_sql("SELECT * FROM {}".format("views"), cnx)
    click_df = pd.read_sql("SELECT * FROM {}".format("clicks"), cnx)
    navigate_df = pd.read_sql("SELECT * FROM {}".format("navigates"), cnx)

    #combining all the data
    total_df = view_df.append(click_df)
    total_df = total_df.append(navigate_df).reset_index(drop=True)


    # check if we have an inpur for userId from the user
    if (user_data[0]):
        #retrieve the data with userId
        total_df = total_df[ total_df['userId'] == user_data[0]]

    #check if the user selected a range of date
    #From
    if (user_data[1]):
        # convert date values to proper type
        user_data[1] = pd.to_datetime(user_data[1])
        #retrieve the data with range
        total_df = total_df[ total_df['actionTime'] >= user_data[1]]

    #To
    if (user_data[2]):
        # convert date values to proper type
        user_data[2] = pd.to_datetime(user_data[2])
        # retrieve the data with range
        total_df = total_df[total_df['actionTime'] <= user_data[2]]

    #Check if the user selected an action type
    if (user_data[3]):
        # retrieve the data with action type
        total_df = total_df[total_df['actionType'] == user_data[3].upper()]

    #Drop empty columns
    total_df = total_df.dropna(how='all', axis=1)

    return total_df

# updating database
def updater():
    insert_data(get_data())

# Scheduler will get the new data from the Front-End every 5 minutes and inserts it to the database
def run_scheduler(seconds):
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=updater, trigger="interval", seconds=seconds)
    scheduler.start()
    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())


app = Flask(__name__)
cors = CORS(app)

@app.route('/data', methods=['GET', 'POST'])
@cross_origin()
#Recieve and process the data from user side (HTML)
def user_handler():

    # Recieving data from user
    userData = []
    userData.append(str(request.args.get('userId')))
    userData.append(str(request.args.get('dateFrom')))
    userData.append(str(request.args.get('dateTo')))
    userData.append(str(request.args.get('actionType')))

    # retrieve the data from database based on user inputs
    r_data = fetch_data(userData)

    # if there are no records matching the defined inputs
    if(r_data.empty):
        return jsonify("Couldn't retrieve the data, please check the inputs")
    # otherwise if there is data matching the defined inputs
    else:
        r_data.to_csv("output.csv", index=False)
        return jsonify("Logs are saved in the output.csv file in the same directory")



if __name__ == '__main__':
    #Creating tables and database if they don't exist
    create_database()

    #Inserting the initial data to the database
    insert_data(get_data())

    #Run scheduler for every 5 minutes
    run_scheduler(seconds=5*60)

    app.run(host='0.0.0.0', port=500)
