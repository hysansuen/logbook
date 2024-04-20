#  ================README=================
# Change following parameters as desired.

# no. of steps on the great circle route, increased steps will increase runtime and accuracy
accuracy = 10

# upward hour adjustment for 3-man crew, recommended values 1.4-1.6.
# increased bias increase overall in-seat hours
three_man_crew_bias = 1.54

# for P2X:
# adjust hours to be deducted from block hours for in-seat time,
# if set to 0, taxi time will still be deducted
block_minus_hour = 1
# ========================================



import csv
import math
from pyproj import Geod
from datetime import datetime, timedelta
from suntimes import SunTimes


port_lat_lon = {}
g = Geod(ellps='clrk66')

with open("iata-icao.csv", encoding="utf8") as portdetails:
    reader = csv.reader(portdetails)
    for row in reader:
        if row[5][-1] not in {'0','1','2','3','4','5','6','7','8','9'}:
            continue
        port_lat_lon[row[3]] = [float(row[5]),float(row[6])]


def caldaynight(origin:str, dest:str, airborne_UTC:str, landing_UTC:str, departure_date:str, off_block_UTC:str, on_block_UTC:str, shitRest:bool = True, P2X:bool = True):
    origin_lat, origin_lon = port_lat_lon[origin]
    dest_lat, dest_lon = port_lat_lon[dest]
    today = datetime.strptime(departure_date,"%Y/%m/%d")

    airborne_UTC = airborne_UTC[:5]
    landing_UTC = landing_UTC[:5]
    off_block_UTC = off_block_UTC[:5]
    on_block_UTC = on_block_UTC[:5]

    landing_UTC = datetime.strptime(landing_UTC,"%H:%M")
    landing_UTC = landing_UTC.replace(year=today.year,month=today.month,day=today.day)
    airborne_UTC = datetime.strptime(airborne_UTC,"%H:%M")
    airborne_UTC = airborne_UTC.replace(year=today.year,month=today.month,day=today.day)
    off_block_UTC = datetime.strptime(off_block_UTC,"%H:%M")
    off_block_UTC = off_block_UTC.replace(year=today.year,month=today.month,day=today.day)
    on_block_UTC = datetime.strptime(on_block_UTC,"%H:%M")
    on_block_UTC = on_block_UTC.replace(year=today.year,month=today.month,day=today.day)

    flight_time = landing_UTC - airborne_UTC
    if flight_time < timedelta(0):
        flight_time = flight_time + timedelta(hours=24)
    # print(flight_time)

    block_time = on_block_UTC - off_block_UTC
    taxi_time = block_time - flight_time
    if taxi_time < timedelta(0):
        taxi_time += timedelta(hours=24)

    day_hour_first_half = 0
    night_hour_first_half = 0
    day_hour_second_half = 0
    night_hour_second_half = 0
    cur_time = airborne_UTC
    no_of_steps = flight_time.total_seconds()//3600*accuracy
    # make steps odd
    if no_of_steps%2 != 1:
        no_of_steps += 1
    timestep = flight_time/no_of_steps
    count = 0

    routepts = [[origin_lon,origin_lat]]
    greatcircle = g.npts(origin_lon,origin_lat,dest_lon,dest_lat,no_of_steps)
    routepts.extend(greatcircle)
    routepts.append([dest_lon,dest_lat])

    for lon, lat in routepts:
        if lat > 66:
            lat = 66
        # print(cur_time)
        # print(f'{lat:.3f} {lon:.3f}')
        sun = SunTimes(lon,lat,10000)
        sunrise = sun.riseutc(cur_time)
        sunrise_next = sun.riseutc(cur_time+timedelta(hours=24))
        sunset = sun.setutc(cur_time)
        sunset_prev = sun.setutc(cur_time-timedelta(hours=24))
        # print(sunset_prev,sunrise,sunset,sunrise_next)

        # daytime
        if sunrise_next == "PD" or sunset_prev == "PD" or sunrise == "PD" or sunset == "PD" or sunrise < cur_time < sunset or cur_time > sunrise_next or cur_time < sunset_prev:
            if lon == origin_lon and lat == origin_lat:
                if not P2X:
                    day_hour_first_half += (airborne_UTC - off_block_UTC).total_seconds()/3600
                # if P2X, ignore taxi time
                continue
            if count < (no_of_steps+2)//2:
                day_hour_first_half += timestep.total_seconds()/3600
            else:
                if lon == dest_lon and lat == dest_lat:
                    if not P2X:
                        day_hour_second_half += (on_block_UTC - landing_UTC).total_seconds()/3600
                else:
                    day_hour_second_half += timestep.total_seconds() / 3600
            count += 1

        # nighttime
        else:
            if lon == origin_lon and lat == origin_lat:
                if not P2X:
                    night_hour_first_half += (airborne_UTC - off_block_UTC).total_seconds() / 3600
                continue
            if count < (no_of_steps+2)//2:
                night_hour_first_half += timestep.total_seconds()/3600
            else:
                if lon == dest_lon and lat == dest_lat:
                    # if P2X, ignore taxi time
                    if not P2X:
                        night_hour_second_half += (on_block_UTC - landing_UTC).total_seconds()/3600
                else:
                    night_hour_second_half += timestep.total_seconds() / 3600
            count += 1
        cur_time = cur_time + timestep


    # crew complement
    # AUS/Middle East : 3-man
    if origin[0] in {"Y","O"} or dest[0] in {"Y","O"}:
        day_hour_first_half *= three_man_crew_bias
        night_hour_first_half *= three_man_crew_bias
        day_hour_second_half *= three_man_crew_bias
        night_hour_second_half *= three_man_crew_bias
    # North America/Europe/Africa : 4-man
    elif origin[0] in {"K","C","E","L","F"} or dest[0] in {"K","C","E","L","F"}:
        pass
    else:
        day_hour = day_hour_first_half + day_hour_second_half
        night_hour = night_hour_first_half + night_hour_second_half

    # if shitRest, use greater nightHours
    if shitRest:
        if night_hour_first_half >= night_hour_second_half:
            day_hour, night_hour =  day_hour_first_half,night_hour_first_half
        else:
            day_hour, night_hour = day_hour_second_half,night_hour_second_half

    # if total ignored taxi time is less than block_minus_hour (default: 1 hr), deduct day and night hour up to (block time - block_minus_hour)/2.
    if P2X and taxi_time < timedelta(hours=block_minus_hour):
        deductible = (timedelta(hours=block_minus_hour) - taxi_time).total_seconds()/3600/2
        # print(timedelta(hours=deductible*2)+taxi_time)
        # print(deductible)
        if day_hour - deductible < 0:
            night_hour -= deductible*2
        elif night_hour - deductible < 0:
            day_hour -= deductible*2
        else:
            day_hour -= deductible
            night_hour -= deductible

    return math.ceil(day_hour*10)/10, math.ceil(night_hour*10)/10

# print(caldaynight("VHHH","YMML","14:34","23:31","2024/04/18","14:20","23:40"))