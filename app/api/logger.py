import logging

logger = logging.getLogger('gatecontrol')
# Note that the log level of the logger is set in the Config
ch = logging.StreamHandler()
formatter = logging.Formatter(logging.BASIC_FORMAT)
ch.setFormatter(formatter)
logger.addHandler(ch)
