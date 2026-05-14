# Release Notes v3.6.6

- Added guard to prevent nonexisting values reported by the api as the current value from being added as options to select entities.
- Fixed entity type determination logic. Now correctly checks for the presence of **any continuous range constraint** (min, max, or range) when deciding between SELECT and NUMBER platforms.
- Updated the get_entity_type() method to properly detect discrete-valued capabilities.
- Added a filter for execute command on/off. All entities derived from these capabilities will be switches instead of buttons.
- Added guard in platform logic resolver so that sensors and binary sensors will not have category config. This is not supported by home assistant and will not load.
- Fix target temperature reset by API after power off for AC units (@[netflash](https://github.com/netflash))
- Add some missing entities for AC units (@[netflash](https://github.com/netflash))

A big thanks to [netflash](https://github.com/netflash) for his PR's fixing AC units 