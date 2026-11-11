from domain.commands.base import ActuatorCommand


class StartPumpCommand(ActuatorCommand):
    # idle -> running; nur erlaubt, wenn "start" in allowed_commands steht.
    command_type = "start_pump"
    port_command = "on"
    state_command = "start"
    target_state = "running"


class StopPumpCommand(ActuatorCommand):
    # running -> idle; nur erlaubt, wenn "stop" in allowed_commands steht.
    command_type = "stop_pump"
    port_command = "off"
    state_command = "stop"
    target_state = "idle"
