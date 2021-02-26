from math import copysign
from os.path import dirname, basename
from subsystems.turret import Turret
from wpilib import Joystick, run, TimedRobot, CameraServer
from controllers import XBoxController, JoystickController, ShooterController
from subsystems import Chassis, Turret, Autonomous, Magazine, Intake, Climber
from hardware import ADXRS450
from tools import Timer
from constants import kS, kV, TRACKWIDTH, TURRET_SHOOT_MOTORS
from wpilib.trajectory import TrajectoryUtil
from glob import glob as files
import time


filenames = files(dirname(__file__) + "/paths/*.json")
try:
    filenames.sort(key=lambda filename: int(basename(filename).split(".")[0]))
except:
    raise Exception(
        "Files in `path` folder MUST follow 'INTEGER.*.json' pattern, where `INTEGER` is any integer value")
print("Path filenames are:", filenames)
trajectories = list(
    map(TrajectoryUtil.fromPathweaverJson, filenames))


@run
class Kthugdess(TimedRobot):
    def robotInit(self):
        # CameraServer.launch()
        self.chassis = Chassis()
        self.climber = Climber()
        self.turret = Turret()
        self.gyro = ADXRS450()
        self.intake = Intake()
        self.mag = Magazine()
        self.controller = XBoxController(0)
        self.chassis.reset_encoders()
        self.auto = Autonomous(kS, kV, TRACKWIDTH, trajectories)
        self.reset()

        # This was for the USB Camera
        # self.other_camera = CameraServer()

        self.auto_timer = Timer()
        # self.other_camera.launch()

    def reset(self):
        self.turret.reset()
        self.auto.reset()
        self.auto.start(self.chassis, self.gyro)

    autonomousInit = reset
    teleopInit = reset

    def autonomousPeriodic(self):
        self.turret.zero()
        # self.turret.track_limelight()
        # print(self.turret.is_zeroed)
        """

        '''
        Rewriting the code but without needing to use timers! -> This will probably break
        '''
        print("If auto is paused: " + str(self.auto.is_paused()) +
              "/ Timer: " + str(self.auto_timer.get()))

        if self.auto.is_paused():
            if self.turret.is_locked():
                print("Shooting")
                self.shoot(True)
            else:
                print("Not locked")
                self.turret.track_limelight()
        else:
            print("Going to next path")
            self.auto.update(self.chassis, self.gyro)
            # self.auto.resume(self.chassis, self.gyro)

        if self.auto.is_done():
            print("Auto has ended")
            self.shoot(False)
            self.turret.idle()
            self.mag.stop()
        else:
            print("Intaking balls")
            self.auto.update(self.chassis, self.gyro)
            self.turret.idle()
            self.intake.intake()
            self.mag.intake()
            # self.turret.track_limelight()
"""
        print(self.auto.current_trajectory)

        if self.auto.is_paused() and self.turret.is_zeroed:
            print("If auto is paused: " + str(self.auto.is_paused()) +
                  "/ Timer: " + str(self.auto_timer.get()))
            if self.auto_timer.get() < 1:
                print("Pausing")
                self.intake.idle()
                self.mag.stop()
                self.turret.track_limelight()
            elif self.auto_timer.get() < 2:
                self.turret.track_limelight()
                if self.auto.current_trajectory == 1:
                    if self.turret.is_locked():
                        print("Shooting")
                        self.shoot(True)
                    else:
                        print("Not locked")
            else:
                print("Resuming auto")
                self.auto.resume(self.chassis, self.gyro)
        elif not self.auto.is_done():  # If the auto isn't paused but it's not done either
            if self.auto.current_trajectory == 0:
                print("Intaking balls")
                self.intake.intake()
                self.mag.intake()
            print("Start up")
            self.turret.track_limelight()
            self.auto_timer.start()
            self.auto.update(self.chassis, self.gyro)
            self.turret.idle()
            self.intake.intake()
            self.mag.intake()
        else:
            print("Auto has ended")
            self.shoot(False)
            self.turret.idle()
            self.mag.stop()

    def teleopPeriodic(self):
        self.turret.zero()
        print(self.climber.servo.get())
        # self.turret.goto_angle(self.turret.HOME_ANGLE)

        if self.controller.deploy_climb():
            self.turret.shooter_stop()
            self.climber.deploy()
            if self.climber.is_deployed():
                self.turret.idle()
        if self.controller.lower_climb():  # Added limit switch, Adam
            self.climber.lower()
        if self.controller.retract_climb():
            self.climber.retract()
        elif self.controller.extend_climb():
            self.climber.extend()
        else:
            if self.climber.is_extended() and self.climber.servo_at_position(self.climber.extend_position):
                print("At position")
                # Whatever position is appropriate to "unlatch" the servo
                self.climber.servo.set(1)
            self.climber.stop()

        if self.controller.intake():
            self.turret.track_limelight()
            self.intake.intake()
            self.mag.intake()
        else:
            self.intake.idle()
            print("Preparing to shoot, self.controller.shoot(): ",
                  self.controller.shoot())
            self.shoot(self.controller.shoot())

        if self.controller.shift():
            self.chassis.set_high_gear()
        else:
            self.chassis.set_low_gear()

        if self.controller.clear_jam():
            self.mag.clear_jam()

        forward = self.controller.forward()
        turn = self.controller.turn()
        self.chassis.arcade_drive(-copysign(abs(forward) ** 1.15, forward),
                                  copysign(abs(turn) ** 1.15, turn))

        # self.turret.goto_angle(self.turret.HOME_ANGLE)
        # print("cw", self.turret.clockwise_limit_switch.get(),
        #       "ccw", self.turret.counterclockwise_limit_switch.get())

    def disabledInit(self):
        # self.turret.hood_goto(0)
        pass

    def disabledPeriodic(self):
        # print("Disabling periodic!")
        pass

    def shoot(self, shoot):
        if self.climber.is_deployed():
            self.turret.goto_angle(self.turret.HOME_ANGLE)
            self.mag.stop()
            return

        if shoot:
            self.turret.shoot()
            self.turret.stop_turning()
            if self.turret.is_full_speed() and self.mag.is_ready():
                self.mag.dump()
            elif self.turret.is_full_speed():
                self.mag.agitate()
        else:
            self.turret.track_limelight()
            self.turret.idle()
            self.mag.stop()
