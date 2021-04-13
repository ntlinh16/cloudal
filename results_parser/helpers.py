import sys
import logging

IGNORE_DIRS = ['sweeps', 'stdout+stderr', 'graphs', '.DS_Store']


def get_logger(name='parser', level=logging.INFO):
    format = '%(asctime)s [%(levelname)s] - %(name)s - %(message)s'
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(format))

    logging.basicConfig(
        level=logging.DEBUG,
        format=format,
        handlers=[handler]
    )
    logger = logging.getLogger(name)

    return logger
