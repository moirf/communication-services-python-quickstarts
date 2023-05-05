import re
from azure.communication.identity._shared.models import CommunicationIdentifier,PhoneNumberIdentifier,\
    CommunicationUserIdentifier,CommunicationIdentifierKind,identifier_from_raw_id
import json
from aiohttp import web
from Logger import Logger
from ConfigurationManager import ConfigurationManager,CallConfiguration
from azure.communication.callautomation import CallAutomationClient,CallInvite,\
CallAutomationEventParser,CallConnected,CallMediaRecognizeDtmfOptions,\
CallConnectionClient,CallDisconnected,PlaySource,FileSource,ParticipantsUpdated,DtmfTone,\
RecognizeCanceled,RecognizeCompleted,RecognizeFailed,PlayCompleted,PlayFailed     

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
    ngrok_url =configuration_manager.get_app_settings('App_base_uri')
    
    def __init__(self):
        Logger.log_message(Logger.INFORMATION, 'Starting ACS Sample App ')
        # Get configuration properties  
        self.app = web.Application()        
        self.app.add_routes([web.post('/api/call',self.run_sample)])
        self.app.add_routes([web.get('/audio/{file_name}', self.load_file)])
        self.app.add_routes([web.post('/api/callbacks/{contextId}',self.start_callBack)])
        web.run_app(self.app, port=58963)
        
    async def run_sample(self,request):
        self.call_configuration =self.initiate_configuration(self.ngrok_url) 
        try:
            target_Ids = self.configuration_manager.get_app_settings('TargetIdentity') 
            Target_Identities= target_Ids.split(';')
            for target_Id in Target_Identities :                       
                if(target_Id and len(target_Id)):  
                    Target_number= target_Id            
                    target_Identity = self.get_identifier_kind(target_Id)                
                    if target_Identity == CommunicationIdentifierKind.COMMUNICATION_USER :                        
                        Callinvite=CallInvite(CommunicationUserIdentifier(target_Id))                    
                    if target_Identity == CommunicationIdentifierKind.PHONE_NUMBER :                        
                        Callinvite=CallInvite(PhoneNumberIdentifier(target_Id),sourceCallIdNumber=PhoneNumberIdentifier(self.call_configuration.source_phone_number))                    
                    call_back_url= self.call_configuration.app_callback_url+'/Target_number=? ' + Target_number   
                    Logger.log_message(Logger.INFORMATION,'Performing CreateCall operation')
                    self.call_connection_Response = CallAutomationClient.create_call(self.calling_Automation_client ,Callinvite,callback_uri=call_back_url)                
                    Logger.log_message(
                    Logger.INFORMATION, 'Call initiated with Call Leg id -- >' + self.call_connection_Response.call_connection.call_connection_id)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failure occured while creating/establishing the call. Exception -- > ' + str(ex))

    async def start_callBack(self,request):
        try: 
             target_id_comm=None
             target_id=self.Target_number
             if(target_id and len(target_id)):
                target_Identity = self.get_identifier_kind(target_id)                
                if target_Identity == CommunicationIdentifierKind.COMMUNICATION_USER :                        
                            target_id_comm=CommunicationUserIdentifier(target_id)                   
                if target_Identity == CommunicationIdentifierKind.PHONE_NUMBER : 
                        target_id_comm=PhoneNumberIdentifier(target_id)
             content = await request.content.read()
             event = CallAutomationEventParser.parse(content)                        
             call_Connection = self.calling_Automation_client.get_call_connection(event.call_connection_id)            
             call_Connection_Media =call_Connection.get_call_media()            
             if event.__class__ == CallConnected:
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)
                 recognize_Options = CallMediaRecognizeDtmfOptions(target_id_comm,max_tones_to_collect=1)
                 recognize_Options.interrupt_prompt = True
                 recognize_Options.inter_tone_timeout = 60                 
                 recognize_Options.initial_silence_timeout=10 
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
                Logger.ERROR, 'Failed to get recognize Options . --> ' + str(ex))
            
          
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
            audio_file_name = self.configuration_manager.get_app_settings('AppointmentReminderMenuAudio')
            Appointment_Confirmed_Audio = self.configuration_manager.get_app_settings('AppointmentConfirmedAudio')
            Appointment_Cancelled_Audio = self.configuration_manager.get_app_settings('AppointmentCancelledAudio')
            Timed_out_Audio = self.configuration_manager.get_app_settings('TimedoutAudio')
            Invalid_Input_Audio = self.configuration_manager.get_app_settings('InvalidInputAudio')

            return CallConfiguration(connection_string, source_phone_number, app_base_url, 
                                     audio_file_name,Event_CallBack_Route,Appointment_Confirmed_Audio,
                                     Appointment_Cancelled_Audio,Timed_out_Audio,Invalid_Input_Audio)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failed to CallConfiguration. Exception -- > ' + str(ex))
       
    # <summary>
    # Get .wav Audio file
    # </summary>
    async def load_file(self, request):
        file_name = request.match_info.get('file_name', 'Anonymous')
        resp = web.FileResponse(f'Audio/{file_name}')
        return resp