ROBOT = "g1"  # Robot name, "go2", "b2", "b2w", "h1", "go2w", "g1"
ROBOT_SCENE = (
    "../unitree_robots/" + ROBOT + "/scene_29dof.xml"
)  # Robot scene (use scene_29dof.xml for G1-29dof)
DOMAIN_ID = 0  # Domain id
INTERFACE = "lo"  # Interface (run g1_ctrl with: ./g1_ctrl -n lo)

USE_JOYSTICK = 0  # Simulate Unitree WirelessController using a gamepad
JOYSTICK_TYPE = "xbox"  # support "xbox" and "switch" gamepad layout
JOYSTICK_DEVICE = 0  # Joystick number

USE_KEYBOARD = True  # Simulate Unitree WirelessController using keyboard

PRINT_SCENE_INFORMATION = True  # Print link, joint and sensors information of robot
ENABLE_ELASTIC_BAND = True  # Virtual spring band, used for lifting g1

SIMULATE_DT = 0.005  # Need to be larger than the runtime of viewer.sync()
VIEWER_DT = 0.02  # 50 fps for viewer
