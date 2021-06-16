import math
import numpy as np
import pyodbc
from flask import Flask
from flask import render_template, request

app = Flask(__name__)

connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=earthquakes2021.database.windows.net;PORT=1433;DATABASE=assignment2;UID=earthquakes2021;PWD=harika@123')

# Converts degree to radians
def degToRad(degree):
    return degree * np.pi / 180


def geoDifference(a_latitude_deg, a_longitude_deg, latitude_deg, longitude_deg):
    radius_earth_miles = 3961
    radius_earth_kilometers = 6373

    a_latitude = degToRad(np.array(a_latitude_deg))
    a_longitude = degToRad(np.array(a_longitude_deg))
    latitude = degToRad(latitude_deg)
    longitude = degToRad(longitude_deg)

    d_latitude = a_latitude - latitude
    d_longitude = a_longitude - longitude

    A = (np.sin(d_latitude / 2) ** 2) + np.cos(a_latitude) * np.cos(latitude) * (np.sin(d_longitude / 2) ** 2)
    C = 2 * np.arctan((A ** 0.5), ((1 - (A)) ** 0.5))

    dist_miles = C * radius_earth_miles
    dist_kilometers = C * radius_earth_kilometers

    return dist_kilometers

def getCorrespondingTime(a_longitude_deg, a_gmt_time):
    gmt_time = np.array(a_gmt_time, dtype='datetime64')
    deltaTime_minutes = (np.array(a_longitude_deg)*4).astype('timedelta64[m]')
    correspondingTime = gmt_time + deltaTime_minutes
    return correspondingTime

@app.route('/')
@app.route('/home')
def home():
    return render_template("base.html")


@app.route('/between', methods=["POST"])
def Between():
    magfrom = (request.form.get("magfrom"))
    magto = (request.form.get("magto"))
    print(magfrom, type(magto))
    cursor = connection.cursor()
    cursor.execute("select * from all_month where mag Between " + (magfrom) + " and " + (magto))
    data = cursor.fetchall()
    data_count = len(data)
    if len(data)==0:
        return "<b>No data to display</b>"
    else:
        return render_template('between.html', data=data,count=data_count,magfrom=magfrom,magto=magto)
    # xreturn render_template('Above5.html')


@app.route('/Above5',methods=["POST"])
def Above5():
    magnitude = 5.0
    cursor = connection.cursor()
    cursor.execute("select * from all_month where mag>{}".format(magnitude))
    data = cursor.fetchall()
    data_count = len(data)
    return render_template('Above5.html', data=data, count=data_count)


@app.route('/calGeoDistance', methods=['POST'])
def CalGeoDistance():
    latitude = float(request.form.get("latitude"))
    longitude = float(request.form.get("longitude"))
    distance = float(request.form.get("distance"))
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM all_month")
    data = cursor.fetchall()
    latitudes = [float(e[1]) for e in data]
    longitudes = [float(e[2]) for e in data]
    data_count = len(data)
    d = geoDifference(latitudes, longitudes, latitude, longitude)
    new_data = []
    for i in range(len(data)):
        if d[i] <= distance:
            new_data.append(data[i])
    if len(new_data)==0:
        return "<b>No data to display</b>"
    else:
        return render_template("location.html", data=new_data, count=data_count)


@app.route('/daterange', methods=["POST"])
def daterange():
    # from_date=str(request.form.get("from_date"))
    # to_date=str(request.form.get("to_date"))
    # from_date = (datetime.strptime(request.form.get("from_date"), '%Y-%m-%d').strftime('%Y-%m-%d'))
    # to_date = (datetime.strptime(request.form.get("to_date"), '%Y-%m-%d').date().strftime('%Y-%m-%d'))
    from_date=request.form.get("from_date")
    to_date=request.form.get("to_date")
    print(from_date, to_date, type(from_date))

    cur = connection.cursor()
    #cur.execute("select * from all_month where (REPLACE(REPLACE(timedate, 'T', ' '), 'Z', '')) between " + from_date + "and " + to_date)
    cur.execute("select * from all_month where time between " + from_date + "and " + to_date )

    data = cur.fetchall()
    return render_template('daterange.html', data=data)


