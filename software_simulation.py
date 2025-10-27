from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError, CommunicationError

from typing import Callable, Annotated
from software_simulation_structure import *

class SoftwareSimulation:

    """
    Software driver of simulation
    """

    def __init__(self):
        self.variables = SoftwareSimulationVariables(on_oxidizing_finished=self.begin_fueling, on_fueling_finished=self.begin_heating,
                                                     on_heating_finished=self.begin_ignition,on_ignition_finished=self.flight,on_ignite=self.do_ignition)
        
        self.phase = PhaseEnum.PHASE_BEGIN
        self.communication_manager = CommunicationManager()
        self.communication_manager.change_transport_type(TransportType.TCP)
        self.register_simulation_callbacks()

    def register_simulation_callbacks(self):
            """
            Register useful (probably should all, but its negligible here) feed/sensor callbacks and register ACK/NACK callbacks from Service calls
            """

            altitude_frame = Frame(ids.BoardID.SOFTWARE, 
                                   ids.PriorityID.LOW, 
                                   ids.ActionID.FEED, 
                                   ids.BoardID.ROCKET, 
                                   ids.DeviceID.SENSOR, 
                                   2, # altitude sensor
                                   ids.DataTypeID.FLOAT,
                                   ids.OperationID.SENSOR.value.READ)
            self.communication_manager.register_callback(self.on_altitude_callback, altitude_frame)

            oxidizer_level_frame = Frame(ids.BoardID.SOFTWARE,
                                   ids.PriorityID.LOW,
                                   ids.ActionID.FEED,
                                   ids.BoardID.ROCKET,
                                   ids.DeviceID.SENSOR,
                                   1, #oxidizer_level
                                   ids.DataTypeID.FLOAT,
                                   ids.OperationID.SENSOR.value.READ)
            self.communication_manager.register_callback(self.on_oxidizer_level_callback,oxidizer_level_frame)

            oxidizer_pressure_frame = Frame(ids.BoardID.SOFTWARE,
                                   ids.PriorityID.LOW,
                                   ids.ActionID.FEED,
                                   ids.BoardID.ROCKET,
                                   ids.DeviceID.SENSOR,
                                   3, #oxidizer_pressure
                                   ids.DataTypeID.FLOAT,
                                   ids.OperationID.SENSOR.value.READ)
            self.communication_manager.register_callback(self.on_oxidizer_pressure_callback,oxidizer_pressure_frame)

            fuel_level_frame = Frame(ids.BoardID.SOFTWARE,
                                   ids.PriorityID.LOW,
                                   ids.ActionID.FEED,
                                   ids.BoardID.ROCKET,
                                   ids.DeviceID.SENSOR,
                                   0, #fuel_level
                                   ids.DataTypeID.FLOAT,
                                   ids.OperationID.SENSOR.value.READ)
            self.communication_manager.register_callback(self.on_fuel_level_callback,fuel_level_frame)

            #SERVICES
            self.register_oxidizer_servo_position_change_callback()
            self.register_fuel_servo_position_change_callback()
            self.register_heater_relay_open_callback()
            self.register_heater_relay_close_callback()
            self.register_ignition_servo_main_valves()
            self.register_ignitor_relay_open_callback()
            self.register_ignitor_relay_close_callback()
            self.register_parachute_relay_open_callback()
            

    def connect(self, settings: TcpSettings):
        self.communication_manager.connect(settings)

    def receive_blocking(self):
        while True:
            try:
                frame = self.communication_manager.receive() # We can handle frames using callbacks or by getting frame right from receive() call
            except TransportTimeoutError:
                pass
            except UnregisteredCallbackError as e:
                pass #I could and probably should register and then log the states of servos, but I think it is negligible during this simulation
                #print(f"unregistered frame received: {e.frame}")

    #Function that are mostly called as a callback when a step is complete -> they update inner state and send open command
    def begin_oxidizing(self):
        print("Begin oxidizing")
        self.phase = PhaseEnum.PHASE_OXIDIZING
        self.send_servo_command(ServoTypes.OXIDIZER_INTAKE, 0)
        self.variables.oxidizer.update_state(0)

    def begin_fueling(self):
        print("Begin fueling")
        self.phase = PhaseEnum.PHASE_FUELING
        self.send_servo_command(ServoTypes.FUEL_INTAKE, 0)
        self.variables.fuel.update_state(0)

    def begin_heating(self):
        print("Begin heating")
        self.phase = PhaseEnum.PHASE_HEATING
        self.send_relay_command(RelayTypes.OXIDIZER_HEATER, ids.OperationID.RELAY.value.OPEN)
        self.variables.heater.update_state(ids.OperationID.RELAY.value.OPEN)

    def begin_ignition(self):
        print("Begin ignition - opening main valves")
        self.phase = PhaseEnum.PHASE_IGNITION
        self.send_servo_command(ServoTypes.FUEL_MAIN,0)
        self.send_servo_command(ServoTypes.OXIDIZER_MAIN,0)

    def do_ignition(self):
        print("Igniting")
        self.send_relay_command(RelayTypes.IGNITER, ids.OperationID.RELAY.value.OPEN)

    def flight(self):
        print("Flying")
        self.phase = PhaseEnum.PHASE_FLIGHT

    def open_parachute(self):
        print("Opening parachute")
        self.send_relay_command(RelayTypes.PARACHUTE, ids.OperationID.RELAY.value.OPEN)
        self.phase = PhaseEnum.PHASE_LANDING

    def done(self):
        self.phase = PhaseEnum.PHASE_DONE
        print("Finished simulation")
        #we may continue or quit() -> I'll do nothing

    #REGISTRATION OF SERVICES' CALLBACKS
    def register_oxidizer_servo_position_change_callback(self):
        oxidizer_servo_frame = Frame(ids.BoardID.SOFTWARE,
                                     ids.PriorityID.LOW,
                                     ids.ActionID.ACK,
                                     ids.BoardID.ROCKET,
                                     ids.DeviceID.SERVO,
                                     1,#oxidizer intake
                                     ids.DataTypeID.INT16,
                                     ids.OperationID.SERVO.value.POSITION,
                                     ())

        oxidizer_servo_frame_fail =  Frame(ids.BoardID.SOFTWARE,
                                     ids.PriorityID.LOW,
                                     ids.ActionID.NACK,
                                     ids.BoardID.ROCKET,
                                     ids.DeviceID.SERVO,
                                     1,#oxidizer intake
                                     ids.DataTypeID.INT16,
                                     ids.OperationID.SERVO.value.POSITION,
                                     ())

        self.communication_manager.register_callback(self.variables.oxidizer.acked, oxidizer_servo_frame)
        self.communication_manager.register_callback(self.variables.oxidizer.nacked, oxidizer_servo_frame_fail)
    
    def register_fuel_servo_position_change_callback(self):
        fuel_servo_frame = Frame(ids.BoardID.SOFTWARE,
                                     ids.PriorityID.LOW,
                                     ids.ActionID.ACK,
                                     ids.BoardID.ROCKET,
                                     ids.DeviceID.SERVO,
                                     0,#fuel intake
                                     ids.DataTypeID.INT16,
                                     ids.OperationID.SERVO.value.POSITION,
                                     ())

        fuel_servo_frame_fail =  Frame(ids.BoardID.SOFTWARE,
                                     ids.PriorityID.LOW,
                                     ids.ActionID.NACK,
                                     ids.BoardID.ROCKET,
                                     ids.DeviceID.SERVO,
                                     0,#fuel intake
                                     ids.DataTypeID.INT16,
                                     ids.OperationID.SERVO.value.POSITION,
                                     ())

        self.communication_manager.register_callback(self.variables.fuel.acked, fuel_servo_frame)
        self.communication_manager.register_callback(self.variables.fuel.nacked, fuel_servo_frame_fail)
        
    def register_heater_relay_open_callback(self):
        heater_relay_open_frame = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.ACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           0, # oxidizer heater
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.OPEN,
                           ())

        heater_relay_open_frame_fail = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.NACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           0, # oxidizer heater
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.OPEN,
                           ())
        
        self.communication_manager.register_callback(self.variables.heater.acked_open, heater_relay_open_frame)
        self.communication_manager.register_callback(self.variables.heater.nacked_open, heater_relay_open_frame_fail)

    def register_heater_relay_close_callback(self):
        heater_relay_close_frame = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.ACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           0, # oxidizer heater
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.CLOSE,
                           ())

        heater_relay_close_frame_fail = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.NACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           0, # oxidizer heater
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.CLOSE,
                           ())
        
        self.communication_manager.register_callback(self.variables.heater.acked_close, heater_relay_close_frame)
        self.communication_manager.register_callback(self.variables.heater.nacked_close, heater_relay_close_frame_fail)

    def register_ignition_servo_main_valves(self):
        fuel_main_frame = Frame(ids.BoardID.SOFTWARE,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.ACK,
                                    ids.BoardID.ROCKET,
                                    ids.DeviceID.SERVO,
                                    2,#fuel main
                                    ids.DataTypeID.INT16,
                                    ids.OperationID.SERVO.value.POSITION,
                                    ())

        fuel_main_frame_fail = Frame(ids.BoardID.SOFTWARE,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.NACK,
                                    ids.BoardID.ROCKET,
                                    ids.DeviceID.SERVO,
                                    2,#fuel main
                                    ids.DataTypeID.INT16,
                                    ids.OperationID.SERVO.value.POSITION,
                                    ())

        oxidizer_main_frame = Frame(ids.BoardID.SOFTWARE,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.ACK,
                                    ids.BoardID.ROCKET,
                                    ids.DeviceID.SERVO,
                                    3,#oxidizer main
                                    ids.DataTypeID.INT16,
                                    ids.OperationID.SERVO.value.POSITION,
                                    ())

        oxidizer_main_frame_fail = Frame(ids.BoardID.SOFTWARE,
                                    ids.PriorityID.LOW,
                                    ids.ActionID.NACK,
                                    ids.BoardID.ROCKET,
                                    ids.DeviceID.SERVO,
                                    3,#oxidizer main
                                    ids.DataTypeID.INT16,
                                    ids.OperationID.SERVO.value.POSITION,
                                    ())

        self.communication_manager.register_callback(self.variables.ignition.fuel_main_acked, fuel_main_frame)
        self.communication_manager.register_callback(self.variables.ignition.fuel_main_nacked, fuel_main_frame_fail)
        
        self.communication_manager.register_callback(self.variables.ignition.oxidizer_main_acked, oxidizer_main_frame)
        self.communication_manager.register_callback(self.variables.ignition.oxidizer_main_nacked, oxidizer_main_frame_fail)

    def register_ignitor_relay_open_callback(self):
        igniter_relay_frame = Frame(ids.BoardID.SOFTWARE, 
                                ids.PriorityID.LOW, 
                                ids.ActionID.ACK, 
                                ids.BoardID.ROCKET, 
                                ids.DeviceID.RELAY, 
                                1, # igniter
                                ids.DataTypeID.FLOAT,
                                ids.OperationID.RELAY.value.OPEN,
                                ()
                                )

        igniter_relay_frame_fail = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.NACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           1, # igniter
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.OPEN,
                           ()
                           )

        self.communication_manager.register_callback(self.variables.ignition.igniter_open_acked, igniter_relay_frame)
        self.communication_manager.register_callback(self.variables.ignition.ingiter_open_nacked, igniter_relay_frame_fail)

    def register_ignitor_relay_close_callback(self):
        igniter_relay_frame = Frame(ids.BoardID.SOFTWARE, 
                                ids.PriorityID.LOW, 
                                ids.ActionID.ACK, 
                                ids.BoardID.ROCKET, 
                                ids.DeviceID.RELAY, 
                                1, # igniter
                                ids.DataTypeID.FLOAT,
                                ids.OperationID.RELAY.value.CLOSE,
                                ()
                                )

        igniter_relay_frame_fail = Frame(ids.BoardID.SOFTWARE, 
                           ids.PriorityID.LOW, 
                           ids.ActionID.NACK, 
                           ids.BoardID.ROCKET, 
                           ids.DeviceID.RELAY, 
                           1, # igniter
                           ids.DataTypeID.FLOAT,
                           ids.OperationID.RELAY.value.CLOSE,
                           ()
                           )

        self.communication_manager.register_callback(self.variables.ignition.igniter_close_acked, igniter_relay_frame)
        self.communication_manager.register_callback(self.variables.ignition.igniter_close_acked, igniter_relay_frame_fail)

    def register_parachute_relay_open_callback(self):
        parachute_relay_frame = Frame(ids.BoardID.SOFTWARE, 
                                      ids.PriorityID.HIGH, 
                                      ids.ActionID.ACK, 
                                      ids.BoardID.ROCKET, 
                                      ids.DeviceID.RELAY, 
                                      2, # parachute
                                      ids.DataTypeID.FLOAT,
                                      ids.OperationID.RELAY.value.OPEN,
                                      ()
                                      )

        parachute_relay_frame_fail = Frame(ids.BoardID.SOFTWARE, 
                                           ids.PriorityID.HIGH, 
                                           ids.ActionID.NACK, 
                                           ids.BoardID.ROCKET, 
                                           ids.DeviceID.RELAY, 
                                           2, # parachute
                                           ids.DataTypeID.FLOAT,
                                           ids.OperationID.RELAY.value.OPEN,
                                           ()
                                           )

        self.communication_manager.register_callback(self.variables.flight.parachute_open_acked, parachute_relay_frame)
        self.communication_manager.register_callback(self.variables.flight.parachute_open_nacked, parachute_relay_frame_fail)
        

    #SERVICES
    def send_servo_command(self, device_type: ServoTypes, position: Annotated[int, "0<=position<=100"]): #I'd love to use pydantic or other library to have better annotation, but I don't want to bloat
        assert device_type in ServoTypes
        assert position in range(0, 100+1)
        
        servo_frame = Frame(ids.BoardID.ROCKET, 
                                 ids.PriorityID.LOW, 
                                 ids.ActionID.SERVICE, 
                                 ids.BoardID.SOFTWARE, 
                                 ids.DeviceID.SERVO, 
                                 device_type, 
                                 ids.DataTypeID.INT16,
                                 ids.OperationID.SERVO.value.POSITION,
                                 (position,) # 0 is for open position, 100 is for closed
                                 )

        self.communication_manager.push(servo_frame)
        self.communication_manager.send()
    
    def send_relay_command(self, device_type: RelayTypes, state: int):
        assert device_type in RelayTypes
        assert state in ids.OperationID.RELAY.value

        relay_frame = Frame(ids.BoardID.ROCKET, 
                            ids.PriorityID.LOW, 
                            ids.ActionID.SERVICE, 
                            ids.BoardID.SOFTWARE, 
                            ids.DeviceID.RELAY, 
                            device_type, # oxidizer heater
                            ids.DataTypeID.FLOAT,
                            state,
                            ()
                            )

        self.communication_manager.push(relay_frame)
        self.communication_manager.send()

    #FEED CALLBACKS
    def on_altitude_callback(self, frame: Frame):
        if(self.phase >= PhaseEnum.PHASE_FLIGHT):
            self.variables.flight.update_altitude(frame.payload[0])
            if(self.variables.flight.is_falling() and self.phase == PhaseEnum.PHASE_FLIGHT):
                self.open_parachute()
            elif(self.variables.flight.altitude <= 3.0 and self.variables.flight.fell): #simulator doesn't respond with altitude=0, so altitude <= 3 has to be here
                self.variables.flight.fell = False #so that if done() doesn't quit, the console won't be spammed with simulation finished messages
                self.done()

    def on_oxidizer_level_callback(self, frame: Frame):
        self.variables.oxidizer.oxidizer_level = frame.payload[0]
        if(not self.variables.oxidizer.should_be_closing and self.variables.oxidizer.servo_open and self.variables.oxidizer.is_oxidiser_ready()):
                self.send_servo_command(ServoTypes.OXIDIZER_INTAKE, 100) #close
                self.variables.oxidizer.update_state(100)

    def on_oxidizer_pressure_callback(self, frame: Frame):
        if(self.phase == PhaseEnum.PHASE_OXIDIZING):
            self.variables.oxidizer.oxidizer_pressure = frame.payload[0]
        elif(self.phase >= PhaseEnum.PHASE_HEATING):
            self.variables.heater.oxidizer_pressure = frame.payload[0]
            if(self.variables.heater.should_work and self.variables.heater.heater_working and self.variables.heater.is_heating_ready()):
                self.send_relay_command(RelayTypes.OXIDIZER_HEATER, ids.OperationID.RELAY.value.CLOSE)
                self.variables.heater.update_state(ids.OperationID.RELAY.value.CLOSE)

    def on_fuel_level_callback(self, frame: Frame):
        self.variables.fuel.fuel_level = frame.payload[0]

        if(not self.variables.fuel.should_be_closing and self.variables.fuel.servo_open and self.variables.fuel.is_fuel_ready()):
            self.send_servo_command(ServoTypes.FUEL_INTAKE, 100)
            self.variables.fuel.update_state(100)
        

if __name__ == "__main__":
    # We must create a frame that will serve as a pattern indicating what kind of frames we want to receive
    # During frame equality comparison the following fields are excluded: priority, data_type, payload
    # You can find more information in communication_library/frame.py
    sim = SoftwareSimulation()

    sim.connect(TcpSettings("127.0.0.1", 3000))

    #first phase -> next phase starts when begin_fueling() is called as a callback from sim.variables.oxidizer when it's done
    sim.begin_oxidizing()

    sim.receive_blocking()