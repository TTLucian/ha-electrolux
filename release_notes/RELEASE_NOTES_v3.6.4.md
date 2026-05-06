# Release Notes v3.6.4

### Refrigerators:
   Added:
   - ```ecoMode```
   - ```autosense```

### Robot vacuum:
   - Implemented Cybele robot vacuum basic entities
   - Added vacuum entity for "PUREi9", "Gordias", "Cybele"

### Washing machines:
   - Fixed load weight information
   - Added Appliance Care & Maintenance Entities
   - Added Network Interface Details
   - Added Appliance Information

### Air conditioners:
   - Added climate entity to "CA", "Azul", "Panther", "Bogong", "Telica" appliance types



### Note:
   - A big "THANK YOU" to [joeblack2k](https://github.com/joeblack2k) for his first contribution.

   - I don't own nor do I have diagnostic json files for all these appliances so further testing is needed. Report any problems you encounter on [GitHub](https://github.com/TTLucian/ha-electrolux/issues)

   - The CI run is currently failing due to some missing tests for the newly added entities. I don't have the time to properly work on the tests, I do not have access to Copilot subscription and premium requests anymore due to lack of project funds. While I'm still working on this, the reduced access to these tools means development and debugging will be slower and more "manual" for the time being. I appreciate your patience as I work through the remaining blockers at this new pace.