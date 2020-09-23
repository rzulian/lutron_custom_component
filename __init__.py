"""Component for interacting with a Lutron RadioRA 2 system."""
import logging

from pylutron import Button, Lutron
import voluptuous as vol

from homeassistant.const import ATTR_ID, CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

DOMAIN = "lutron"

_LOGGER = logging.getLogger(__name__)

LUTRON_BUTTONS = "lutron_buttons"
LUTRON_CONTROLLER = "lutron_controller"
LUTRON_DEVICES = "lutron_devices"

CONF_LUTRON_DB_FILE = 'db_file'
# Attribute on events that indicates what action was taken with the button.
ATTR_ACTION = "action"
ATTR_FULL_ID = "full_id"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_USERNAME): cv.string,
                vol.Optional(CONF_LUTRON_DB_FILE, default=''): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, base_config):
    """Set up the Lutron component."""

    hass.data[LUTRON_BUTTONS] = []
    hass.data[LUTRON_CONTROLLER] = None
    hass.data[LUTRON_DEVICES] = {
        "light": [],
        "cover": [],
        "switch": [],
        "scene": [],
        "binary_sensor": [],
        "led": [],
    }

    config = base_config.get(DOMAIN)
    hass.data[LUTRON_CONTROLLER] = Lutron(
        config[CONF_HOST], config[CONF_USERNAME], config[CONF_PASSWORD]
    )

    db_file =  config[CONF_LUTRON_DB_FILE]
    if db_file != '' and not db_file.startswith("/"):
            db_file = hass.config.path(db_file)

    hass.data[LUTRON_CONTROLLER].load_xml_db(db_file)
    hass.data[LUTRON_CONTROLLER].connect()
    _LOGGER.info("Connected to main repeater at %s", config[CONF_HOST])

    # Sort our devices into types
    for area in hass.data[LUTRON_CONTROLLER].areas:
        for output in area.outputs:
            if output.type in ("SYSTEM_SHADE", "MOTOR"):
                hass.data[LUTRON_DEVICES]["cover"].append((area.name, output))
            elif output.is_light:
                hass.data[LUTRON_DEVICES]["light"].append((area.name, output))
            else:
                hass.data[LUTRON_DEVICES]["switch"].append((area.name, output))
        for keypad in area.keypads:
            for button in keypad.buttons:
                # If the button has a function assigned to it, add it as a scene
                # TODO verify this!
                if button.name != "Unknown Button" and button.button_type in (
                    "SingleAction",
                    "DualAction",
                    "AdvancedToggle",
                    "AdvancedConditional",
                    "Toggle",
                    "SingleSceneRaiseLower",
                    "MasterRaiseLower",
                    "SimpleConditional"
                ):
                    # Associate an LED with a button if there is one
                    # TODO check this a led is a scene???
                    led = next(
                        (led for led in keypad.leds if led.number == button.number),
                        None,
                    )
                    hass.data[LUTRON_DEVICES]["scene"].append(
                         (area.name, keypad.name, button, led)
                    )

                    # Add the LED as a light device if is controlled via integration
                    if not(led is None) and button.led_logic==5:
                        hass.data[LUTRON_DEVICES]["led"].append((area.name, keypad.name, led))
                        
                hass.data[LUTRON_BUTTONS].append(
                    LutronButton(hass, area.name, keypad, button)
                )      
        if area.occupancy_group is not None:
            hass.data[LUTRON_DEVICES]["binary_sensor"].append(
                (area.name, area.occupancy_group)
            )

    for component in ("light", "cover", "switch", "scene", "binary_sensor"):
        discovery.load_platform(hass, component, DOMAIN, {}, base_config)
    return True


class LutronDevice(Entity):
    """Representation of a Lutron device entity."""

    def __init__(self, area_name, lutron_device, controller):
        """Initialize the device."""
        self._lutron_device = lutron_device
        self._controller = controller
        self._area_name = area_name

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.hass.async_add_executor_job(
            self._lutron_device.subscribe, self._update_callback, None
        )

    def _update_callback(self, _device, _context, _event, _params):
        """Run when invoked by pylutron when the device state changes."""
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the device."""
        return f"{self._area_name} {self._lutron_device.name}"

    @property
    def should_poll(self):
        """No polling needed."""
        return False


class LutronButton:
    """Representation of a button on a Lutron keypad.

    This is responsible for firing events as keypad buttons are press
    (and possibly release, depending on the button type). It is not
    represented as an entity; it simply fires events.
    """

    def __init__(self, hass, area_name, keypad, button):
        """Register callback for activity on the button."""
        name = f"{keypad.name}: {button.name}"
        self._hass = hass
        self._has_release_event = (
            button.button_type is not None and  button.button_type in ("RaiseLower", "DualAction" )
        )
        self._id = slugify(name)
        self._keypad = keypad
        self._area_name = area_name
        self._button_name = button.name
        self._button = button
        self._event = "lutron_event"
        self._full_id = slugify(f"{area_name} {keypad.name}: {button.name}")

        button.subscribe(self.button_callback, None)

    def button_callback(self, button, context, event, params):
        """Fire an event about a button being press, release, hold, etc."""

        ev_map = {
            Button.Event.PRESS: "press",
            Button.Event.RELEASE: "release",
            Button.Event.HOLD: "hold",
            Button.Event.DOUBLE_TAP: "double_tap",
            Button.Event.HOLD_RELEASE: "hold_release"
        }

        if event in ev_map:
            data = {ATTR_ID: self._id, ATTR_ACTION: ev_map[event], ATTR_FULL_ID: self._full_id}
            self._hass.bus.fire(self._event, data)
