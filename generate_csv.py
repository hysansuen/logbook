# =================README=====================
# Start from here
# 1. Locate CX logbook directory and change the csv reader path below.
# e.g. if logbook is at root directory, enter "./Merged1_LogBook_2017 Mar-2019 Feb]"
logbook_paths = ["./hysan/Merged1_LogBook_2024 Jun-2025 Feb.txt"
#                 "./hysan/Merged1_LogBook_2019 Feb-2021 Jan.txt",
 #                "./hysan/Merged1_LogBook_2022 Nov-2024 Apr.txt",
  #               "./hysan/Merged1_LogBook_2024 Mar-2024 Apr.txt"]


# 2. Whose logbook is this?
name = "hysan"

# 3. If P2X not needed, set p2x to False (automatically revert to P2)
p2x = True
# 4. (optional) go to daynight.py and adjust parameters if needed.
# =============================================



import datetime
from daynight import caldaynight
import csv
from tail_to_type import b773

log = []
# log = [{departure_date:2022/12/12, off_block_UTC: 12:22....}, {},....]

iata_to_icao = {}
with open("iata-icao.csv", encoding="utf8") as iataicaomap:
    reader = csv.reader(iataicaomap)
    for row in reader:
        if row[5][-1] not in {'0','1','2','3','4','5','6','7','8','9'}:
            continue
        iata_to_icao[row[2]] = row[3]


def logger(reader):
    for row in reader:
        if not row:
            continue
        if row[0][:2] != "20":
            continue
        flight_info = row[0].split()

        if len(flight_info) == 4:
            # sim duty
            if log and log[-1]['departure_date'] == flight_info[0] and (not log[-1]["isFlightDuty"] and log[-1]["duty_code"] == flight_info[3])  :
                continue
            log.append({"isFlightDuty": False,
                        "departure_date": flight_info[0],
                        "duty_code": flight_info[3],
                        })
        else:
            # flight duty
            if log and log[-1]['departure_date'] == flight_info[0] and log[-1]['origin'] == iata_to_icao[flight_info[2]]:
                print("DUPLICATE")
                continue

            # Adjust CX logbook departure date(local) to UTC.
            # if off block time is +1 or -1 ,adjust departure date
            if len(flight_info[6]) > 5:
                if flight_info[6][-2:] == "+1":
                    flight_info[0] = datetime.datetime.strftime(
                        (datetime.datetime.strptime(flight_info[0], "%Y/%m/%d") + datetime.timedelta(days=1)),
                        "%Y/%m/%d"
                    )
                else:
                    flight_info[0] = datetime.datetime.strftime(
                        (datetime.datetime.strptime(flight_info[0], "%Y/%m/%d") - datetime.timedelta(days=1)),
                        "%Y/%m/%d"
                    )

            if flight_info[4] in b773:
                ac_type = 'B777-300'
            else:
                ac_type = 'B777-300ER'

            log.append({"isFlightDuty": True,

                        "departure_date":flight_info[0],

                        "reg" : flight_info[4],

                        "type" : ac_type,

                        "pic" : flight_info[-2] + " " + flight_info[-1],

                        "origin":iata_to_icao[flight_info[2]],

                        "dest":iata_to_icao[flight_info[3]],

                        "off_block_UTC":flight_info[6],

                        "airborne_UTC":flight_info[7],

                        "landing_UTC":flight_info[8],

                        "on_block_UTC":flight_info[9],

                        })


# READS CX LOGBOOK FORMAT HERE, CHANGE DIRECTORY, ADD CSV READER IF MULTIPLE LOGBOOKS EXIST.
for path in logbook_paths:
    with open(path, encoding="utf8") as logbook1:
        reader = csv.reader(logbook1)
        logger(reader)


for i in range(len(log)):
    flight = log[i]
    if flight['isFlightDuty']:
        departure_date = flight['departure_date']
        origin = flight['origin']
        dest = flight['dest']
        off_block_UTC = flight['off_block_UTC']
        airborne_UTC = flight['airborne_UTC']
        landing_UTC = flight['landing_UTC']
        on_block_UTC = flight['on_block_UTC']
        log[i]['day'], log[i]['night'] = caldaynight(origin,dest,airborne_UTC,landing_UTC,departure_date,off_block_UTC,on_block_UTC,p2x)

total_day = 0
total_night = 0
total_sectors = 0

for r in log:
    if "day" in r:
        total_day += r['day']
    if "night" in r:
        total_night += r['night']
    if r["isFlightDuty"]:
        total_sectors += 1
    print(r)
total = total_day + total_night

print(total,total_day,total_night,total_sectors)

# daynight hours, change resulting file name as required
with open(f"daynighthours-{name}.csv", "w", newline='') as file:
    writer = csv.writer(file)
    field = ['isFlightDuty','departure date UTC','type','registration','pilot-in-command','origin','dest','off block UTC','airborne UTC','landing UTC','on block UTC','day','night','duty code']
    writer.writerow(field)
    for flight in log:
        if flight['isFlightDuty']:
            writer.writerow([True,flight['departure_date'],flight['type'],flight['reg'],flight['pic'],flight['origin'],
                             flight['dest'],flight['off_block_UTC'],flight['airborne_UTC'],flight['landing_UTC'],
                            flight['on_block_UTC'],flight['day'],flight['night'],''])
        else:
            writer.writerow([False,flight['departure_date'],"","","","","","","","","","","",flight['duty_code']])
    writer.writerow(["","","","","","","","","","","total day/night",total_day,total_night])
    writer.writerow(["","","","","","","","","","","","total hours:",total])
    writer.writerow(["", "", "", "","", "","","", "", "", "", "total sectors:", total_sectors])


# REPORT LEFT PAGE, change resulting file name as required
with open(f"{name}_report_left.csv", "w", newline="") as file:
    writer = csv.writer(file)
    fields = ['Year/20XX','Month/Date','Type','Registration','Pilot-in-command','Co-pilot or student', "Holder's operating capacity",'  From   To ','Take-offs','Landings']
    writer.writerow(fields)
    for flight in log:
        if flight['isFlightDuty']:
            if p2x:
                writer.writerow([flight['departure_date'].split('/')[0],
                                 flight['departure_date'].split('/')[1] + '/' + flight['departure_date'].split('/')[2],
                                 flight['type'],
                                 flight['reg'],
                                 flight['pic'],
                                 'Self',
                                 'P2X',
                                 f'{flight["origin"]}    {flight["dest"]}',
                                 "",
                                 ""
                                 ])
            else:
                writer.writerow([flight['departure_date'].split('/')[0],
                                 flight['departure_date'].split('/')[1] + '/' + flight['departure_date'].split('/')[2],
                                 flight['type'],
                                 flight['reg'],
                                 flight['pic'],
                                 'Self',
                                 'P2',
                                 f'{flight["origin"]}    {flight["dest"]}',
                                 "",
                                 ""
                                 ])

        else:
            writer.writerow([flight['departure_date'].split('/')[0],
                             flight['departure_date'].split('/')[1] + '/' + flight['departure_date'].split('/')[2],
                             'B777',
                             'CPA',
                             "",
                             "Self",
                             'P/UT',
                             "",
                             "",
                             ""
            ])


# REPORT RIGHT PAGE, change resulting file name as required
with open(f"{name}_report_right.csv", "w", newline="") as file:
    writer = csv.writer(file)
    fields = ['P1 day','P2 day', 'P2X day', 'Dual day','P1 night','P2 night', 'P2X night', 'Dual night',
              'Instrument Flying','Simulator Time','Remarks']
    writer.writerow(fields)
    for flight in log:
        if flight["isFlightDuty"]:
            writer.writerow([
                "",
                "",
                flight['day'],
                "",
                "",
                "",
                flight['night'],
                "",
                flight['day'] + flight['night'],
                "",
                ""
            ])
        else:
            writer.writerow([
                "","","","","","","","",
                "2",
                "4",
                flight['duty_code']
            ])
