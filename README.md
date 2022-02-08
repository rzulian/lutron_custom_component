# lutron_custom_component
Lutron custom component for HA using pylutron

This is using a fork of pylutron , which is currently a PR https://github.com/thecynic/pylutron/pull/52 .

This PR is adding:
- support for Homeworks QS.
- support for recursive areas in naming
- areas with IntegrationID are OccupancyGroup
- OUTPUT to support movement raise, lower, stop, jogs(eg for motors)
- buttons: support for actions 
- corrected led states
- support for QS_IO_INTERFACE
- support for phantom keypads
- support for seetouch international keypads
- support for CCI

Features:
- ability to include a `db_file` to the configuration, so that the Lutron component can cache the data
```
lutron:
  host: 192.168.1.23
  username: lutron
  password: password
  db_file: 'Lutron.xml'
```
- leds in keypad's buttons that are configured as "integration", are created as Light devices `LutronLedLight`, so you can control them
- binary sensors for Occupancy group
- buttons to support press, release, hold, double tap, and hold release status
- added a new `LutronMotorBlind` to support motorized shades/blinds via a Motor output (e.g )

The custom component is loading the `pylutron` branch using `  "requirements": ["git+https://github.com/rzulian/pylutron.git@homeworks-support#pylutron==0.2.6"],` in `manifest.json`.
