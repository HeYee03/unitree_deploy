import mujoco
import numpy as np
import pygame
import sys
import struct

from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelPublisher

from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import WirelessController_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__WirelessController_
from unitree_sdk2py.utils.thread import RecurrentThread

import config

if config.ROBOT == "g1":
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowCmd_
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
    from unitree_sdk2py.idl.default import (
        unitree_hg_msg_dds__LowState_ as LowState_default,
    )
else:
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowCmd_
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import LowState_
    from unitree_sdk2py.idl.default import (
        unitree_go_msg_dds__LowState_ as LowState_default,
    )

TOPIC_LOWCMD = "rt/lowcmd"
TOPIC_LOWSTATE = "rt/lowstate"
TOPIC_HIGHSTATE = "rt/sportmodestate"
TOPIC_WIRELESS_CONTROLLER = "rt/wirelesscontroller"

MOTOR_SENSOR_NUM = 3
NUM_MOTOR_IDL_GO = 20
NUM_MOTOR_IDL_HG = 35


class UnitreeSdk2Bridge:

    def __init__(self, mj_model, mj_data):
        self.mj_model = mj_model
        self.mj_data = mj_data

        self.num_motor = self.mj_model.nu
        self.dim_motor_sensor = MOTOR_SENSOR_NUM * self.num_motor
        self.have_imu = False
        self.have_frame_sensor = False
        self.dt = self.mj_model.opt.timestep
        self.idl_type = (
            self.num_motor > NUM_MOTOR_IDL_GO
        )  # 0: unitree_go, 1: unitree_hg

        self.joystick = None
        self.use_keyboard = False
        self.keyboard_screen = None

        # Check sensor
        for i in range(self.dim_motor_sensor, self.mj_model.nsensor):
            name = mujoco.mj_id2name(
                self.mj_model, mujoco._enums.mjtObj.mjOBJ_SENSOR, i
            )
            if name == "imu_quat":
                self.have_imu_ = True
            if name == "frame_pos":
                self.have_frame_sensor_ = True

        # Unitree sdk2 message
        self.low_state = LowState_default()
        self.low_state_puber = ChannelPublisher(TOPIC_LOWSTATE, LowState_)
        self.low_state_puber.Init()
        self.lowStateThread = RecurrentThread(
            interval=self.dt, target=self.PublishLowState, name="sim_lowstate"
        )
        self.lowStateThread.Start()

        self.high_state = unitree_go_msg_dds__SportModeState_()
        self.high_state_puber = ChannelPublisher(TOPIC_HIGHSTATE, SportModeState_)
        self.high_state_puber.Init()
        self.HighStateThread = RecurrentThread(
            interval=self.dt, target=self.PublishHighState, name="sim_highstate"
        )
        self.HighStateThread.Start()

        self.wireless_controller = unitree_go_msg_dds__WirelessController_()
        self.wireless_controller_puber = ChannelPublisher(
            TOPIC_WIRELESS_CONTROLLER, WirelessController_
        )
        self.wireless_controller_puber.Init()
        self.WirelessControllerThread = RecurrentThread(
            interval=0.01,
            target=self.PublishWirelessController,
            name="sim_wireless_controller",
        )
        self.WirelessControllerThread.Start()

        self.low_cmd_suber = ChannelSubscriber(TOPIC_LOWCMD, LowCmd_)
        self.low_cmd_suber.Init(self.LowCmdHandler, 10)

        # joystick
        self.key_map = {
            "R1": 0,
            "L1": 1,
            "start": 2,
            "select": 3,
            "R2": 4,
            "L2": 5,
            "F1": 6,
            "F2": 7,
            "A": 8,
            "B": 9,
            "X": 10,
            "Y": 11,
            "up": 12,
            "right": 13,
            "down": 14,
            "left": 15,
        }

    def LowCmdHandler(self, msg: LowCmd_):
        if self.mj_data != None:
            for i in range(self.num_motor):
                self.mj_data.ctrl[i] = (
                    msg.motor_cmd[i].tau
                    + msg.motor_cmd[i].kp
                    * (msg.motor_cmd[i].q - self.mj_data.sensordata[i])
                    + msg.motor_cmd[i].kd
                    * (
                        msg.motor_cmd[i].dq
                        - self.mj_data.sensordata[i + self.num_motor]
                    )
                )

    def PublishLowState(self):
        if self.mj_data != None:
            for i in range(self.num_motor):
                self.low_state.motor_state[i].q = self.mj_data.sensordata[i]
                self.low_state.motor_state[i].dq = self.mj_data.sensordata[
                    i + self.num_motor
                ]
                self.low_state.motor_state[i].tau_est = self.mj_data.sensordata[
                    i + 2 * self.num_motor
                ]

            if self.have_frame_sensor_:

                self.low_state.imu_state.quaternion[0] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 0
                ]
                self.low_state.imu_state.quaternion[1] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 1
                ]
                self.low_state.imu_state.quaternion[2] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 2
                ]
                self.low_state.imu_state.quaternion[3] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 3
                ]

                self.low_state.imu_state.gyroscope[0] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 4
                ]
                self.low_state.imu_state.gyroscope[1] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 5
                ]
                self.low_state.imu_state.gyroscope[2] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 6
                ]

                self.low_state.imu_state.accelerometer[0] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 7
                ]
                self.low_state.imu_state.accelerometer[1] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 8
                ]
                self.low_state.imu_state.accelerometer[2] = self.mj_data.sensordata[
                    self.dim_motor_sensor + 9
                ]

            if self.joystick != None or self.use_keyboard:
                if self.use_keyboard:
                    kb = self._get_keyboard_state()
                    btn_R1 = kb["R1"]
                    btn_L1 = kb["L1"]
                    btn_start = kb["start"]
                    btn_select = kb["select"]
                    btn_R2 = kb["R2"]
                    btn_L2 = kb["L2"]
                    btn_A = kb["A"]
                    btn_B = kb["B"]
                    btn_X = kb["X"]
                    btn_Y = kb["Y"]
                    btn_up = kb["up"]
                    btn_down = kb["down"]
                    btn_left = kb["left"]
                    btn_right = kb["right"]
                    stick_lx = kb["lx"]
                    stick_ly = kb["ly"]
                    stick_rx = kb["rx"]
                    stick_ry = kb["ry"]
                else:
                    pygame.event.get()
                    btn_R1 = self.joystick.get_button(self.button_id["RB"])
                    btn_L1 = self.joystick.get_button(self.button_id["LB"])
                    btn_start = self.joystick.get_button(self.button_id["START"])
                    btn_select = self.joystick.get_button(self.button_id["SELECT"])
                    btn_R2 = int(self.joystick.get_axis(self.axis_id["RT"]) > 0)
                    btn_L2 = int(self.joystick.get_axis(self.axis_id["LT"]) > 0)
                    btn_A = self.joystick.get_button(self.button_id["A"])
                    btn_B = self.joystick.get_button(self.button_id["B"])
                    btn_X = self.joystick.get_button(self.button_id["X"])
                    btn_Y = self.joystick.get_button(self.button_id["Y"])
                    btn_up = int(self.joystick.get_hat(0)[1] > 0)
                    btn_down = int(self.joystick.get_hat(0)[1] < 0)
                    btn_left = int(self.joystick.get_hat(0)[0] < 0)
                    btn_right = int(self.joystick.get_hat(0)[0] > 0)
                    stick_lx = self.joystick.get_axis(self.axis_id["LX"])
                    stick_ly = -self.joystick.get_axis(self.axis_id["LY"])
                    stick_rx = self.joystick.get_axis(self.axis_id["RX"])
                    stick_ry = -self.joystick.get_axis(self.axis_id["RY"])

                # Encode wireless_remote to match C++ REMOTE_DATA_RX / BtnDataStruct layout:
                #   byte 0-1:  head[2] (zeros)
                #   byte 2-3:  btn (uint16, LSB-first bit fields)
                #     bit0=R1, bit1=L1, bit2=Start, bit3=Select,
                #     bit4=R2, bit5=L2, bit6=f1, bit7=f2,
                #     bit8=A,  bit9=B,  bit10=X,  bit11=Y,
                #     bit12=up, bit13=right, bit14=down, bit15=left
                #   byte 4-7:  lx (float)
                #   byte 8-11: rx (float)
                #   byte 12-15: ry (float)
                #   byte 16-19: L2 (float, trigger axis)
                #   byte 20-23: ly (float)
                btn_value = (
                    (int(btn_R1) << 0)
                    | (int(btn_L1) << 1)
                    | (int(btn_start) << 2)
                    | (int(btn_select) << 3)
                    | (int(btn_R2) << 4)
                    | (int(btn_L2) << 5)
                    |
                    # f1, f2 = 0 (bits 6,7)
                    (int(btn_A) << 8)
                    | (int(btn_B) << 9)
                    | (int(btn_X) << 10)
                    | (int(btn_Y) << 11)
                    | (int(btn_up) << 12)
                    | (int(btn_right) << 13)
                    | (int(btn_down) << 14)
                    | (int(btn_left) << 15)
                )
                # Pack as little-endian: 2B head + uint16 btn + 5 floats
                packed = struct.pack(
                    "<2s H f f f f f",
                    b"\x00\x00",  # head
                    btn_value,  # btn (uint16)
                    float(stick_lx),  # lx
                    float(stick_rx),  # rx
                    float(stick_ry),  # ry
                    float(btn_L2),  # L2 trigger axis
                    float(stick_ly),  # ly
                )
                for i in range(len(packed)):
                    self.low_state.wireless_remote[i] = packed[i]

            self.low_state_puber.Write(self.low_state)

    def PublishHighState(self):

        if self.mj_data != None:
            self.high_state.position[0] = self.mj_data.sensordata[
                self.dim_motor_sensor + 10
            ]
            self.high_state.position[1] = self.mj_data.sensordata[
                self.dim_motor_sensor + 11
            ]
            self.high_state.position[2] = self.mj_data.sensordata[
                self.dim_motor_sensor + 12
            ]

            self.high_state.velocity[0] = self.mj_data.sensordata[
                self.dim_motor_sensor + 13
            ]
            self.high_state.velocity[1] = self.mj_data.sensordata[
                self.dim_motor_sensor + 14
            ]
            self.high_state.velocity[2] = self.mj_data.sensordata[
                self.dim_motor_sensor + 15
            ]

        self.high_state_puber.Write(self.high_state)

    def PublishWirelessController(self):
        if self.joystick != None or self.use_keyboard:
            if self.use_keyboard:
                kb = self._get_keyboard_state()

            key_state = [0] * 16
            if self.use_keyboard:
                key_state[self.key_map["R1"]] = kb["R1"]
                key_state[self.key_map["L1"]] = kb["L1"]
                key_state[self.key_map["start"]] = kb["start"]
                key_state[self.key_map["select"]] = kb["select"]
                key_state[self.key_map["R2"]] = kb["R2"]
                key_state[self.key_map["L2"]] = kb["L2"]
                key_state[self.key_map["F1"]] = 0
                key_state[self.key_map["F2"]] = 0
                key_state[self.key_map["A"]] = kb["A"]
                key_state[self.key_map["B"]] = kb["B"]
                key_state[self.key_map["X"]] = kb["X"]
                key_state[self.key_map["Y"]] = kb["Y"]
                key_state[self.key_map["up"]] = kb["up"]
                key_state[self.key_map["right"]] = kb["right"]
                key_state[self.key_map["down"]] = kb["down"]
                key_state[self.key_map["left"]] = kb["left"]
            else:
                pygame.event.get()
                key_state[self.key_map["R1"]] = self.joystick.get_button(
                    self.button_id["RB"]
                )
                key_state[self.key_map["L1"]] = self.joystick.get_button(
                    self.button_id["LB"]
                )
                key_state[self.key_map["start"]] = self.joystick.get_button(
                    self.button_id["START"]
                )
                key_state[self.key_map["select"]] = self.joystick.get_button(
                    self.button_id["SELECT"]
                )
                key_state[self.key_map["R2"]] = (
                    self.joystick.get_axis(self.axis_id["RT"]) > 0
                )
                key_state[self.key_map["L2"]] = (
                    self.joystick.get_axis(self.axis_id["LT"]) > 0
                )
                key_state[self.key_map["F1"]] = 0
                key_state[self.key_map["F2"]] = 0
                key_state[self.key_map["A"]] = self.joystick.get_button(
                    self.button_id["A"]
                )
                key_state[self.key_map["B"]] = self.joystick.get_button(
                    self.button_id["B"]
                )
                key_state[self.key_map["X"]] = self.joystick.get_button(
                    self.button_id["X"]
                )
                key_state[self.key_map["Y"]] = self.joystick.get_button(
                    self.button_id["Y"]
                )
                key_state[self.key_map["up"]] = self.joystick.get_hat(0)[1] > 0
                key_state[self.key_map["right"]] = self.joystick.get_hat(0)[0] > 0
                key_state[self.key_map["down"]] = self.joystick.get_hat(0)[1] < 0
                key_state[self.key_map["left"]] = self.joystick.get_hat(0)[0] < 0

            key_value = 0
            for i in range(16):
                key_value += key_state[i] << i

            self.wireless_controller.keys = key_value
            if self.use_keyboard:
                self.wireless_controller.lx = kb["lx"]
                self.wireless_controller.ly = kb["ly"]
                self.wireless_controller.rx = kb["rx"]
                self.wireless_controller.ry = kb["ry"]
            else:
                self.wireless_controller.lx = self.joystick.get_axis(self.axis_id["LX"])
                self.wireless_controller.ly = -self.joystick.get_axis(
                    self.axis_id["LY"]
                )
                self.wireless_controller.rx = self.joystick.get_axis(self.axis_id["RX"])
                self.wireless_controller.ry = -self.joystick.get_axis(
                    self.axis_id["RY"]
                )

            self.wireless_controller_puber.Write(self.wireless_controller)

    def SetupJoystick(self, device_id=0, js_type="xbox"):
        pygame.init()
        pygame.joystick.init()
        joystick_count = pygame.joystick.get_count()
        if joystick_count > 0:
            self.joystick = pygame.joystick.Joystick(device_id)
            self.joystick.init()
        else:
            print("No gamepad detected.")
            sys.exit()

        if js_type == "xbox":
            self.axis_id = {
                "LX": 0,  # Left stick axis x
                "LY": 1,  # Left stick axis y
                "RX": 3,  # Right stick axis x
                "RY": 4,  # Right stick axis y
                "LT": 2,  # Left trigger
                "RT": 5,  # Right trigger
                "DX": 6,  # Directional pad x
                "DY": 7,  # Directional pad y
            }

            self.button_id = {
                "X": 2,
                "Y": 3,
                "B": 1,
                "A": 0,
                "LB": 4,
                "RB": 5,
                "SELECT": 6,
                "START": 7,
            }

        elif js_type == "switch":
            self.axis_id = {
                "LX": 0,  # Left stick axis x
                "LY": 1,  # Left stick axis y
                "RX": 2,  # Right stick axis x
                "RY": 3,  # Right stick axis y
                "LT": 5,  # Left trigger
                "RT": 4,  # Right trigger
                "DX": 6,  # Directional pad x
                "DY": 7,  # Directional pad y
            }

            self.button_id = {
                "X": 3,
                "Y": 4,
                "B": 1,
                "A": 0,
                "LB": 6,
                "RB": 7,
                "SELECT": 10,
                "START": 11,
            }
        else:
            print("Unsupported gamepad. ")

    def SetupKeyboard(self, gui=None):
        """Setup keyboard/GUI as virtual joystick.
        Args:
            gui: VirtualControllerGUI instance (handles keyboard + mouse input)
        """
        self.use_keyboard = True
        self.gui = gui
        print("\n" + "=" * 50)
        print("  Virtual Controller Active")
        print("=" * 50)
        print("  Keyboard: WASD=Move  QEZX=Turn")
        print("  GUI: Drag joystick pads / Click buttons")
        print("=" * 50 + "\n")

    def _get_keyboard_state(self, keys=None):
        """Get controller state from GUI or keyboard."""
        if self.gui is not None:
            # GUI handles both keyboard and mouse joystick
            return self.gui.get_state()
        # Fallback: basic keyboard-only (should not reach here normally)
        return {
            "R1": 0,
            "L1": 0,
            "start": 0,
            "select": 0,
            "R2": 0,
            "L2": 0,
            "A": 0,
            "B": 0,
            "X": 0,
            "Y": 0,
            "up": 0,
            "down": 0,
            "left": 0,
            "right": 0,
            "lx": 0.0,
            "ly": 0.0,
            "rx": 0.0,
            "ry": 0.0,
        }

    def PrintSceneInformation(self):
        print(" ")

        print("<<------------- Link ------------->> ")
        for i in range(self.mj_model.nbody):
            name = mujoco.mj_id2name(self.mj_model, mujoco._enums.mjtObj.mjOBJ_BODY, i)
            if name:
                print("link_index:", i, ", name:", name)
        print(" ")

        print("<<------------- Joint ------------->> ")
        for i in range(self.mj_model.njnt):
            name = mujoco.mj_id2name(self.mj_model, mujoco._enums.mjtObj.mjOBJ_JOINT, i)
            if name:
                print("joint_index:", i, ", name:", name)
        print(" ")

        print("<<------------- Actuator ------------->>")
        for i in range(self.mj_model.nu):
            name = mujoco.mj_id2name(
                self.mj_model, mujoco._enums.mjtObj.mjOBJ_ACTUATOR, i
            )
            if name:
                print("actuator_index:", i, ", name:", name)
        print(" ")

        print("<<------------- Sensor ------------->>")
        index = 0
        for i in range(self.mj_model.nsensor):
            name = mujoco.mj_id2name(
                self.mj_model, mujoco._enums.mjtObj.mjOBJ_SENSOR, i
            )
            if name:
                print(
                    "sensor_index:",
                    index,
                    ", name:",
                    name,
                    ", dim:",
                    self.mj_model.sensor_dim[i],
                )
            index = index + self.mj_model.sensor_dim[i]
        print(" ")


class ElasticBand:

    def __init__(self):
        self.stiffness = 200
        self.damping = 100
        self.point = np.array([0, 0, 3])
        self.length = 0
        self.enable = True

    def Advance(self, x, dx):
        """
        Args:
          δx: desired position - current position
          dx: current velocity
        """
        δx = self.point - x
        distance = np.linalg.norm(δx)
        direction = δx / distance
        v = np.dot(dx, direction)
        f = (self.stiffness * (distance - self.length) - self.damping * v) * direction
        return f

    def MujuocoKeyCallback(self, key):
        glfw = mujoco.glfw.glfw
        if key == glfw.KEY_7:
            self.length -= 0.1
        if key == glfw.KEY_8:
            self.length += 0.1
        if key == glfw.KEY_9:
            self.enable = not self.enable
