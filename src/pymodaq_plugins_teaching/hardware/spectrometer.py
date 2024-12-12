import numpy as np
from pymodaq.utils.math_utils import gauss1D
from typing import List, Union
from collections.abc import Iterable
from numbers import Number
import math
from time import perf_counter


class Spectrometer: #classe
    """Mock Controller of a spectrometer

    Allows to change the used grating, to move the grating by setting the central wavelength and get the data out of it
    """
    gratings = ['G300', 'G1200']

    Nx = 256
    infos = 'Spectrometer Controller Wrapper 0.1.0'

    def __init__(self): # méthode
        super().__init__()

        self._amp = 10
        self._noise = 0.5
        self._wh = 2
        self._grating = self.gratings[0]

        self._tau = 2  # s
        self._alpha = None
        self._init_value = None
        self._start_time = 0
        self._moving = False
        self._espilon = 0.01

        self._lambda = 532
        self._target_lambda = self._lambda

        self._lambda0 = 528

    def open_communication(self):
        return True

    def close_communication(self):
        return True

    def stop(self):
        self._moving = False

    @property
    def tau(self):
        """
        fetch the characteristic time to reach a particular wavelength
        Returns
        -------
        float: the current characteristic decay time value

        """
        return self._tau

    @tau.setter
    def tau(self, value):
        """
        Set the characteristic time to reach a particular wavelength
        Parameters
        ----------
        value: (float) a strictly positive characteristic time in seconds
        """
        if value <= 0:
            raise ValueError(f'A characteristic time of {value} is not possible. It should be strictly positive')
        else:
            self._tau = value

    @property
    def grating(self):
        """Get.set the current grating in the spectrometer"""
        return self._grating

    @grating.setter
    def grating(self, grat):
        if grat in self.gratings:
            self._grating = grat

    @property
    def amplitude(self):
        """Get/Set the amplitude of the measured spectrum"""
        return self._amp

    @amplitude.setter
    def amplitude(self, value):
        if value > 0.:
            self._amp = value
        if value > 100:
            self._amp = 100

    @property
    def noise(self):
        """Get/Set the noise of the measured spectrum"""
        return self._noise

    @noise.setter
    def noise(self, value):
        if value > 0.:
            self._noise = value

    @property
    def width(self):
        """Get/Set the width of the measured spectrum main peak"""
        return self._wh

    @width.setter
    def width(self, value):
        if value > 0.:
            self._wh = value

    def find_reference(self):
        """Simulate the moving of the grating into a known "limit" for absolute positioning"""
        self.set_wavelength(600, 'abs')

    def set_wavelength(self, value, set_type='abs'):
        """Move the grating to set the central wavelength out of the spectrometer"""
        if set_type == 'abs' and value < 0:
            raise ValueError('Wavelength cannot be negative')
        if set_type == 'abs':
            self._target_lambda = value
        else:
            self._target_lambda = self._lambda + value

        self._init_value = self._lambda
        if self._init_value != self._target_lambda:
            self._alpha = math.fabs(math.log(self._espilon / math.fabs(self._init_value - self._target_lambda)))
        else:
            self._alpha = math.fabs(math.log(self._espilon / 10))
        self._start_time = perf_counter()
        self._moving = True

    def get_wavelength(self):
        """Get the current central wavelength in the spectrometer"""
        if self._moving:
            curr_time = perf_counter()
            self._lambda = \
                math.exp(- self._alpha * (curr_time-self._start_time) / self._tau) *\
                (self._init_value - self._target_lambda) + self._target_lambda
        return self._lambda

    def get_wavelength_axis(self):
        """Get the wavelength axis out of the spectrometer (dependent of the central wavelength (grating position))
        and dispersion of the selected grating"""
        if self._grating == 'G300':
            coeff = 0.7
        elif self._grating == 'G1200':
            coeff = 0.25
        return (np.linspace(0, self.Nx, self.Nx, endpoint=False) - self.Nx / 2) * coeff + self._lambda

    @property
    def data_wavelength(self,):
        """Central wavelength of the physical feature measured by our spectrometer"""
        return self._lambda0

    @data_wavelength.setter
    def data_wavelength(self, lambda0):
        """Defines the center wavelength of the spectrum peak to be measured"""
        if lambda0 < 0:
            raise ValueError('Wavelength cannot be negative')
        self._lambda0 = lambda0

    def _set_data_response(self, lambda_axis: Union[float, Iterable] = 515) -> np.ndarray:
        """Defines the wavelength response of the physical process measured by our spectrometer

        Parameters
        ----------
        lambda_axis: float or iterable of floats

        Returns
        -------
        ndarray
        """
        if isinstance(lambda_axis, Number):
            lambda_axis = np.array([lambda_axis])
        else:
            if not isinstance(lambda_axis, Iterable):
                raise TypeError('lambda_axis should be an iterable of float')
            else:
                if not isinstance(lambda_axis[0], Number):
                    raise TypeError('lambda_axis should be an iterable of float')

        return self._amp * gauss1D(lambda_axis, self._lambda0, self._wh) + self._noise * np.random.rand(len(lambda_axis))

    def _get_data_0D(self, data=None):
        """Get the data at the central wavelength of the spectrometer"""
        if data is None:
            data = self._set_data_response(self.get_wavelength())
        return data

    def _get_data_1D(self, data=None):
        """Get the data as a function of the wavelength axis of the spectrometer
        """
        if data is None:
            data = self._set_data_response(self.get_wavelength_axis())
        return data

    def grab_spectrum(self):
        """get the intensity spectrum out of the spectrometer"""
        return self._get_data_1D()

    def grab_image(self):
        y_axis_array = np.linspace(0, 127, 128)
        data1D = self._get_data_1D()
        data2D = np.outer(gauss1D(y_axis_array, np.mean(y_axis_array), 50), data1D)
        return data2D

    def grab_monochromator(self):
        """get the intensity at the central wavelength"""
        return self._get_data_0D()
