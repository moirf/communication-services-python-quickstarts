#from EventHandler.EventAuthHandler import EventAuthHandler


class CallConfiguration:

    def __init__(self, connection_string, source_identity, source_phone_number, app_base_url, audio_file_name,Event_CallBack_Route,Appointment_Confirmed_Audio,
                                     Appointment_Cancelled_Audio,Agent_Audio,Invalid_Input_Audio):
        self.connection_string: str = str(connection_string)
        self.source_identity: str = str(source_identity)
        self.source_phone_number: str = str(source_phone_number)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_name: str = str(audio_file_name)
        self.Appointment_Confirmed_Audio: str = str(Appointment_Confirmed_Audio)
        self.Appointment_Cancelled_Audio: str = str(Appointment_Cancelled_Audio)
        self.Agent_Audio: str = str(Agent_Audio)
        self.Invalid_Input_Audio: str = str(Invalid_Input_Audio)
        self.Event_CallBack_Route:str = str(Event_CallBack_Route)
        self.app_callback_url: str = app_base_url + Event_CallBack_Route
        self.audio_file_url: str =  audio_file_name
