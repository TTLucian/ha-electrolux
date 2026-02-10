# Testing Scripts for Electrolux Integration

This directory contains two Python scripts designed to help with testing and development of the Electrolux Home Assistant integration. These scripts allow you to interact directly with the Electrolux API to inspect appliance details and test commands.

## Note: If you regenerate api key and tokens in electrolux api portal for use these scripts, the integration most likely must be reauthenticated with newly generated credentials

## 📋 Scripts Overview

### 1. `script_appliance_details.py` - Appliance Information Tool

This script retrieves and analyzes detailed information about your Electrolux appliances, including their current state and capabilities. It's essential for understanding what features your appliances support and how they should be configured in Home Assistant.

#### Features:
- **Appliance Discovery**: Lists all appliances connected to your Electrolux account
- **Detailed State Analysis**: Retrieves current appliance state and properties
- **Capability Inspection**: Gets appliance capabilities and supported features
- **Model Information**: Extracts model details from various data sources
- **Data Export**: Saves complete appliance data to timestamped files for analysis

#### Usage:

```bash
python scripts/script_appliance_details.py
```

#### What it does:
1. **Authentication**: Prompts for or reads API credentials
2. **Appliance Selection**: Shows numbered list of all your appliances
3. **Data Retrieval**: Fetches state and capabilities for selected appliance
4. **Analysis**: Searches for model information and key properties
5. **Export**: Saves raw JSON data to a text file named after the appliance ID for further analysis

#### Output Files:
The script creates files named after the appliance model with the PNC (Product Number Code) stripped (e.g., `BSE788380M.txt`) containing:
- Appliance metadata (name, ID, type, model, connection status)
- Complete raw state data (JSON)
- Complete raw capabilities data (JSON)

### 2. `script_test_commands.py` - Command Testing Tool

This interactive script allows you to send test commands directly to your appliances and see the results. It's invaluable for testing new features, debugging issues, and understanding the correct command format for different appliance functions.

#### Features:
- **Interactive Command Testing**: Send JSON commands and see immediate results
- **Clean API Response Display**: Shows only the raw JSON response from the Electrolux API
- **State Monitoring**: Check current appliance state before/after commands
- **Command History**: Tracks command count during session
- **Safety Features**: Shows command preview before sending

#### Usage:

```bash
python scripts/script_test_commands.py
```

#### What it does:
1. **Authentication**: Prompts for or reads API credentials
2. **Appliance Selection**: Shows numbered list of all your appliances
3. **Interactive Session**: Enters command testing mode
4. **Command Input**: Accepts JSON commands or special commands
5. **Result Display**: Shows success/failure and any returned data

#### Available Commands:

##### Special Commands:
- `state` or `s` - Show current appliance state
- `help` or `h` - Show command help
- `quit` or `q` - Exit the program

##### JSON Commands:
Send any valid JSON command structure. Examples:

```json
{"cavityLight": true}
{"targetTemperatureC": 180}
{"userSelections": {"programUID": "12345", "temperature": 5}}
{"executionState": "START"}
```

## 🔐 Authentication

Both scripts support two authentication methods:

### Method 1: Environment Variables (Recommended)
Set these environment variables before running the scripts:

```bash
export ELECTROLUX_API_KEY="your_api_key_here"
export ELECTROLUX_ACCESS_TOKEN="your_access_token_here"
export ELECTROLUX_REFRESH_TOKEN="your_refresh_token_here"
```

### Method 2: Interactive Input
If environment variables are not set, the scripts will prompt you to enter credentials interactively.

## 📊 Understanding Appliance Data

### State Data Structure
The appliance state contains real-time information about your appliance:

```json
{
  "properties": {
    "reported": {
      "connectionState": "CONNECTED",
      "applianceInfo": {...},
      "userSelections": {...},
      "executionState": "READY",
      ...
    }
  }
}
```

### Capabilities Data Structure
Capabilities define what features your appliance supports:

```json
{
  "cavityLight": {
    "type": "boolean",
    "access": "readwrite",
    "default": false
  },
  "targetTemperatureC": {
    "type": "number",
    "min": 30,
    "max": 250,
    "step": 5,
    "access": "readwrite"
  }
}
```

## 🛠️ Development Workflow

### Step 1: Discover Your Appliances
```bash
python scripts/script_appliance_details.py
```
- Run this first to understand what appliances you have
- Save the output files for reference
- Note the appliance IDs and supported features

### Step 2: Test Commands Safely
```bash
python scripts/script_test_commands.py
```
- Start with read-only commands like `{"cavityLight": null}` to check current state
- Test simple commands like turning lights on/off
- Gradually test more complex commands
- Always check state between commands

### Step 3: Analyze Results
- Use the exported data files to understand capability structures
- Test edge cases and error conditions
- Validate that commands work as expected

## ⚠️ Safety Guidelines

