import re
from azure.communication.identity._shared.models import CommunicationIdentifier,PhoneNumberIdentifier,\
    CommunicationUserIdentifier,CommunicationIdentifierKind,identifier_from_raw_id
import json
from aiohttp import web
from Logger import Logger
from urllib.parse import urlencode
from ConfigurationManager import ConfigurationManager,CallConfiguration
from azure.communication.callautomation import CallAutomationClient,CallInvite,\
CallAutomationEventParser,CallConnected,CallMediaRecognizeDtmfOptions,\
CallConnectionClient,CallDisconnected,PlaySource,FileSource,ParticipantsUpdated,DtmfTone,\
RecognizeCanceled,RecognizeCompleted,RecognizeFailed,PlayCompleted,PlayFailed     

class Program():     
    target_number = None
    ngrok_url = None
    call_configuration: CallConfiguration = None
    calling_automation_client: CallAutomationClient  = None
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
    calling_automation_client = CallAutomationClient.from_connection_string(configuration_manager.get_app_settings('Connectionstring'))
    ngrok_url =configuration_manager.get_app_settings('app_base_uri')
    targets_identifiers= {}; 

    def __init__(self):
        Logger.log_message(Logger.INFORMATION, 'Starting ACS Sample App ')
        # Get configuration properties  
        self.app = web.Application()        
        self.app.add_routes([web.post('/api/call',self.run_sample)])
        self.app.add_routes([web.get('/audio/{file_name}', self.load_file)])
        self.app.add_routes([web.post('/api/callbacks',self.start_callBack)])
        web.run_app(self.app, port=8080)
    
    async def run_sample(self,request):
        self.call_configuration =self.initiate_configuration(self.ngrok_url) 
        try:
            target_ids = self.configuration_manager.get_app_settings('TargetIdentity') 
            Target_identities= target_ids.split(';')
            for target_id in Target_identities :                       
                if(target_id and len(target_id)):            
                    target_Identity = self.get_identifier_kind(target_id)                
                    if target_Identity == CommunicationIdentifierKind.COMMUNICATION_USER :                        
                        Callinvite=CallInvite(CommunicationUserIdentifier(target_id))                    
                    if target_Identity == CommunicationIdentifierKind.PHONE_NUMBER :                        
                        Callinvite=CallInvite(PhoneNumberIdentifier(target_id),sourceCallIdNumber=PhoneNumberIdentifier(self.call_configuration.source_phone_number))                    
                    call_back_url= self.call_configuration.app_callback_url 
                    Logger.log_message(Logger.INFORMATION,'Performing CreateCall operation')
                    self.call_connection_response = CallAutomationClient.create_call(self.calling_automation_client ,Callinvite,callback_uri=call_back_url)
                    self.targets_identifiers[self.call_connection_response.call_connection.call_connection_id] = target_id;                
                    Logger.log_message(
                    Logger.INFORMATION, 'Call initiated with Call Leg id -- >' + self.call_connection_response.call_connection.call_connection_id)
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, 'Failure occured while creating/establishing the call. Exception -- > ' + str(ex))

    async def start_callBack(self,request):
        try: 
             _content = await request.content.read()
             event = CallAutomationEventParser.parse(_content)                        
             call_connection = self.calling_automation_client.get_call_connection(event.call_connection_id)            
             call_connection_media =call_connection.get_call_media()            
             if event.__class__ == CallConnected:
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)
                 recognize_options = CallMediaRecognizeDtmfOptions(identifier_from_raw_id(self.targets_identifiers[event.call_connection_id]),max_tones_to_collect=1)
                 recognize_options.interrupt_prompt = True
                 recognize_options.inter_tone_timeout = 10                 
                 recognize_options.initial_silence_timeout=5 
                 File_source=FileSource(uri=(self.call_configuration.app_base_url + self.call_configuration.audio_file_name))                 
                 File_source.play_source_id= 'AppointmentReminderMenu'                 
                 recognize_options.play_prompt = File_source                
                 recognize_options.operation_context= 'AppointmentReminderMenu'             
                 call_connection_media.start_recognizing(recognize_options)
             if event.__class__ == RecognizeCompleted and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'RecognizeCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 toneDetected=event.collect_tones_result.tones[0]
                 if toneDetected == DtmfTone.ONE:
                     play_Source = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.appointment_confirmed_audio))
                     call_connection_media.play_to_all(play_Source,content='ResponseToDtmf')
                 elif toneDetected == DtmfTone.TWO :
                       play_Source = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.appointment_cancelled_audio))
                       call_connection_media.play_to_all(play_Source,content='ResponseToDtmf')
                 else:
                     play_Source = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.invalid_input_audio))
                     call_connection_media.play_to_all(play_Source) 
                 
             if event.__class__ == RecognizeFailed and event.operation_context == 'AppointmentReminderMenu' :
                 Logger.log_message(Logger.INFORMATION,'Recognition timed out for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 play_Source = FileSource(uri=(self.call_configuration.app_base_url+self.call_configuration.timed_out_audio))
                 call_connection_media.play_to_all(play_Source)
             if event.__class__ == PlayCompleted:
                     Logger.log_message(Logger.INFORMATION,'PlayCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_connection.hang_up(True)
             if event.__class__ == PlayFailed:
                     Logger.log_message(Logger.INFORMATION,'PlayFailed event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_connection.hang_up(True)            
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
            connection_string = self.configuration_manager.get_app_settings('connectionstring')
            source_phone_number = self.configuration_manager.get_app_settings('Sourcephone')
            event_callback_route=self.configuration_manager.get_app_settings('eventcallbackroute')
            audio_file_name = self.configuration_manager.get_app_settings('appointmentremindermenuaudio')
            appointment_confirmed_audio = self.configuration_manager.get_app_settings('appointmentconfirmedaudio')
            appointment_cancelled_audio = self.configuration_manager.get_app_settings('appointmentcancelledaudio')
            timed_out_audio = self.configuration_manager.get_app_settings('timedoutaudio')
            invalid_input_audio = self.configuration_manager.get_app_settings('invalidinputaudio')

            return CallConfiguration(connection_string, source_phone_number, app_base_url, 
                                     audio_file_name,event_callback_route,appointment_confirmed_audio,
                                     appointment_cancelled_audio,timed_out_audio,invalid_input_audio)
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
    
if __name__ == '__main__':
    Program()