"""
Project: Descriptors
Filename: Validator_Classes.py
Description

Classes for filed validation

"""
__author__ = "Guido Boehm"
__filename__ = "Validator_Classes.py"
__credits__ = [""]
__license__ = "GNU GPLv3"
__version__ = "0.0.1"
__maintainer__ = "Guido Boehm"
__email__ = "olb@family-boehm.de"
__status__ = "Prototype"
__copyright__ = """
Copyright 2022, Guido Boehm
All Rights Reserved. 
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES 
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND 
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR 
OTHER DEALINGS IN THE SOFTWARE. 
"""

#  Copyright 2022, Guido Boehm
#  All Rights Reserved.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#  OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#  WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#  OTHER DEALINGS IN THE SOFTWARE.
#

import numbers
import re

from abc import ABC, abstractmethod


class BaseValidator(ABC):
    """
    Base class for value validation
    """
    def __init__(self, min_=None, max_=None):
        self._min = min_
        self._max = max_

    def __set_name__(self, owner_class, prop_name):
        self.prop_name = prop_name

    def __get__(self, instance, owner_class):
        if instance is None:
            return self
        else:
            return instance.__dict__.get(self.prop_name, None)

    @abstractmethod
    def validate(self, value):
        """
        abstract validate method. This will need to be implemented specifically by each subclass
        Args:
            value: value that is subjetced to validation

        Returns:

        """
        pass

    def __set__(self, instance, value):
        self.validate(value)
        instance.__dict__[self.prop_name] = value


class IntegerField(BaseValidator):
    """
    Subclass that validates interger values
    """
    def validate(self, value):
        """
        validates the value
        Args:
            value: value that is subjected to validation

        Returns:

        Raises:
            ValueError: if conditions are not met

        """
        if not isinstance(value, numbers.Integral):
            raise ValueError(f'{self.prop_name} must be an integer.')
        if self._min is not None and value < self._min:
            raise ValueError(f'{self.prop_name} must be >= {self._min}.')
        if self._max is not None and value > self._max:
            raise ValueError(f'{self.prop_name} must be <= {self._max}')


class CharField(BaseValidator):
    """
    Subclass to validate strings
    """
    def __init__(self, min_=None, max_=None):
        min_ = max(min_ or 0, 0)
        super().__init__(min_, max_)

    def validate(self, value):
        """
        validates the value
        Args:
            value: value that is subjected to validation

        Returns:

        Raises:
            ValueError: if conditions are not met
        """
        # strip spaces
        if not isinstance(value, str):
            raise ValueError(f'{self.prop_name} must be a string.')
        value = value.strip()
        if self._min is not None and len(value) < self._min:
            raise ValueError(f'{self.prop_name} must be >= {self._min} chars.')
        if self._max is not None and len(value) > self._max:
            raise ValueError(f'{self.prop_name} must be <= {self._max} chars')


class BoolField(BaseValidator):
    """
    validates that value is only of type boolean
    """

    def __init__(self):
        super().__init__()

    def validate(self, value):
        """
        validates the value
        Args:
            value: value that is subjected to validation

        Returns:

        Raises:
            ValueError: if conditions are not met
        """
        # strip spaces
        if not isinstance(value, bool):
            raise ValueError(f'{self.prop_name} must be a boolean.')


class FQDNField(BaseValidator):
    """
    validates that value is a valid FQDN
    """

    def __init__(self, min_=1, max_=255):
        min_ = max(min_ or 0, 0)
        super().__init__(min_, max_)

    @staticmethod
    def is_fqdn(value):
        """
        https://en.m.wikipedia.org/wiki/Fully_qualified_domain_name
        """

        # Remove trailing dot
        if value[-1] == '.':
            value = value[0:-1]

        #  Split hostname into list of DNS labels
        labels = value.split('.')

        #  Define pattern of DNS label
        #  Can begin and end with a number or letter only
        #  Can contain hyphens, a-z, A-Z, 0-9
        #  1 - 63 chars allowed
        fqdn = re.compile(r'^[a-z0-9]([a-z-0-9-]{0,61}[a-z0-9])?$', re.IGNORECASE)

        # Check that all labels match that pattern.
        return all(fqdn.match(label) for label in labels)

    def validate(self, value):
        """
        validates the value
        Args:
            value: value that is subjected to validation

        Returns:

        Raises:
            ValueError: if conditions are not met
        """
        if not self._min < len(value) < self._max or not FQDNField.is_fqdn(value):
            raise ValueError(f'{self.prop_name} must be a valid FQDN.')


class IPv4Field(BaseValidator):
    """
    validates that value is a valid IPv4 Address
    """

    def __init__(self):
        super().__init__()

    @staticmethod
    def is_ipv4(value):
        """
        returns True is value is a valid ipv4 acddress

        """
        ipv4 = re.compile(r'^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.){3}(25[0-5]|(2[0-4]|1\d|[1-9]|)\d)$')

        return ipv4.match(value)

    def validate(self, value):
        """
        validates the value
        Args:
            value: value that is subjected to validation

        Returns:

        Raises:
            ValueError: if conditions are not met
        """
        if not IPv4Field.is_ipv4(value):
            raise ValueError(f'{self.prop_name} must be a valid IPv4 address.')
