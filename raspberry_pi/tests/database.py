from src import Database

def test_db():
    db = Database()
    # (measurement_datetime, room, area, location_name, count, um01, um03, um05, running_state, alarm_high)

    data = {"measurement_datetime": "2025-03-31 12:00:00", "room": "CR11", "area": "1K", "location_name": "IS-1K-019", "count": 1, "um01": 1304, "um03": 118, "um05": 67, "running_state": 1, "alarm_high": 1}
    l = []
    print(tuple(data.values()))
    l.append(tuple(data.values()))
    # print(   l)
    # data1 = [
    #     ("2025-03-31 12:00:00", "testRoom", "testArea", "Location1", 1, 100, 200, 300, 0, 0),
    # ] 
    # db.save_measurement(data1)
    # data2 = [
    #     ("2025-03-31 12:01:00", "testRoom", "testArea", "Location2", 2, 110, 210, 310, 0, 0)
    # ]
    db.save_measurement(l)

    print("Done")

if __name__ == "__main__":
    test_db()