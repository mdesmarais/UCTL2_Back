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


def createLoggers():
    """
        Creates loggers that are used by the simulation and the setup / race script
    """
    raceLogger = logging.getLogger('Race')
    raceLogger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
   
    formatter = logging.Formatter('[%(name)s] %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    raceLogger.addHandler(ch)

    # Creates a logger for simulation output (stdout and stderr)
    simLogger = logging.getLogger('Sim')
    simLogger.setLevel(logging.DEBUG)
    ch2 = logging.StreamHandler()
   
    formatter2 = logging.Formatter('[%(name)s] %(message)s')
    ch2.setFormatter(formatter2)
    simLogger.addHandler(ch2)


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
    print('-- Starting simulation --')
    process = subprocess.Popen(['java', '-jar', simPath, configPath], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    logger = logging.getLogger('Sim')

    with process.stdout:
        for line in iter(process.stdout.readline, b''):
            logger.error(line.strip().decode('utf-8'))

    process.wait()
    print('-- End of the simulation')


async def main():
    if len(sys.argv) == 1:
        print('Usage: uctl2.py path_to_config_file')
        configName = 'config.json'
        if not os.path.isfile(configName) and createDefaultConfig(configName):
            print('A default configuration %s has been created' % (configName,))
        sys.exit(-1)

    configFile = os.path.abspath(sys.argv[1])
    config = None

    createLoggers()

    print('Loading configuration', configFile)
    try:
        with open(configFile, 'r') as f:
            jsonConfig = json.load(f)

            config = Config.readFromJson(jsonConfig)
    except FileNotFoundError:
        print('Unable to open config file', configFile)
        sys.exit(-1)
    except json.JSONDecodeError as e:
        print('The given config file does not contain valid JSON\n->', e)
        sys.exit(-1)
    
    if config is None:
        print('Configuration error')
        sys.exit(-1)
    
    race = readRace(config)

    if race is False:
        sys.exit(-1)

    # Sending initial informations to the server (route, teams, segments, race infos)
    if not sendRace(race, config['api']['baseUrl'], config['api']['actions']['setupRace']):
        print('Unable to send initial race informations')
        sys.exit(-1)
    
    await notifier.broadcastEvent(0, None)
    
    # Starting simulation
    Thread(target=executeSimulation, args=[config['simPath'], configFile]).start()

    # Starting the race file broadcasting
    await broadcastRace(config)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(notifier.startNotifier(5678), main()))
    loop.close()