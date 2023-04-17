# import asyncio
# import nest_asyncio
# from azure.communication.identity._shared.models import CommunicationIdentifier, CommunicationUserIdentifier
# from Controller.OutboundCallController import OutboundCallController
# from Logger import Logger
# from ConfigurationManager import ConfigurationManager
# from CallConfiguration import CallConfiguration
# from Ngrok.NgrokService import NgrokService
# from azure.communication.identity import CommunicationIdentityClient
# from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
# from callautomation import OutboundCallReminder

import asyncio
import nest_asyncio
import azure
import azure.communication
import azure.communication.callautomation
from azure.core.messaging import CloudEvent
from CallAutomation_AppointmentRemainder import CallAutomation_AppointmentRemainder
from azure.communication.identity._shared.models import CommunicationIdentifier, CommunicationUserIdentifier
from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
import json
from aiohttp import web
from Logger import Logger
from ConfigurationManager import ConfigurationManager
from CallConfiguration import CallConfiguration
from Ngrok.NgrokService import NgrokService
from azure.communication.identity import CommunicationIdentityClient


class Program():
    builder = web.create
    configuration_manager = None
    __ngrok_service = None
    url = "http://localhost:9007"

    def __init__(self):
        Logger.log_message(Logger.INFORMATION, "Starting ACS Sample App ")
        # Get configuration properties
        self.configuration_manager = ConfigurationManager.get_instance()

    async def program(self):
        # Start Ngrok service
        ngrok_url = self.start_ngrok_service()

        try:
            if (ngrok_url and len(ngrok_url)):
                Logger.log_message(Logger.INFORMATION,"Server started at -- > " + self.url)
                run_sample = asyncio.create_task(self.run_sample(ngrok_url))                
                await run_sample

            else:
                Logger.log_message(Logger.INFORMATION,
                                   "Failed to start Ngrok service")

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start Ngrok service --> "+str(ex))

        Logger.log_message(Logger.INFORMATION,
                           "Press 'Ctrl + C' to exit the sample")
        self.__ngrok_service.dispose()

    def start_ngrok_service(self):
        try:
            ngrokPath = self.configuration_manager.get_app_settings(
                "NgrokExePath")

            if (not(len(ngrokPath))):
                Logger.log_message(Logger.INFORMATION,
                                   "Ngrok path not provided")
                return None

            Logger.log_message(Logger.INFORMATION, "Starting Ngrok")
            self.__ngrok_service = NgrokService(ngrokPath, None)

            Logger.log_message(Logger.INFORMATION, "Fetching Ngrok Url")
            ngrok_url = self.__ngrok_service.get_ngrok_url()

            Logger.log_message(Logger.INFORMATION,
                               "Ngrok Started with url -- > " + ngrok_url)
            return ngrok_url

        except Exception as ex:
            Logger.log_message(Logger.INFORMATION,
                               "Ngrok service got failed -- > " + str(ex))
            return None

    async def run_sample(self, app_base_url):
        call_configuration = self.initiate_configuration(app_base_url)
        try:
            outbound_call_pairs = self.configuration_manager.get_app_settings(
                "DestinationIdentities")

            if (outbound_call_pairs and len(outbound_call_pairs)):
                identities = outbound_call_pairs.split(";")
                tasks = []
                for identity in identities:
                    pair = identity.split(",")
                    task = asyncio.ensure_future(AppointmentCallReminder(
                        call_configuration).report(pair[0].strip(), pair[1].strip()))
                    tasks.append(task)

                _ = await asyncio.gather(*tasks)

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to initiate the outbound call Exception -- > " + str(ex))

        self.delete_user(call_configuration.connection_string,
                         call_configuration.source_identity)

        # <summary>
        # Fetch configurations from App Settings and create source identity
        # </summary>
        # <param name="app_base_url">The base url of the app.</param>
        # <returns>The <c CallConfiguration object.</returns>

    def initiate_configuration(self, app_base_url):
        connection_string = self.configuration_manager.get_app_settings(
            "Connectionstring")
        source_phone_number = self.configuration_manager.get_app_settings(
            "SourcePhone")

        source_identity = self.create_user(connection_string)
        audio_file_name = self.generate_custom_audio_message()

        return CallConfiguration(connection_string, source_identity, source_phone_number, app_base_url, audio_file_name)

    # <summary>
    # Get .wav Audio file
    # </summary>

    def generate_custom_audio_message(self):
        configuration_manager = ConfigurationManager()
        key = configuration_manager.get_app_settings("CognitiveServiceKey")
        region = configuration_manager.get_app_settings(
            "CognitiveServiceRegion")
        custom_message = configuration_manager.get_app_settings(
            "CustomMessage")

        try:
            if (key and len(key) and region and len(region) and custom_message and len(custom_message)):

                config = SpeechConfig(subscription=key, region=region)
                config.set_speech_synthesis_output_format(
                    SpeechSynthesisOutputFormat["Riff24Khz16BitMonoPcm"])

                synthesizer = SpeechSynthesizer(SpeechSynthesizer=config)

                result = synthesizer.speak_text_async(custom_message).get()
                stream = AudioDataStream(result)
                stream.save_to_wav_file("/audio/custom-message.wav")

                return "custom-message.wav"

            return "sample-message.wav"
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Exception while generating text to speech, falling back to sample audio. Exception -- > " + str(ex))
            return "sample-message.wav"

    


if __name__ == "__main__":
    nest_asyncio.apply()
    obj = Program()
    asyncio.run(obj.program())
    
    
    def CallUri():
     app = web.Application()
     builder = webapplication.ConfigParser(defaults=None, dict_type=collections.OrderedDict, allow_no_value=False, delimiters=, '=', ':')

    def __init__(self):
        self.app.add_routes(
            [web.post('/api/call', self.on_outbound_request_async)])
        self.app.add_routes([web.get("/Audio/{file_name}", self.load_file)])
        web.run_app(self.app, port=9007)

    async def on_outbound_request_async(self, request):
        param = request.rel_url.query
        content = await request.content.read()

       

    async def load_file(self, request):
        file_name = request.match_info.get('file_name', "Anonymous")
        resp = web.FileResponse(f'Audio/{file_name}')
        return resp
