from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import CommunicationError

from typing import Callable, Annotated
from enum import IntEnum

class PhaseEnum(IntEnum):
    """
    Enum holding inner state of SoftwareSimulation
    """
    PHASE_BEGIN = 0,
    PHASE_OXIDIZING = 1,
    PHASE_FUELING = 2,
    PHASE_HEATING = 3,
    PHASE_IGNITION = 4,
    PHASE_FLIGHT = 5,
    PHASE_LANDING = 6,
    PHASE_DONE = 7

class RelayTypes(IntEnum): #There is probably a reason why you didn't do it in ids.py, but it's more convenient here
    OXIDIZER_HEATER = 0,
    IGNITER = 1,
    PARACHUTE = 2

class ServoTypes(IntEnum):
    FUEL_INTAKE = 0,
    OXIDIZER_INTAKE = 1,
    FUEL_MAIN = 2,
    OXIDIZER_MAIN = 3

class SoftwareSimulationVariables:
    """
    This class keeps track of the state of each phase by creating an object with needed fields. 
    The simulation then updates those fields and calculates what to do next.
    """
    class Servo:
        """
        Main servo class. It's a parent for Oxidizer and Fuel and is abstracting away repeating parts.
        """
        def __init__(self, on_finished: Callable):
            self.on_finished = on_finished
            
            self.servo_open = False
            self.should_be_opening = False
            self.should_be_closing = False

        def update_state(self, position):
            self.should_be_closing = position != 0
            self.should_be_opening = not self.should_be_closing

        def acked(self, frame: Frame):
            #I don't know if my approach is correct, but I assume the servo is open only after getting acked
            if(self.should_be_opening):
                self.should_be_opening = False
                self.servo_open = True
            else:
                self.should_be_closing = False
                self.servo_open = False

                #closed -> send callback and begin next phase
                self.on_finished()

        def nacked(self, frame: Frame): #override to add error handling or something, during this simulation it doesn't matter
            raise CommunicationError("Nacked received: "+str(frame))

    class Oxidizer(Servo):
        """
        Class representation of oxidizing process, which is used during the first phase.
        Keeps track of oxidizer level and pressure.
        """
        def __init__(self, on_finished: Callable):
            super().__init__(on_finished)
            #variables from sensors
            self.oxidizer_level = 0.0
            self.oxidizer_pressure = 0.0 #it seems I didn't have to keep track of the pressure, since by filling the tank the pressure goes up by itself. Oh well

        def is_oxidiser_ready(self):
            return self.oxidizer_level >= 100 and self.oxidizer_pressure >= 30

    class Fuel(Servo):
        """
        Class representation of fueling process, which is used during the second phase.
        Keeps track of fuel level.
        """
        def __init__(self, on_finished: Callable):
            super().__init__(on_finished)
            self.fuel_level = 0.0

        def is_fuel_ready(self):
            return self.fuel_level >= 100

    class Heater:
        """
        Class representation of heating process, which is used during the third phase.
        Keeps track of oxidizer pressure.
        """
        def __init__(self, on_finished: Callable):
            self.oxidizer_pressure = 0.0
            self.heater_working = False
            self.on_finished = on_finished

            self.should_work = False

        def is_heating_ready(self):
            return self.oxidizer_pressure >= 55

        def update_state(self, state: int):
            assert state in ids.OperationID.RELAY.value 
            if(state == ids.OperationID.RELAY.value.OPEN):
                self.should_work = True
            elif(state == ids.OperationID.RELAY.value.CLOSE):
                self.should_work = False

        def acked_open(self, frame: Frame):
            self.heater_working = True

        def nacked_open(self, frame: Frame):
            raise CommunicationError("Heater open: NACK received!")

        def acked_close(self, frame: Frame):
            self.heater_working = False
            self.on_finished()

        def nacked_close(self,frame: Frame):
            raise CommunicationError("Heater close: NACK received!")

    class Ignition:
        """
        Class representation of ignition process, which is used during the fourth phase.
        Keeps track of fuel main and oxidizer main servos and callbacks when they are both open.
        Then, it waits for ack from igniter to callback to next phase
        """
        def __init__(self,on_finished: Callable,on_ignite: Callable):
            self.fuel_main_open = False
            self.oxidizer_main_open = False
            self.ignite = on_ignite

            self.on_finished = on_finished

        def is_ready_to_ignite(self):
            return self.oxidizer_main_open and self.fuel_main_open

        def fuel_main_acked(self, frame: Frame):
            self.fuel_main_open = True
            
            if(self.is_ready_to_ignite()):
                self.ignite()

        def fuel_main_nacked(self, frame: Frame):
            raise CommunicationError("Ingition fuel main: NACK received! "+str(frame))
        
        def oxidizer_main_acked(self, frame: Frame):
            self.oxidizer_main_open = True

            if(self.is_ready_to_ignite()):
                self.ignite()

        def oxidizer_main_nacked(self, frame: Frame):
            raise CommunicationError("Ingition oxidizer main: NACK received! "+str(frame))

        def igniter_open_acked(self, frame: Frame):
            self.on_finished()
    
        def ingiter_open_nacked(self, frame: Frame):
            raise CommunicationError("Igniter open: NACK received! "+str(frame))

        def igniter_close_acked(self, frame: Frame): #The igniter doesn't close in this simulation, but since it's a relay it should handle both states?
            pass

        def igniter_close_nacked(self, frame: Frame):
            raise CommunicationError("Igniter close: NACK received! "+str(frame))

    class Flight:
        """
        Class representation of flight, which is used during fifth and sixth phase.
        At fifth phase, it keeps track of the altitude and register max value.
        At sixth phase, it handles parachute relay responses
        """
        def __init__(self):
            self.altitude = 0.0
            self.max_registered_altitude = 0.0
            self.fell = False

        def update_altitude(self, altitude: float):
            self.max_registered_altitude = max(altitude, self.max_registered_altitude)
            self.altitude = altitude

            if(self.max_registered_altitude > self.altitude):
                self.fell = True

        def is_falling(self):
            return self.max_registered_altitude > self.altitude

        def parachute_open_acked(self, frame: Frame): #Nothing to do here
            pass

        def parachute_open_nacked(self, frame: Frame):
            raise CommunicationError("Parachute open: NACK received!")


    def __init__(self, on_oxidizing_finished: Callable, on_fueling_finished: Callable, on_heating_finished: Callable, on_ignite: Callable, on_ignition_finished: Callable):
        self.oxidizer = self.Oxidizer(on_finished=on_oxidizing_finished)
        self.fuel = self.Fuel(on_finished = on_fueling_finished)
        self.heater = self.Heater(on_finished=on_heating_finished)
        self.ignition = self.Ignition(on_finished=on_ignition_finished, on_ignite = on_ignite)
        self.flight = self.Flight()