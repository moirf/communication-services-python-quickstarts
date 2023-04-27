import asyncio
import re
from typing import Self
import nest_asyncio
import uuid
import azure
import azure.communication
from azure.core.messaging import CloudEvent
from azure.communication.identity._shared.models import CommunicationIdentifier,PhoneNumberIdentifier,\
    CommunicationUserIdentifier,CommunicationIdentifierKind
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
    
    Target_number = None
    ngrok_url = None
    call_configuration: CallConfiguration = None
    calling_Automation_client: CallAutomationClient  = None
    call_connection: CallConnectionClient = None
    configuration_manager = None
    user_identity_regex: str = '8:acs:[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}_[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}'
    phone_identity_regex: str = '^\\+\\d{10,14}$'
    
    def get_identifier_kind(self, participantnumber: str):
            # checks the identity type returns as string
        if(re.search(self.user_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.COMMUNICATION_USER
        elif(re.search(self.phone_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.PHONE_NUMBER
        else:
            return CommunicationIdentifierKind.UNKNOWN
    configuration_manager = ConfigurationManager.get_instance()
    calling_Automation_client = CallAutomationClient.from_connection_string(configuration_manager.get_app_settings('Connectionstring'))
    ngrok_url =configuration_manager.get_app_settings('AppBaseUri')
    
    #call_configuration = initiate_configuration(Self,ngrok_url) 

    def __init__(self):
        Logger.log_message(Logger.INFORMATION, 'Starting ACS Sample App ')
        # Get configuration properties  
        self.app = web.Application()        
               
        self.app.add_routes([web.post('/api/call',self.run_sample)])
        self.app.add_routes([web.get('/Audio/{file_name}', self.load_file)])
        self.app.add_routes([web.post('/api/callbacks',self.start_callBack)])
        web.run_app(self.app, port=8080)
    async def program(self):
        # Start Ngrok service
        try:
            if (self.ngrok_url and len(self.ngrok_url)):
                Logger.log_message(Logger.INFORMATION,'Server started at -- > ' + self.ngrok_url)
                
                run_sample = asyncio.create_task(self.run_sample())               
                web.run_app(self.app, port=58963)
                await run_sample ;
            else:
                Logger.log_message(Logger.INFORMATION,
                                   'Failed to start Ngrok service')

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failed to start Ngrok service --> '+str(ex))

    async def run_sample(self,request):
        self.call_configuration =self.initiate_configuration(self.ngrok_url) 
        try:
            target_Id = self.configuration_manager.get_app_settings('targetIdentity')
                        
            if(target_Id and len(target_Id)):
                source_caller_id = CommunicationUserIdentifier(self.call_configuration.source_identity)
                #source_caller_id_number=CommunicationIdentifier(raw_id = call_configuration.source_identity)
                target_Identity = self.get_identifier_kind(target_Id)                
                if target_Identity == CommunicationIdentifierKind.COMMUNICATION_USER :
                    self.Target_number=CommunicationUserIdentifier(target_Id)
                    Callinvite=CallInvite(self.Target_number)                    
                if target_Identity == CommunicationIdentifierKind.PHONE_NUMBER :
                    self.Target_number=PhoneNumberIdentifier(target_Id)
                    Callinvite=CallInvite(self.Target_number,sourceCallIdNumber=PhoneNumberIdentifier(self.call_configuration.source_phone_number))                    
                              
                Logger.log_message(Logger.INFORMATION,'Performing CreateCall operation')
                self.call_connection_Response = CallAutomationClient.create_call(self.calling_Automation_client ,Callinvite,callback_uri=self.call_configuration.app_callback_url)                
                Logger.log_message(
                 Logger.INFORMATION, 'Call initiated with Call Leg id -- >' + self.call_connection_Response.call_connection.call_connection_id)
           

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failure occured while creating/establishing the call. Exception -- > ' + str(ex))

    async def start_callBack(self,request):
        try: 
             content = await request.content.read()
             event = CallAutomationEventParser.parse(content)                        
             call_Connection = self.calling_Automation_client.get_call_connection(event.call_connection_id)            
             call_Connection_Media =call_Connection.get_call_media()            
             if event.__class__ == CallConnected:
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)                
                   
                 recognize_Options = CallMediaRecognizeDtmfOptions(self.Target_number,max_tones_to_collect=1)
                 recognize_Options.interrupt_prompt = True
                 recognize_Options.inter_tone_timeout = 30                 
                 recognize_Options.initial_silence_timeout=5 
                 File_source=FileSource(uri=(self.call_configuration.app_base_url + self.call_configuration.audio_file_url))                 
                 File_source.play_source_id= 'AppointmentReminderMenu'                 
                 recognize_Options.play_prompt = File_source                
                 recognize_Options.operation_context= 'AppointmentReminderMenu'             
                 call_Connection_Media.start_recognizing(recognize_Options)
                 
             if event.__class__ == RecognizeCompleted and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'RecognizeCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 toneDetected=event.collect_tones_result.tones[0]
                 if toneDetected == DtmfTone.ONE:
                     playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Appointment_Confirmed_Audio))
                     PlayOption = call_Connection_Media.play_to_all(playSource,content='ResponseToDtmf')
                 elif toneDetected == DtmfTone.TWO :
                       playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Appointment_Cancelled_Audio))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content='ResponseToDtmf')
                 else:
                     playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Invalid_Input_Audio))
                     call_Connection_Media.play_to_all(playSource)                
                           
                 
             if event.__class__ == RecognizeFailed and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'Recognition timed out for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 playSource = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.Timed_out_Audio))
                 call_Connection_Media.play_to_all(playSource)
             if event.__class__ == PlayCompleted:
                     Logger.log_message(Logger.INFORMATION,'PlayCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True)
             if event.__class__ == PlayFailed:
                     Logger.log_message(Logger.INFORMATION,'PlayFailed event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True)            
             if event.__class__ == ParticipantsUpdated :
                 Logger.log_message(Logger.INFORMATION,'Participants Updated --> ')
             if event.__class__ == CallDisconnected :
                 Logger.log_message(Logger.INFORMATION,'Call Disconnected event received for call connection id --> ' 
                                 + event.call_connection_id) 
                 
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failed to start Audio --> ' + str(ex))
            
          
     # <summary>
        # Fetch configurations from App Settings and create source identity
        # </summary>
        # <param name='app_base_url'>The base url of the app.</param>
        # <returns>The <c CallConfiguration object.</returns>

    def initiate_configuration(self, app_base_url):
        try:
            connection_string = self.configuration_manager.get_app_settings('Connectionstring')
            source_phone_number = self.configuration_manager.get_app_settings('SourcePhone')
            Event_CallBack_Route=self.configuration_manager.get_app_settings('EventCallBackRoute')
            source_identity = self.create_user(connection_string)
            audio_file_name = self.configuration_manager.get_app_settings('AppointmentReminderMenuAudio')
            Appointment_Confirmed_Audio = self.configuration_manager.get_app_settings('AppointmentConfirmedAudio')
            Appointment_Cancelled_Audio = self.configuration_manager.get_app_settings('AppointmentCancelledAudio')
            Timed_out_Audio = self.configuration_manager.get_app_settings('TimedoutAudio')
            Invalid_Input_Audio = self.configuration_manager.get_app_settings('InvalidInputAudio')

            return CallConfiguration(connection_string, source_identity, source_phone_number, app_base_url, 
                                     audio_file_name,Event_CallBack_Route,Appointment_Confirmed_Audio,
                                     Appointment_Cancelled_Audio,Timed_out_Audio,Invalid_Input_Audio)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failed to CallConfiguration. Exception -- > ' + str(ex))
       
    # <summary>
    # Get .wav Audio file
    # </summary>
    
    async def on_incoming_request_async(self, request):
              param = request.rel_url.query
              content = await request.content.read()              
              return 'OK'
          
   
    async def load_file(self, request):
        file_name = request.match_info.get('file_name', 'Anonymous')
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


if __name__ == '__main__':
    Program()
#     nest_asyncio.apply()
#     obj = Program()
#     asyncio.run(obj.program())
    
   
    
