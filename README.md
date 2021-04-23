# Gatecontrol
REST service for a Raspberry Pi operating an FAAC-E124 gate control unit.

## Hardware Architecture



## FAAC-E124 Control Unit Configuration
Please refer to the [FAAC-E124 manual](http://www.faac.co.uk/productfiles/245_Manual_rad0ADBE.pdf)
for details on the control unit. Chapter 5 of the document explains how to program the device.
The following values need to be configured:
```
LO = E or EP
o1 = 05
o2 = 06
```

Setting `LO` to either `E` or `EP` configures the input `IN 1` to operate the gate semi-automatically:
A first impulse on the input will open the gate. A second one will close it.
Configuring `o1` to `05` activates output `OUT 1` in _OPEN_ or _PAUSE_ state of the gate.
Setting `o2` to `06` activates output `OUT 2` in _CLOSED_ state. 

## Environment Variables
The following environment variables can be set to configure the service.
If a variable is not defined the value in brackets is used as default.
The basic authentication is activated if both `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD` are provided.

* `HOST` (0.0.0.0): The host interface where this service is running
* `PORT` (8000): The port the service is listening
* `BASIC_AUTH_USERNAME`: The username that must be passed to the service in a basic auth header
* `BASIC_AUTH_PASSWORD`: The password that must be passed to the service in a basic auth header
* `WEBHOOK_URL` (http://localhost:51828): The URL of the homebridge running the _Homebridge Webhooks_ plugin
* `ACCESSORY_ID` (gatecontrol): The accessory ID as configured as gate in the _Homebridge Webhooks_ plugin

## API Documentation
The service utilizes the [FastAPI](https://fastapi.tiangolo.com/) framework.
It generates an OpenAPI under the URL `http://HOST:PORT/docs` e.g. http://localhost:8000/docs.