### Before Testing:
- **Backup Settings**: Note your appliance's current settings
- **Start Small**: Begin with simple, reversible commands
- **Monitor State**: Always check appliance state before and after commands
- **Understand Timeouts**: Some commands may take time to complete

### Command Safety:
- **Boolean Commands**: `{"cavityLight": true}` / `{"cavityLight": false}` are usually safe
- **Numeric Limits**: Respect min/max values from capabilities
- **Step Constraints**: Use values that align with step requirements
- **State Commands**: `{"executionState": "START"}` may start appliance operation

### Error Handling:
- Commands may fail due to appliance state (e.g., can't start if door is open)
- Network issues can cause temporary failures
- Invalid commands will be rejected by the API

## 🔍 Troubleshooting

### Common Issues:

#### Authentication Errors:
- Verify your API credentials are correct and current
- Check that tokens haven't expired
- Ensure you're using the correct Electrolux developer account

#### Appliance Not Found:
- Confirm the appliance is connected to your Electrolux account
- Check that it's powered on and connected to the internet
- Verify the appliance ID is correct

#### Command Failures:
- Check appliance state - some commands require specific conditions
- Verify command format matches capability definitions
- Ensure numeric values respect min/max/step constraints

#### Connection Issues:
- Check your internet connection
- Verify Electrolux API status
- Try again after a few minutes

### Debug Mode:
Both scripts provide detailed error messages and stack traces for debugging. If you encounter issues, the full error output will help identify the problem.

## 📝 Example Session

```
$ python script_test_commands.py

📋 Available appliances:
  1. My Oven (944188772-00-31862190-443E07363DAB)
     Type: OVEN
     Model: BSE788380M
     Connection: CONNECTED

Choose an appliance (enter number): 1

🔧 Starting test command session for: My Oven (944188772-00-31862190-443E07363DAB)

📊 Getting current state for appliance: 944188772-00-31862190-443E07363DAB
✅ Current state retrieved

Command #1 > {"cavityLight": true}
📤 Sending command to appliance 944188772-00-31862190-443E07363DAB:
   Command: {
     "cavityLight": true
   }
✅ Command executed successfully!
📨 API Response:
{
  "commandId": "abc123-def456",
  "status": "accepted",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response Example:
```
Command #2 > {"cavityLight": true}
📤 Sending command to appliance 944188772-00-31862190-443E07363DAB:
   Command: {
     "cavityLight": true
   }
❌ Command failed!
📨 API Response:
{
  "error": "COMMAND_VALIDATION_ERROR",
  "message": "Command validation failed",
  "detail": "Remote control disabled"
}
```

## 🤝 Contributing

When developing new features for the Electrolux integration:

1. **Use these scripts** to test your changes against real appliances
2. **Document new capabilities** discovered during testing
3. **Validate command formats** before implementing in the main integration
4. **Test edge cases** and error conditions thoroughly

These scripts are essential tools for ensuring the integration works correctly with real Electrolux appliances and their various capabilities.

## 🚀 **Running the Scripts: Two Methods**

### **Method 1: Run from Repository (Recommended)**

This is the easiest and most reliable way to run the scripts, as they are designed to work within the repository structure.

#### **Prerequisites:**
- Python 3.8 or higher
- Git (for cloning the repository)

#### **Step-by-Step Instructions:**

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/TTLucian/homeassistant_electrolux_status.git
   cd homeassistant_electrolux_status
   ```

2. **Create a Virtual Environment (Recommended):**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate

   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install electrolux-group-developer-sdk>=0.2.0
   ```

4. **Set Environment Variables (Optional but Recommended):**
   ```bash
   # On Windows
   set ELECTROLUX_API_KEY=your_api_key_here
   set ELECTROLUX_ACCESS_TOKEN=your_access_token_here
   set ELECTROLUX_REFRESH_TOKEN=your_refresh_token_here

   # On macOS/Linux
   export ELECTROLUX_API_KEY="your_api_key_here"
   export ELECTROLUX_ACCESS_TOKEN="your_access_token_here"
   export ELECTROLUX_REFRESH_TOKEN="your_refresh_token_here"
   ```

5. **Run the Scripts:**
   ```bash
   # For appliance details
   python scripts/script_appliance_details.py

   # For command testing
   python scripts/script_test_commands.py
   ```

6. **Follow Interactive Prompts:**
   - If environment variables aren't set, enter credentials when prompted
   - Select your appliance from the numbered list
   - Follow the script's guidance

#### **Expected Output:**
- Appliance discovery and selection
- Detailed state and capability data
- Exported data files in the repository root

### **Method 2: Extract as Standalone Scripts (Advanced)**

For users who want to run the scripts without cloning the entire repository, you can extract the necessary components.

#### **Prerequisites:**
- Python 3.8 or higher
- Understanding of Python imports and dependencies

#### **Step-by-Step Instructions:**

1. **Install the SDK:**
   ```bash
   pip install electrolux-group-developer-sdk>=0.2.0
   ```

2. **Create Standalone API Client:**
   
   Create a new file `electrolux_api_client.py` with this content:
   ```python
   """Standalone Electrolux API Client for testing scripts."""
   
   import logging
   from typing import Any, Dict, List
   
   from electrolux_group_developer_sdk.auth.token_manager import TokenManager
   from electrolux_group_developer_sdk.client.appliance_client import ApplianceClient
   
   _LOGGER = logging.getLogger(__name__)
   
   class ElectroluxApiClient:
       """Standalone wrapper for the Electrolux API client."""
   
       def __init__(self, api_key: str, access_token: str, refresh_token: str):
           """Initialize the API client."""
           self._token_manager = TokenManager(access_token, refresh_token, api_key)
           self._client = ApplianceClient(self._token_manager)
   
       async def get_appliances_list(self) -> List[Dict[str, Any]]:
           """Get list of appliances."""
           appliances = await self._client.get_appliances()
           result = []
           for appliance in appliances:
               # Extract model from PNC
               pnc = appliance.applianceId
               model_name = getattr(appliance, "model", "Unknown")
               if model_name == "Unknown" and pnc:
                   pnc_parts = pnc.split("_")
                   if len(pnc_parts) > 0:
                       model_part = pnc_parts[0]
                       if model_part.isdigit() and len(model_part) >= 6:
                           model_name = model_part
   
               appliance_data = {
                   "applianceId": appliance.applianceId,
                   "applianceName": appliance.applianceName,
                   "applianceType": appliance.applianceType,
                   "connectionState": "connected",
                   "applianceData": {
                       "applianceName": appliance.applianceName,
                       "modelName": model_name,
                   },
                   "created": "2022-01-01T00:00:00.000Z",
               }
               result.append(appliance_data)
           return result
   
       async def get_appliance_state(self, appliance_id: str) -> Dict[str, Any]:
           """Get appliance state."""
           return await self._client.get_appliance_state(appliance_id)
   
       async def get_appliance_capabilities(self, appliance_id: str) -> Dict[str, Any]:
           """Get appliance capabilities."""
           return await self._client.get_appliance_capabilities(appliance_id)
   
       async def execute_appliance_command(self, appliance_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
           """Execute a command on the appliance."""
           return await self._client.execute_command(appliance_id, command)
   ```

3. **Modify the Scripts:**

   **For `script_appliance_details.py`:**
   - Change the import line from:
     ```python
     from custom_components.electrolux_status.util import ElectroluxApiClient
     ```
   - To:
     ```python
     from electrolux_api_client import ElectroluxApiClient
     ```
   - Remove the `sys.path.insert(0, os.path.dirname(__file__))` line

   **For `script_test_commands.py`:**
   - Apply the same import change as above

4. **Create Directory Structure:**
   ```
   your_project/
   ├── electrolux_api_client.py
   ├── scripts/
   │   ├── script_appliance_details.py
   │   ├── script_test_commands.py
   │   └── TESTING_SCRIPTS_README.md
   └── requirements.txt  # with: electrolux-group-developer-sdk>=0.2.0
   ```

5. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

6. **Set Environment Variables:**
   ```bash
   export ELECTROLUX_API_KEY="your_api_key"
   export ELECTROLUX_ACCESS_TOKEN="your_access_token"
   export ELECTROLUX_REFRESH_TOKEN="your_refresh_token"
   ```

7. **Run the Scripts:**
   ```bash
   python scripts/script_appliance_details.py
   python scripts/script_test_commands.py
   ```

#### **Differences Between Methods:**

| Aspect | Repository Method | Standalone Method |
|--------|------------------|-------------------|
| **Ease of Use** | ✅ Very Easy | ⚠️ Advanced |
| **Maintenance** | ✅ Auto-updated | ⚠️ Manual updates needed |
| **Dependencies** | ✅ All included | ⚠️ Manual extraction required |
| **File Structure** | ✅ Preserved | ⚠️ Custom setup needed |
| **Support** | ✅ Full support | ⚠️ Community support only |

#### **When to Use Each Method:**

- **Use Repository Method** if you want the easiest experience and don't mind cloning the repo
- **Use Standalone Method** if you need to integrate the scripts into your own project or have specific requirements

#### **Troubleshooting Standalone Setup:**

- **Import Errors**: Ensure `electrolux_api_client.py` is in the same directory as the scripts
- **SDK Issues**: Verify the SDK is installed: `pip list | grep electrolux`
- **Permission Errors**: Make sure scripts have execute permissions: `chmod +x script_*.py`
- **Path Issues**: If you move files, update any relative imports accordingly</content>
<parameter name="filePath">d:\Lucian\Documents\Github\homeassistant_electrolux_status\TESTING_SCRIPTS_README.md
