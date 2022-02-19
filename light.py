"""Support for Lutron lights."""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, 
    SUPPORT_BRIGHTNESS,
    LightEntity,
    SUPPORT_FLASH,
)

from . import LUTRON_CONTROLLER, LUTRON_DEVICES, LutronDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Lutron lights."""
    devs = []
    for (area_name, device) in hass.data[LUTRON_DEVICES]["light"]:
        dev = LutronLight(area_name, device, hass.data[LUTRON_CONTROLLER])
        devs.append(dev)
    
    for (area_name, keypad_name, device) in hass.data[LUTRON_DEVICES]["led"]:
        dev = LutronLedLight(area_name, keypad_name, device, hass.data[LUTRON_CONTROLLER])
        devs.append(dev)

    add_entities(devs, True)


def to_lutron_level(level):
    """Convert the given Home Assistant light level (0-255) to Lutron (0.0-100.0)."""
    return float((level * 100) / 255)


def to_hass_level(level):
    """Convert the given Lutron (0.0-100.0) light level to Home Assistant (0-255)."""
    return int((level * 255) / 100)


class LutronLight(LutronDevice, LightEntity):
    """Representation of a Lutron Light, including dimmable."""

    def __init__(self, area_name, lutron_device, controller):
        """Initialize the light."""
        self._prev_brightness = None
        super().__init__(area_name, lutron_device, controller)

    @property
    def supported_features(self):
        """Flag supported features."""
        supported_features = 0
        if self._lutron_device.is_dimmable:
            supported_features = SUPPORT_BRIGHTNESS
        return supported_features

    @property
    def brightness(self):
        """Return the brightness of the light."""
        new_brightness = to_hass_level(self._lutron_device.last_level())
        if new_brightness != 0:
            self._prev_brightness = new_brightness
        return new_brightness

    def turn_on(self, **kwargs):
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs and self._lutron_device.is_dimmable:
            brightness = kwargs[ATTR_BRIGHTNESS]
        elif self._prev_brightness == 0:
            brightness = 255
        else:
            brightness = self._prev_brightness
        self._prev_brightness = brightness
        self._lutron_device.level = to_lutron_level(brightness)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._lutron_device.level = 0

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attr = {"lutron_integration_id": self._lutron_device.id}
        return attr

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._lutron_device.last_level() > 0

    def update(self):
        """Call when forcing a refresh of the device."""
        if self._prev_brightness is None:
            self._prev_brightness = to_hass_level(self._lutron_device.level)


class LutronLedLight(LutronDevice, LightEntity):
    """Representation of a Lutron Led."""

    def __init__(self, area_name, keypad_name, lutron_device, controller):
        """Initialize the light."""
        self._state = None
        self._keypad_name = keypad_name
        super().__init__(area_name, lutron_device, controller)
    
    @property
    def name(self):
        """Return the name of the device."""
        return f"{self._area_name} {self._keypad_name}: {self._lutron_device.name}"

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_FLASH

    def turn_on(self, **kwargs):
        """Turn the light on."""
        self._state = 1
        self._lutron_device.state = 1

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._state = 0
        self._lutron_device.state = 0

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # attr = {"lutron_integration_id": self._lutron_device.id}
        # return attr
        pass

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state == 1

    def update(self):
        """Call when forcing a refresh of the device."""
        if self._state is None:
            self._state = self._lutron_device.state