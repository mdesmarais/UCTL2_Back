import asyncio
import json
import logging
import os.path
import signal
import subprocess
import sys
from threading import Thread

import aiohttp

import events
import uctl2_race
from config import Config, InvalidConfigError
from notifier import Notifier
from uctl2_setup import readRace

root_logger = logging.getLogger()


def createDefaultConfig(path: str) -> bool:
    """
        Creates a default configuration with the given path

        If a file with the same name aleready exists, then it
        will be overwrited.

        :param path: path of the configuration file
        :return: a boolean that indicates if the file creation succeded or not
    """
    try:
        with open(path, 'w') as f:
            config = Config()
            json.dump(config, f, indent=2)
    except Exception as e:
        print('Unable to create a default configuration', path, e)
        return False
    
    return True


def load_config(path: str) -> Config:
    """
        Loads a configuration from a file and transforms it
        to a Config instance.

        :param path: path to the configuration file
        :return: an instance to Config

        :raises FileNotFoundError: if the given path is not an existing file
        :raises json.JSONDecodeError: if the file is not correctly formated
        :raises InvalidConfigError: if the configuration is not valid
    """
    logger = logging.getLogger('load_config')

    logger.info('Loading configuration %s', path)
    try:
        with open(path, 'r') as f:
            jsonConfig = json.load(f)

            config = Config.readFromJson(jsonConfig)
        
        return config
    except FileNotFoundError:
        logger.error('Unable to open config file %s', path)
        raise
    except json.JSONDecodeError as e:
        logger.error('The given config file does not contain a valid JSON\n-> %s', e)
        raise
    except InvalidConfigError as e:
        logger.error('Invalid configuration : %s', e)
        raise


async def main(config, race, notifier): 
    # Starting the race file broadcasting
    uctl2_race.broadcast_running = True
    async with aiohttp.ClientSession() as session:
        await uctl2_race.broadcastRace(race, config, notifier, session)

    await notifier.stopNotifier()


def setup(config, handlers=[], loop=asyncio.get_event_loop()):
    for handler in handlers:
        root_logger.addHandler(handler)

    root_logger.setLevel(logging.INFO)

    race = readRace(config)

    if race is False:
        root_logger.error('Unable to read race from config')
        return

    notifier = Notifier(race)

    loop.add_signal_handler(signal.SIGINT, stop_broadcast)
    loop.add_signal_handler(signal.SIGTERM, stop_broadcast)

    loop.run_until_complete(asyncio.gather(notifier.startNotifier(5680), notifier.broadcaster(), main(config, race, notifier)))
    loop.close()


def stop_broadcast(*args):
    uctl2_race.broadcast_running = False


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Usage: uctl2.py path_to_config_file')
        configName = 'config.json'
        if not os.path.isfile(configName) and createDefaultConfig(configName):
            print('A default configuration %s has been created' % (configName,))
        sys.exit(-1)

    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s - %(message)s')
    ch.setFormatter(formatter)

    root_logger.addHandler(ch)
    root_logger.setLevel(logging.INFO)

    try:
        config = load_config(os.path.abspath(sys.argv[1]))
    except:
        sys.exit(-1)

    setup(config, [ch])
