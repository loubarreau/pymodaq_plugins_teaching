from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, comon_parameters_fun, main, DataActuatorType,\
    DataActuator  # common set of parameters for all actuators
from pymodaq.utils.daq_utils import ThreadCommand # object used to send info back to the main thread
from pymodaq.utils.parameter import Parameter

from pymodaq_plugins_teaching.hardware.spectrometer import Spectrometer


class DAQ_Move_Monochromator(DAQ_Move_base):
    """ Instrument plugin class for an actuator.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Move module through inheritance via
    DAQ_Move_base. It makes a bridge between the DAQ_Move module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of controllers and actuators that should be compatible with this instrument plugin.
        * With which instrument and controller it has been tested.
        * The version of PyMoDAQ during the test.
        * The version of the operating system.
        * Installation instructions: what manufacturer’s drivers should be installed to make it run?

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    # TODO add your particular attributes here if any

    """
    _controller_units = 'whatever'  # TODO for your plugin: put the correct unit here
    is_multiaxes = False  # TODO for your plugin set to True if this plugin is controlled for a multiaxis controller
    _axis_names = ['Axis1', 'Axis2']  # TODO for your plugin: complete the list
    _epsilon = 0.1  # TODO replace this by a value that is correct depending on your controller
    data_actuator_type = DataActuatorType['DataActuator']  # wether you use the new data style for actuator otherwise set this
    # as  DataActuatorType['float']  (or entirely remove the line)

    params = [
                 {'title': 'Infos', 'name': 'infos', 'type': 'str', 'value': '', 'readonly': True},
                 {'title': 'Grating', 'name': 'gratings', 'type': 'list',
                  'value': Spectrometer.gratings[0],
                  'limits': Spectrometer.gratings},
                 {'title': 'Tau (ms)', 'name': 'tau', 'type': 'int', 'value': 500},
                ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)
    # _epsilon is the initial default value for the epsilon parameter allowing pymodaq to know if the controller reached
    # the target value. It is the developer responsibility to put here a meaningful value

    def ini_attributes(self):
        self.controller: Spectrometer = None

    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        pos = DataActuator(data=self.controller.get_wavelength())  # when writing your own plugin replace this line
        pos = self.get_position_with_scaling(pos)
        return pos

    def close(self):
        """Terminate the communication protocol"""
        self.controller.close_communication()  # when writing your own plugin replace this line

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        if param.name() == 'tau':
            self.controller.tau = param.value() / 1000
        else:
            pass

    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_stage_init(old_controller=controller,
                            new_controller=Spectrometer())

        if self.is_master:  # implemented in the current 4.3.x_dev branch, otherwise
            # use self.settings['multiaxes', 'multi_status'] == 'Master'
            initialized = self.controller.open_communication()
        else:
            initialized = True
        self.commit_settings(self.settings.child('tau'))  # tau in settings in ms but in driver in seconds
        self.settings.child('infos').setValue(self.controller.infos)
        info = "Successful initialization"

        return info, initialized

    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        self.controller.set_wavelength(value.value())  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['doing an absolute move']))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)
        self.controller.set_wavelength(value.value(), set_type='rel')  # when writing your own plugin replace this line
        # or
        # self.move_abs(self.target_value)
        self.emit_status(ThreadCommand('Update_Status', ['Doing a relative move']))

    def move_home(self):
        """Call the reference method of the controller"""

        self.controller.find_reference()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))

    def stop_motion(self):
        """Stop the actuator and emits move_done signal"""
        self.controller.stop()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


if __name__ == '__main__':
    main(__file__)
