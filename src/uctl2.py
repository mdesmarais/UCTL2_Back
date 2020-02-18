import aiohttp
import asyncio
import json
import logging
import os.path
import subprocess
import sys
from threading import Thread

from config import Config
from uctl2_race import broadcastRace
from uctl2_setup import readRace, sendRace
import events
import notifier


def createDefaultConfig(name):
    """
        Creates a default configuration with the given name

        If a file with the same name aleready exists, then it
        will be overwrited.

        :param name: name of the configuration file
        :ptype name: str
        :return: a boolean that indicates if the file creation succeded or not
        :rtype: bool
    """
    try:
        with open(name, 'w') as f:
            config = Config()
            json.dump(config, f, indent=2)
    except Exception as e:
        print('Unable to create a default configuration', name, e)
        return False
    
    return True


def executeSimulation(simPath, configPath):
    """
        Executes the jar of the simulation

        It creates a new process where its output is redirected
        to the sim logger (name=Sim).
        This function should be executed in a separate thread.

        :param simPath: path to the simulation jar file
        :ptype simPath: str
        :param configPath: absolute path to the configuration file
        :ptype configPath: str
    """
    logger = logging.getLogger('Sim')
    logger.info('-- Starting simulation --')
    process = subprocess.Popen(['java', '-jar', simPath, configPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    with process.stdout:
        for line in iter(process.stdout.readline, b''):
            logger.info(line.strip().decode('utf-8'))

    process.wait()
    logger.info('-- End of the simulation')


async def main():
    if len(sys.argv) == 1:
        print('Usage: uctl2.py path_to_config_file')
        configName = 'config.json'
        if not os.path.isfile(configName) and createDefaultConfig(configName):
            print('A default configuration %s has been created' % (configName,))
        sys.exit(-1)

    configFile = os.path.abspath(sys.argv[1])
    config = None

    ch = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s - %(message)s')
    ch.setFormatter(formatter)
    logging.basicConfig(handlers=[ch], level=logging.INFO)

    logger = logging.getLogger(__name__)

    logger.info('Loading configuration %s', configFile)
    try:
        with open(configFile, 'r') as f:
            jsonConfig = json.load(f)

            config = Config.readFromJson(jsonConfig)
    except FileNotFoundError:
        logger.error('Unable to open config file %s', configFile)
        sys.exit(-1)
    except json.JSONDecodeError as e:
        logger.error('The given config file does not contain valid JSON\n-> %s', e)
        sys.exit(-1)
    
    if config is None:
        sys.exit(-1)
    
    race = readRace(config)
    notifier.race = race

    if race is False:
        sys.exit(-1)

    # Sending initial informations to the server (route, teams, segments, race infos)
    #if not sendRace(race, config['api']['baseUrl'], config['api']['actions']['setupRace']):
    #    logger.error('Unable to send initial race informations')
    #    sys.exit(-1)
    
    # Starting simulation
    Thread(target=executeSimulation, args=[config['simPath'], configFile]).start()
    await asyncio.sleep(2)

    # Starting the race file broadcasting
    async with aiohttp.ClientSession() as session:
        await broadcastRace(race, config, session)

    await notifier.stopNotifier()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(notifier.startNotifier(5678), notifier.broadcaster(), main()))
    loop.close()
