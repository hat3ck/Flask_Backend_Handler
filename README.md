# Flask_Backend_Handler
This is a Python and Flask based application that stores, consumes, and processes logs.  
I’m assuming that the Front-End programmer sends logs in a JSON file to the main directory (sample.json). I’m using Mysql to create a database for logs. There is also a simple HTML webpage so the user can retrieve data based on any combination of user, time range, and log type in an output file with CSV format(output.csv). 
I decided to create 3 different tables in the MySQL database (information about the credentials of the database can be found in app.py). Each table per action type since we don’t have too many actions (views, clicks, & navigates). For updating the database every 5 minutes, I’m using a scheduler to check the input from Front-End every 5 minutes and update the database tables. Finally, I’m handling data transfer between HTML and Python app by using the GET method.  

How to run the app:  
1- You need to install python packages imported at the beginning of the app.py file.  
2- You need to make sure your browser supports Cross-Origin Resource Sharing (CORS).  
3- run app.py with Python 3.  
4- open index.html in a browser, select the combination, and submit. If successful, it will prompt a message and you will be able to see the output.csv file in the main directory.  

Follow up question:  
Based on the scale of data the implementation may be totally different. Here this program can respond to 100 users’ logs per 5 minutes easily. However, for a larger scale of the data Hadoop ecosystem and Spark could be used which also provides the ability to perform data analytics and machine learning implementations. Also, a non-relational database like MongoDB might work better in that scenario. 


