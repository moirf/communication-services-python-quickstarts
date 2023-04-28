import asyncio
import re
import nest_asyncio
import uuid
import azure
import ast
from azure.eventgrid import EventGridEvent,SystemEventNames
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
    PlayCompleted,PlayFailed
    

configuration_manager = ConfigurationManager.get_instance()
calling_Automation_client = CallAutomationClient.from_connection_string(configuration_manager.get_app_settings("Connectionstring"))
# ngrok_url =configuration_manager.get_app_settings("BaseUri")
BaseUri=configuration_manager.get_app_settings('BaseUri')
callerId = None


user_identity_regex: str = "8:acs:[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}_[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}"
phone_identity_regex: str = "^\\+\\d{10,14}$"

def get_identifier_kind(self, participantnumber: str):
         # checks the identity type returns as string
       if (re.search(self.user_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.COMMUNICATION_USER
       elif (re.search(self.phone_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.PHONE_NUMBER
       else:
            return CommunicationIdentifierKind.UNKNOWN
 
class Program():   
    
    def __init__(self):
        
        app = web.Application()
        app.add_routes([web.post('/api/incomingCall', self.run_sample)])
        app.add_routes([web.get('/Audio/{file_name}', self.load_file)])
        app.add_routes([web.post('/api/calls/{contextId}', self.start_callBack)])
        web.run_app(app, port=58963)
        
    async def run_sample(self,request):
            try:               
                self.source_identity=CommunicationUserIdentifier(configuration_manager.get_app_settings("Connectionstring"))
                content = await request.content.read()
                post_data = str(content.decode('UTF-8'))
                if post_data:
                    json_data = ast.literal_eval(json.dumps(post_data))
                    event = EventGridEvent.from_dict(ast.literal_eval(json_data)[0])
                    event_data = event.data
                    if event.event_type == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                            try:
                                subscription_validation_event = event_data
                                code = subscription_validation_event['validationCode']
                                if code:
                                    data = {"validationResponse": code}
                                    Logger.log_message(Logger.INFORMATION,
                                                    "Successfully Subscribed EventGrid.ValidationEvent --> " + str(data))
                                    return web.Response(body=str(data), status=200)
                            except Exception as ex:
                                Logger.log_message(
                                    Logger.ERROR, "Failed to Subscribe EventGrid.ValidationEvent --> " + str(ex))
                                return web.Response(text=str(ex), status=500)   
                    
                    callerId = str(event_data['from']['rawId'])                   
                    incomingCallContext = event_data['incomingCallContext']                   
                    callbackUri = BaseUri + '/api/calls/callerId='+ callerId
                    AnswerCallResult = calling_Automation_client.answer_call(incomingCallContext, callbackUri)
                    return web.Response(status=200)
            except Exception as ex:
                    Logger.log_message(
                        Logger.ERROR, "Failed to start server recording --> " + str(ex))
                    
    async def load_file(self, request):
        file_name = request.match_info.get('file_name', 'Anonymous')
        resp = web.FileResponse(f'Audio/{file_name}')
        return resp  
    
    async def start_callBack(self,request):
        try: 
             content = await request.content.read()
             event = CallAutomationEventParser.parse(content)                        
             call_Connection = calling_Automation_client.get_call_connection(event.call_connection_id)            
             call_Connection_Media =call_Connection.get_call_media()            
             if event.__class__ == CallConnected:
                 Logger.log_message(Logger.INFORMATION,'CallConnected event received for call connection id --> ' 
                                 + event.call_connection_id)                
                   
                 recognize_Options = CallMediaRecognizeDtmfOptions(callerId,max_tones_to_collect=1)
                 recognize_Options.interrupt_prompt = True
                 recognize_Options.inter_tone_timeout = 30                 
                 recognize_Options.initial_silence_timeout=5 
                 File_source=FileSource(uri=(BaseUri + configuration_manager.get_app_settings('MainMenuAudio')))                 
                 File_source.play_source_id= 'MainMenu'                 
                 recognize_Options.play_prompt = File_source                
                 recognize_Options.operation_context= 'MainMenu'             
                 call_Connection_Media.start_recognizing(recognize_Options)
                 
             if event.__class__ == RecognizeCompleted and event.operation_context == 'MainMenu' :
                 Logger.log_message(Logger.INFORMATION,'RecognizeCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 toneDetected=event.collect_tones_result.tones[0]
                 if toneDetected == DtmfTone.ONE:
                     playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('SalesAudio')))
                     PlayOption = call_Connection_Media.play_to_all(playSource,content='SimpleIVR')
                 elif toneDetected == DtmfTone.TWO :
                       playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('MarketingAudio')))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content='SimpleIVR')
                 elif toneDetected == DtmfTone.THREE :
                       playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('CustomerCareAudio')))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content='SimpleIVR')
                 elif toneDetected == DtmfTone.FOUR :
                       playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('AgentAudio')))
                       PlayOption = call_Connection_Media.play_to_all(playSource,content='AgentConnect')
                 elif toneDetected == DtmfTone.FIVE :
                      call_Connection.hang_up(True)
                 else:
                     playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('InvalidAudio')))
                     call_Connection_Media.play_to_all(playSource,content='SimpleIVR')                
                           
                 
             if event.__class__ == RecognizeFailed and event.operation_context == 'MainMenu' :
                 Logger.log_message(Logger.INFORMATION,'Recognition timed out for call connection id --> '+ event.call_connection_id
                                    +'Correlation id:'+event.correlation_id)
                 playSource = FileSource(uri=(BaseUri + configuration_manager.get_app_settings('InvalidAudio')))
                 call_Connection_Media.play_to_all(playSource,content='SimpleIVR')
             if event.__class__ == PlayCompleted:
                 
                 if event.operation_context == 'AgentConnect':
                     Participant_ToAdd = configuration_manager.get_app_settings('ParticipantToAdd')
                        
                     if(Participant_ToAdd and len(Participant_ToAdd)):                        
                          
                            Participant_Identity = get_identifier_kind(Participant_ToAdd)                
                            if Participant_Identity == CommunicationIdentifierKind.COMMUNICATION_USER :
                                self.Participant_Add=CommunicationUserIdentifier(Participant_ToAdd)
                                Callinvite=CallInvite(self.Participant_Add)                    
                            if Participant_Identity == CommunicationIdentifierKind.PHONE_NUMBER :
                                self.Participant_Add=PhoneNumberIdentifier(Participant_ToAdd)
                                Callinvite=CallInvite(self.Participant_Add,sourceCallIdNumber=self.source_identity)                    
                                        
                            Logger.log_message(Logger.INFORMATION,'Performing add Participant operation')
                            self.Addparticipant_Response=call_Connection.add_participant(Callinvite)                            
                            Logger.log_message(
                            Logger.INFORMATION, 'Call initiated with Call Leg id -- >' + self.Addparticipant_Response.participant)
                                         
                 if event.operation_context == 'SimpleIVR':
                     Logger.log_message(Logger.INFORMATION,'PlayCompleted event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True)
                     
             if event.__class__ == PlayFailed:
                     Logger.log_message(Logger.INFORMATION,'PlayFailed event received for call connection id --> '+ event.call_connection_id
                                    +'Call Connection Properties :'+event.correlation_id)
                     call_Connection.hang_up(True)           
              
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Call objects failed to get for connection id --> " + str(ex)) 
            
              

if __name__ == '__main__':
    Program()           

   