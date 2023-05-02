---
page_type: sample
languages:
- python
products:
- azure
- azure-communication-services
---

# Appointment Reminder Call Sample

This sample application shows how the Azure Communication Services Server, Calling package can be used to build IVR related solutions. This sample makes an outbound call to a phone number or a communication identifier and plays an audio message. If the callee presses 1 (tone1), to reschedule an appointment, then leaves the call.If the callee presses 2(tone2) cancell an appointment,then leave the call. If the callee presses  any other key then the application ends the call.
The application is a console based application build using Python 3.9.

## Getting started

### Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- [Python](https://www.python.org/downloads/) 3.9 and above
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- Get a phone number for your new Azure Communication Services resource. For details, see [Get a phone number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=platform-azp)
- Download and install [Ngrok](https://www.ngrok.com/download). As the sample is run locally, Ngrok will enable the receiving of all the events.
- Download and install  [Visual Studio (2022 v17.4.0 and above)](https://visualstudio.microsoft.com/vs/) (Make sure to install version that corresponds with your visual studio instance, 32 vs 64 bit)
[Python311](https://www.python.org/downloads/) (Make sure to install version that corresponds with your visual studio instance, 32 vs 64 bit)

### Configuring application

- Open the config.ini file to configure the following settings
- Connection String: Azure Communication Service resource's connection string.
- Source Phone: Phone number associated with the Azure Communication Service resource.
- target Identity: Multiple sets of outbound target and Transfer target. These sets are seperated by a semi-colon, and outbound target and Transfer target in a each set are seperated by a coma.
-App_base_uri: Base url of the app. (For local development replace the Ngrok url.For e.g. "https://95b6-43-230-212-228.ngrok-free.app")  

### Run the Application

- Add azure communication callautomation's wheel file path in requirement.txt
- Navigate to the directory containing the requirements.txt file and use the following commands for installing all the dependencies and for running the application respectively:
	- pip install -r requirements.txt
	- python program.py
