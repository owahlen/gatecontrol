import logging

logger = logging.getLogger('gatecontrol')
# Note that the log level of the logger is set in the Config
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)
