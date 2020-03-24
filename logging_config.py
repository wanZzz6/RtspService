# -*- conding:utf-8 -*-

import datetime
import logging
import logging.config
import os

IS_INIT = False


def genLogDict(logDir, logFile):
    """
    生成日志参数字典
    :param logDir: 日志文件夹
    :param logFile: 日志文件名
    :return: 参数字典
    """

    logDict = {
        "version": 1,
        "disable_existing_loggers": False,
        # 日志输出格式设置
        "formatters": {
            "simple": {
                'format': '%(asctime)s [%(name)s:%(lineno)d] [%(levelname)s]- %(message)s'
            },
            'standard': {
                'format': '%(asctime)s [%(threadName)s:%(thread)d] [%(name)s:%(lineno)d] [%(levelname)s]- %(message)s'
            },
        },

        "handlers": {
            # 控制台处理器,控制台输出
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "stream": "ext://sys.stdout"
            },
            # 默认处理器,打印到文件
            "default": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "simple",
                "filename": os.path.join(logDir, logFile),
                'mode': 'w+',
                "maxBytes": 1024 * 1024 * 10,  # 10 MB
                "backupCount": 20,
                "encoding": "utf8"
            },
        },
        "root": {
            'handlers': ['default', 'console'],
            'level': "DEBUG",
            'propagate': False
        }
    }
    return logDict


def initLogConf(log_file_name=''):
    """
    配置日志
    """
    baseDir = os.path.dirname(os.path.abspath(__file__))
    logDir = os.path.join(baseDir, "./logs")
    if not os.path.exists(logDir):
        os.makedirs(logDir)  # 创建路径
    if not log_file_name:
        log_file_name = datetime.datetime.now().strftime("%Y-%m-%d") + ".log"
    logDict = genLogDict(logDir, log_file_name)
    logging.config.dictConfig(logDict)
    logging.debug("Init logging config, file : [{}]".format(log_file_name))


def getLogger(name):
    if not IS_INIT:
        initLogConf()

    return logging.getLogger(name)


if __name__ == '__main__':
    initLogConf()
    logger = logging.getLogger("test")
    logger.error('hello world')
