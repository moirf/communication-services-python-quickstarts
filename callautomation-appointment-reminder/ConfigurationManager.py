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
    
    def __init__(self, connection_string,source_phone_number, app_base_url, audio_file_name,Event_CallBack_Route,Appointment_Confirmed_Audio,
                                     Appointment_Cancelled_Audio,Timed_out_Audio,Invalid_Input_Audio):
        self.connection_string: str = str(connection_string)
        #self.source_identity: str = str(source_identity)
        self.source_phone_number: str = str(source_phone_number)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_name: str = str(audio_file_name)
        self.Appointment_Confirmed_Audio: str = str(Appointment_Confirmed_Audio)
        self.Appointment_Cancelled_Audio: str = str(Appointment_Cancelled_Audio)
        self.Timed_out_Audio: str = str(Timed_out_Audio)
        self.Invalid_Input_Audio: str = str(Invalid_Input_Audio)
        self.Event_CallBack_Route:str = str(Event_CallBack_Route)
        self.app_callback_url: str = app_base_url + Event_CallBack_Route
        self.audio_file_url: str =  audio_file_name