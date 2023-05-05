import configparser
class ConfigurationManager:
    __configuration = None
    __instance = None   

    def __init__(self):
        if(self.__configuration == None):            
            self.__configuration = configparser.ConfigParser()
            self.__configuration.read('config.ini')

    @staticmethod
    def get_instance():
       
        if(ConfigurationManager.__instance == None):
            ConfigurationManager.__instance = ConfigurationManager()
        return ConfigurationManager.__instance

    def get_app_settings(self, key):
        if (key != None):
            return self.__configuration.get("DEFAULT", key)
        return None
    
class CallConfiguration:
    
    def __init__(self, connection_string,source_phone_number, app_base_url, audio_file_name,event_callback_route,appointment_confirmed_audio,
                                     appointment_cancelled_audio,timed_out_audio,invalid_input_audio):
        self.connection_string: str = str(connection_string)
        #self.source_identity: str = str(source_identity)
        self.source_phone_number: str = str(source_phone_number)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_name: str = str(audio_file_name)
        self.appointment_confirmed_audio: str = str(appointment_confirmed_audio)
        self.appointment_cancelled_audio: str = str(appointment_cancelled_audio)
        self.timed_out_audio: str = str(timed_out_audio)
        self.invalid_input_audio: str = str(invalid_input_audio)
        self.event_callback_route:str = str(event_callback_route)
        self.app_callback_url: str = app_base_url + event_callback_route
        self.audio_file_url: str =  audio_file_name