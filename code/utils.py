import logging

import settings


class LoggerSingleton:
    _instances = {}

    @classmethod
    def get_logger(cls, name):
        if name not in cls._instances:
            log_lvl = settings.LOGLEVEL

            logger = logging.getLogger(name)
            logger.setLevel(log_lvl)
            logger.propagate = False

            handler = logging.StreamHandler()
            handler.setLevel(log_lvl)
            handler.setFormatter(logging.Formatter(settings.LOG_FORMAT))
            logger.addHandler(handler)

            cls._instances[name] = logger

        return cls._instances[name]