@app.route('/api/clusters', methods=['GET'])
def apiClusters():
    from_latitude = float(request.args.get("from_latitude"))
    from_longtitude = float(request.args.get("from_longitude"))
    to_latitude = float(request.args.get("to_latitude"))
    to_longtitude = float(request.args.get("to_longitude"))
    area = float(request.args.get("area"))
    print(area)
    print(to_latitude)
    print(to_longtitude)
    print(from_latitude)
    print(from_longtitude)
    # a .rea = 1000000
    length_area = area ** 0.5
    degree_change = length_area/100      # 111km per degree
    x_latitude = degree_change if to_latitude-from_latitude > 0 else -degree_change
    x_longitude = degree_change if to_longtitude-from_longtitude > 0 else -degree_change

    clusters = []
    lat_index = int(math.ceil((to_latitude-from_latitude)/x_latitude))
    long_index = int(math.ceil((to_longtitude-from_longtitude)/x_longitude))

    start_lat = from_latitude
    Map = []
    # clusters.append(start_lat)
    updated_html = '<table> <tr> <th> From Latitude </th> <th> From Longitude </th> <th> To Latitude </th> <th> To Longitude </th> <th> Count </th> <th> Avg Mag </th> </tr> '
    for i in range(lat_index):
        end_lat = start_lat + x_latitude
        start_long = from_longtitude
        lower_lat = start_lat if start_lat < end_lat else end_lat
        upper_lat = start_lat if start_lat > end_lat else end_lat
        for j in range(long_index):
            end_long = start_long + x_longitude
            clusters.append([start_lat, start_long, end_lat, end_long])
            lower_long = start_long if start_long < end_long else end_long
            upper_long = start_long if start_long > end_long else end_long
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) AS COUNT, AVG(MAG) AS MAG_AVG FROM all_month WHERE (LATITUDE BETWEEN " + str(lower_lat) + " AND " + str(upper_lat) + ") AND (LONGITUDE BETWEEN " + str(lower_long) + " AND " + str(upper_long) + ")")
            rows = cursor.fetchall()
            updated_html += '<tr> <td> ' + str(start_lat) + ' </td> <td> ' + str(start_long) + ' </td> <td> ' + str(end_lat) + ' </td> <td> ' + str(end_long) + ' </td> <td> ' + str(rows[0][0]) +' </td> <td> ' + str(rows[0][1]) +'</tr>'
            clusters.append([start_lat, start_long, end_lat, end_long])
            print([start_lat, start_long, end_lat, end_long])
            start_long = end_long
        start_lat = end_lat

    return updated_html + '</table>'


@app.route('/hourHistogram', methods=['Post'])
def apiHourHistogram():
    cursor=connection.cursor()
    cursor.execute("SELECT MAG, TIME, LATITUDE, LONGITUDE FROM all_month WHERE MAG > 4.0")
    data = cursor.fetchall()

    time = [str(e[1]) for e in data]
    longitudes = [float(e[3]) for e in data]

    Map = []
    for i in range(24):
        Map.append([])
    C_TIME = getCorrespondingTime(longitudes, time)
    hrs = [int(str(e)[11:13]) for e in C_TIME]
    for i in range(len(data)):
        Map[hrs[i]].append(data[i])

    update_html = '<table> <tr> <th> Hours </th> <th> Count </th> <th> Average Magnitude </th> <th> Percentage </th> </tr> '
    for i in range(24):
        update_html += '<tr> <th> ' + str(i) + ' </th> <td> ' + str(len(Map[i])) + ' </td> '
        sum_mag = 0
        for e in Map[i]:
            sum_mag += float(e[0])
        update_html += '<td> ' + str(sum_mag / len(Map[i])) + '</td> '
        update_html += '<td> ' + str(float(len(Map[i])) / len(data)) + '</td> </tr>'

    return update_html

if __name__ == "__main__":
    app.run(debug=True)
