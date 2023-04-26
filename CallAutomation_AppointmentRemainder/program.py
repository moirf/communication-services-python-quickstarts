import asyncio
import nest_asyncio
import uuid
import azure
import azure.communication
from azure.core.messaging import CloudEvent
from azure.communication.identity._shared.models import CommunicationIdentifier,PhoneNumberIdentifier, CommunicationUserIdentifier
from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
import json
from aiohttp import web
from Logger import Logger
from ConfigurationManager import ConfigurationManager
from CallConfiguration import CallConfiguration
from azure.communication.identity import CommunicationIdentityClient
from azure.communication.callautomation import CallAutomationClient,CallInvite,\
CallAutomationEventParser,CallConnected,CallMediaRecognizeOptions,CallMediaRecognizeDtmfOptions,\
CallConnectionClient,CallDisconnected,PlaySource,FileSource,ParticipantsUpdated,DtmfTone,\
RecognizeCanceled,RecognizeCompleted,RecognizeFailed,AddParticipantFailed,AddParticipantSucceeded,\
    PlayCompleted,PlayFailed,RemoveParticipantSucceeded,RemoveParticipantFailed
    
    
class Program(): 
    app = web.Application() 
    Target_number = None
    ngrok_url = None
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
    def __init__(self):
        Logger.log_message(Logger.INFORMATION, "Starting ACS Sample App ")
        # Get configuration properties
        app = web.Application() 
        self.configuration_manager = ConfigurationManager.get_instance()        
        self.max_retry_attempt_count: int = int(ConfigurationManager.get_instance().get_app_settings("MaxRetryCount"))
        self.calling_Automation_client = CallAutomationClient.from_connection_string(self.configuration_manager.get_app_settings("Connectionstring"))
        self.ngrok_url =self.configuration_manager.get_app_settings("AppBaseUri")
        self.call_configuration = self.initiate_configuration(self.ngrok_url)        
        self.app.add_routes([web.post('/api/call',(self.on_incoming_request_async))])
        self.app.add_routes([web.get("/Audio/{file_name}", self.load_file)])
        self.app.add_routes([web.post('/api/callbacks',self.start_callBack)])

    async def program(self):
        # Start Ngrok service
        try:
            if (self.ngrok_url and len(self.ngrok_url)):
                Logger.log_message(Logger.INFORMATION,"Server started at -- > " + self.ngrok_url)
                
                run_sample = asyncio.create_task(self.run_sample(self.call_configuration))               
                web.run_app(self.app, port=58963)
                await run_sample ;
            else:
                Logger.log_message(Logger.INFORMATION,
                                   "Failed to start Ngrok service")

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start Ngrok service --> "+str(ex))

    async def run_sample(self, call_configuration):
        
        try:
            Target_Phone_Number = self.configuration_manager.get_app_settings("TargetPhoneNumber")
                        
            if(Target_Phone_Number and len(Target_Phone_Number)):
               source = CommunicationUserIdentifier(call_configuration.source_identity)
               targets = CommunicationUserIdentifier(Target_Phone_Number) 
            #    source = PhoneNumberIdentifier(call_configuration.source_identity)
            #    targets = PhoneNumberIdentifier(Target_Phone_Number)
               self.Target_number=targets;
               Callinvite=CallInvite(targets)
               #Callinvite.sourceCallIdNumber=source
               Logger.log_message(Logger.INFORMATION,"Performing CreateCall operation")
               self.call_connection_Response = CallAutomationClient.create_call(self.calling_Automation_client ,Callinvite,callback_uri=call_configuration.app_callback_url)                
               Logger.log_message(
                Logger.INFORMATION, "Call initiated with Call Leg id -- >" + self.call_connection_Response.call_connection.call_connection_id)
           

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failure occured while creating/establishing the call. Exception -- > " + str(ex))

    async def start_callBack(self,request):
        try: 
             content = await request.content.read()
             event = CallAutomationEventParser.parse(content) 
             Logger.log_message(Logger.INFORMATION,' event Kind  --> '+ event.kind)
                         
             call_Connection = self.calling_Automation_client.get_call_connection(event.call_connection_id)            
             call_Connection_Media =call_Connection.get_call_media()            
             if event.kind == 'CallConnected' :
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)                
                   
                 recognize_Options = CallMediaRecognizeDtmfOptions(self.Target_number,max_tones_to_collect=1)
                 recognize_Options.interrupt_prompt = True
                 recognize_Options.inter_tone_timeout = 10
                 recognize_Options.initial_silence_timeout=5                  
                 #recognize_Options.play_prompt = FileSource(uri=(self.call_configuration.app_base_url + self.call_configuration.audio_file_url))                 
                 File_source=FileSource(uri=(self.call_configuration.app_base_url + self.call_configuration.audio_file_url))                 
                 File_source.play_source_id= "AppointmentReminderMenu"                 
                 recognize_Options.play_prompt = File_source                
                 recognize_Options.operation_context= "AppointmentReminderMenu"             
                 call_Connection_Media.start_recognizing(recognize_Options)
                 
             if event.kind == 'RecognizeCompleted' and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'RecognizeCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 toneDetected=event.collect_tones_result.tones[0]
                 if toneDetected == DtmfTone.ONE:
                     playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Appointment_Confirmed_Audio))
                     PlayOption = call_Connection_Media.play_to_all(playSource,content="ResponseToDtmf")
                 elif toneDetected == DtmfTone.TWO :
                       playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Appointment_Cancelled_Audio))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content="ResponseToDtmf")
                 elif toneDetected == DtmfTone.THREE :
                       playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Agent_Audio))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content="AgentConnect")
                 else:
                     playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Invalid_Input_Audio))
                     call_Connection_Media.play_to_all(playSource)
                 
                           
                 
             if event.kind == 'RecognizeFailed' and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'RecognizeFailed event received for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id) 
             if event.kind == 'PlayCompleted':
                     Logger.log_message(Logger.INFORMATION,'PlayCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True)
             if event.kind == 'PlayFailed':
                     Logger.log_message(Logger.INFORMATION,'PlayFailed event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True) 
             if event.kind == 'AddParticipantSucceeded' :
                  Logger.log_message(Logger.INFORMATION,'participant added --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)               
             if event.kind == 'AddParticipantFailed' :
                   Logger.log_message(Logger.INFORMATION,'Failed participant Reason --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id) 
             if event.kind == 'ParticipantsUpdated' :
                 Logger.log_message(Logger.INFORMATION,'Participants Updated --> ')
                                    
             
             
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start Audio --> " + str(ex))
            
          
    
        # <summary>
        # Fetch configurations from App Settings and create source identity
        # </summary>
        # <param name="app_base_url">The base url of the app.</param>
        # <returns>The <c CallConfiguration object.</returns>

    def initiate_configuration(self, app_base_url):
        try:
            connection_string = self.configuration_manager.get_app_settings("Connectionstring")
            source_phone_number = self.configuration_manager.get_app_settings("SourcePhone")
            Event_CallBack_Route=self.configuration_manager.get_app_settings("EventCallBackRoute")
            source_identity = self.create_user(connection_string)
            audio_file_name = self.configuration_manager.get_app_settings("AppointmentReminderMenuAudio")
            Appointment_Confirmed_Audio = self.configuration_manager.get_app_settings("AppointmentConfirmedAudio")
            Appointment_Cancelled_Audio = self.configuration_manager.get_app_settings("AppointmentCancelledAudio")
            Agent_Audio = self.configuration_manager.get_app_settings("AgentAudio")
            Invalid_Input_Audio = self.configuration_manager.get_app_settings("InvalidInputAudio")

            return CallConfiguration(connection_string, source_identity, source_phone_number, app_base_url, 
                                     audio_file_name,Event_CallBack_Route,Appointment_Confirmed_Audio,
                                     Appointment_Cancelled_Audio,Agent_Audio,Invalid_Input_Audio)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to CallConfiguration. Exception -- > " + str(ex))
    # <summary>
    # Get .wav Audio file
    # </summary>
    
    async def on_incoming_request_async(self, request):
              param = request.rel_url.query
              content = await request.content.read()              
              return "OK"
          
   
    async def load_file(self, request):
        file_name = request.match_info.get('file_name', "Anonymous")
        resp = web.FileResponse(f'Audio/{file_name}')
        return resp
       # web.run_app(self.app, port=8080)
          
          
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
    
   
    
