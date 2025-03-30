from src import Database

def test_db():
    db = Database()
    # (measurement_datetime, room, area, location_name, count, um01, um03, um05, running_state, alarm_high)
    data = [
        ("2023-10-01 12:00:00", "Room1", "Area1", "Location1", 1, 100, 200, 300, 0, 0),
        ("2023-10-01 12:01:00", "Room2", "Area2", "Location2", 2, 110, 210, 310, 0, 0)
    ] 
    db.save_measurement(data)
    print("Done")

if __name__ == "__main__":
    test_db()