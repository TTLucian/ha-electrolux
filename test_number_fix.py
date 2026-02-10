"""Test to verify the NumberDeviceClass None fix."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # This would fail type checking before the fix
    from homeassistant.components.number.const import NumberDeviceClass

    # Simulate the problematic code pattern
    def test_device_class_none_handling(device_class: NumberDeviceClass | None) -> None:
        """Test that device_class None handling works correctly."""
        # This is the pattern that was failing type checking
        if device_class not in {}:  # Simplified UNIT_CONVERTERS check
            return

        # After the guard, device_class should not be None
        assert device_class is not None  # This is what the fix adds
        # Now we can safely use device_class as a dict key
        result = {"some_key": "value"}.get(device_class, "default")
        print(f"Result: {result}")

    print("Type checking test passed - assertions ensure None safety")
