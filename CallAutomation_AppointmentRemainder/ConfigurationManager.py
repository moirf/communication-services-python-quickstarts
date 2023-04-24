import configparser
class ConfigurationManager:
    __configuration = None
    __instance = None
    _configpath=None

    def __init__(self):
        if(self.__configuration == None):
            _configpath = 'C:/Users/v-raniv/Desktop/Git_project/April/python/communication-services-python-quickstarts/CallAutomation_AppointmentRemainder/config.ini'           
            self.__configuration = configparser.ConfigParser()
            self.__configuration.read(_configpath)

    @staticmethod
    def get_instance():
       
        if(ConfigurationManager.__instance == None):
            ConfigurationManager.__instance = ConfigurationManager()
        return ConfigurationManager.__instance

    def get_app_settings(self, key):
        if (key != None):
            return self.__configuration.get("DEFAULT", key)
        return None
