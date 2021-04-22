# Gatecontrol
REST service for a Raspberry Pi operating an FAAC-E124 gate controller.

Based on 
* [fastapi](https://github.com/paurakhsharma/python-microservice-fastapi)

## FAAC-E124 Configuration
     IN 1: OPEN A (LO = E or EP)
     OUT 1: OPEN or PAUSE (o1 = 05)
     OUT 2: CLOSED (o2 = 06)

## Environment Variables
Defaults are shown in brackets
SERVER_ADDRESS (:8080): 
