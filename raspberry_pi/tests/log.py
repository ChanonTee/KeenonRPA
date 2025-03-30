from src.dust_log import DustLogger

logger = DustLogger()
logger.setup_logger("test")
logger.save_log({"location": "test", "data": "test"}, 1)
print("Done")