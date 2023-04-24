import asyncio
import nest_asyncio
import uuid
import azure
import azure.communication
import azure.communication.callautomation
from azure.core.messaging import CloudEvent
from azure.communication.identity._shared.models import CommunicationIdentifier,PhoneNumberIdentifier, CommunicationUserIdentifier
from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
import json
from aiohttp import web
from Logger import Logger
from ConfigurationManager import ConfigurationManager
from CallConfiguration import CallConfiguration
from Ngrok.NgrokService import NgrokService
from azure.communication.identity import CommunicationIdentityClient
from AppointmentCallReminder import AppointmentCallReminder
from Controller.RemainderCallController import RemainderCallController
from azure.communication.callautomation import CallAutomationClient,CallInvite,\
CallAutomationEventParser,CallConnected,CallMediaRecognizeOptions,CallMediaRecognizeDtmfOptions,\
    CallConnectionClient,CallDisconnected
class Program(): 
    app = web.Application() 
    call_configuration: CallConfiguration = None
    calling_Automation_client: CallAutomationClient  = None
    call_connection: CallConnectionClient = None 
    
    call_connected_task: asyncio.Future = None
    play_audio_completed_task: asyncio.Future = None
    call_terminated_task: asyncio.Future = None
    tone_received_complete_task: asyncio.Future = None
    add_participant_complete_task: asyncio.Future = None
    max_retry_attempt_count: int = None
     
    configuration_manager = None
    __ngrok_service = None
    url = "http://localhost:8080"
    target = None
    
    async def start_callBbak(request):
        try:
             #param = request.rel_url.query
             param = request.call_connection_Response
             #content = await request.content.read()
             content = await request.
             #event = CloudEvent.from_dict(json.loads(contant)[0])
             event = CallAutomationEventParser.parse(param)
             call_Connection = CallAutomationClient.from_connection_string(event.call_Connection.call_connection_id)            
             call_Connection_Media =call_Connection._call_media            
             if event.type == CallConnected:
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)
             # recognize_Options=CallMediaRecognizeDtmfOptions(CommunicationIdentifier.raw_id(target))

          
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start server recording --> " + str(ex))
            
          

    def __init__(self):
        Logger.log_message(Logger.INFORMATION, "Starting ACS Sample App ")
        # Get configuration properties
        self.configuration_manager = ConfigurationManager.get_instance()        
        self.max_retry_attempt_count: int = int(ConfigurationManager.get_instance().get_app_settings("MaxRetryCount"))
        self.calling_Automation_client = CallAutomationClient.from_connection_string(self.configuration_manager.get_app_settings("Connectionstring"))
        self.app.add_routes([web.post('/api/call',(self.on_incoming_request_async))])
        self.app.add_routes([web.get("/audio/{file_name}", self.load_file)])
        self.app.add_routes([web.post('/api/callbacks',self.start_callBbak)])

    async def program(self):
        # Start Ngrok service
        ngrok_url = self.start_ngrok_service()
        #ngrok_url = "https://61a5-103-70-129-182.ngrok.io"
        try:
            if (ngrok_url and len(ngrok_url)):
                Logger.log_message(Logger.INFORMATION,"Server started at -- > " + self.url)
                run_sample = asyncio.create_task(self.run_sample(ngrok_url)) 
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.start_callBbak())
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
           ngrokPath = self.configuration_manager.get_app_settings("NgrokExePath")

           if (not(len(ngrokPath))):
                  Logger.log_message(Logger.INFORMATION,
                                   "Ngrok path not provided")
                  return None
 
           Logger.log_message(Logger.INFORMATION, "Starting Ngrok")
           self.__ngrok_service = NgrokService(ngrokPath, None)

           Logger.log_message(Logger.INFORMATION, "Fetching Ngrok Url")
           ngrok_url = self.__ngrok_service.get_ngrok_url()
           ngrok_url  = self.configuration_manager.get_app_settings("AppBaseUri")        
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
            Target_Phone_Number = self.configuration_manager.get_app_settings("TargetPhoneNumber")            
            if(Target_Phone_Number and len(Target_Phone_Number)):
               source = CommunicationUserIdentifier(call_configuration.source_identity)
               targets = CommunicationUserIdentifier(Target_Phone_Number) 
               target=targets;
               Callinvite=CallInvite(targets)
               Logger.log_message(Logger.INFORMATION,"Performing CreateCall operation")
               self.call_connection_Response = CallAutomationClient.create_call(self.calling_Automation_client ,Callinvite,callback_uri=call_configuration.app_callback_url)                
               Logger.log_message(
                Logger.INFORMATION, "Call initiated with Call Leg id -- >" + self.call_connection_Response.call_connection.call_connection_id)
            # self.register_to_callstate_change_event(self.call_connection.call_connection_id)

            # await self.call_connected_task

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failure occured while creating/establishing the call. Exception -- > " + str(ex))

        # self.delete_user(call_configuration.connection_string,
        #                  call_configuration.source_identity)


    
        # <summary>
        # Fetch configurations from App Settings and create source identity
        # </summary>
        # <param name="app_base_url">The base url of the app.</param>
        # <returns>The <c CallConfiguration object.</returns>

    def initiate_configuration(self, app_base_url):
        try:
            connection_string = self.configuration_manager.get_app_settings(
                "Connectionstring")
            source_phone_number = self.configuration_manager.get_app_settings(
                "SourcePhone")

            source_identity = self.create_user(connection_string)
            audio_file_name = self.generate_custom_audio_message()

            return CallConfiguration(connection_string, source_identity, source_phone_number, app_base_url, audio_file_name)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to CallConfiguration. Exception -- > " + str(ex))
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



    async def on_incoming_request_async(self, request):
              param = request.rel_url.query
              content = await request.content.read()              
              return "OK"
          
   
    async def load_file(self, request):
        file_name = request.match_info.get('file_name', "Anonymous")
        resp = web.FileResponse(f'audio/{file_name}')
        return resp
        web.run_app(self.app, port=8080)
          
          
    def create_user(self, connection_string):
        client = CommunicationIdentityClient.from_connection_string(
            connection_string)
        user: CommunicationIdentifier = client.create_user()
        return user.properties.get('id')
     # <summary>
    # Delete the user
    # </summary>

    def delete_user(self, connection_string, source):
        client = CommunicationIdentityClient.from_connection_string(
            connection_string)
        user = CommunicationUserIdentifier(source)
        client.delete_user(user)


if __name__ == "__main__":
    nest_asyncio.apply()
    obj = Program()
    asyncio.run(obj.program())
    
    
    def CallUri():
     app = web.Application()    

    
