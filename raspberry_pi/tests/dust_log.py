from src import DustLogger

def test_log():
    logger = DustLogger()
    logger.setup_logger("test")
    logger.save_log({"location": "test", "data": "test"}, 1)
    print("Done")

if __name__ == "__main__":
    test_log()