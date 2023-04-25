#from EventHandler.EventAuthHandler import EventAuthHandler


class CallConfiguration:

    def __init__(self, connection_string, source_identity, source_phone_number, app_base_url, audio_file_name,Event_CallBack_Route):
        self.connection_string: str = str(connection_string)
        self.source_identity: str = str(source_identity)
        self.source_phone_number: str = str(source_phone_number)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_name: str = str(audio_file_name)
        self.Event_CallBack_Route:str = str(Event_CallBack_Route)
        self.app_callback_url: str = app_base_url + Event_CallBack_Route
        self.audio_file_url: str = app_base_url + audio_file_name
