import asyncio
import re
import nest_asyncio
import uuid
import azure
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
ngrok_url =configuration_manager.get_app_settings("AppBaseUri")

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
 
class InboundCallAutomationController():

    recFileFormat = ''

    def __init__(self):
        app = web.Application()
        app.add_routes([web.get("/api/incomingCall", self.run_sample)])
        app.add_routes([web.get("/startRecordingWithOptions", self.load_file)])
        app.add_routes([web.get("/api/calls/{contextId}", self.start_callBack)])
        web.run_app(app, port=58963)
        
    async def run_sample(request):
        try:
            
            content = await request.content.read()
            event = CallAutomationEventParser.parse(content)
            if event._class=="":
             Logger.log_message(
                Logger.ERROR, "Failed to start server recording --> " )
             
            
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start server recording --> " + str(ex))
           

   