from src import Database

def test_save_measurement():
    db = Database()
    for i in range(1, 4):
        point = "test01"
        dust_level = 200 + i
        count = i
        db.save_measurement(point, dust_level, count)
    
def test_get_measurement():
    db = Database()
    data = db.get_measurement()
    print(data)

if __name__ == "__main__":
    test_save_measurement()
    test_get_measurement()