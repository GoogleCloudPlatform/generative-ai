import pytest

from tau2.domains.telecom.user_data_model import (
    APNNames,
    APNSettings,
    AppPermissions,
    AppStatus,
    MockPhoneAttributes,
    NetworkModePreference,
    NetworkStatus,
    NetworkTechnology,
    PerformanceLevel,
    SignalStrength,
    SimStatus,
    TelecomUserDB,
    UserSurroundings,
    VpnDetails,
)
from tau2.domains.telecom.user_tools import TelecomUserTools


@pytest.fixture
def telecom_tools():
    """Fixture to create and return TelecomUserTools instance for testing."""
    device_attrs = MockPhoneAttributes()
    surroundings_attrs = UserSurroundings()
    db = TelecomUserDB(device=device_attrs, surroundings=surroundings_attrs)
    # Initialize with some default apps for testing app-related tools
    db.device.app_statuses = {
        "messaging": AppStatus(app_name="messaging", permissions=AppPermissions()),
        "browser": AppStatus(
            app_name="browser", permissions=AppPermissions(network=True, storage=True)
        ),
    }
    tools = TelecomUserTools(db=db)
    return tools


class TestTelecomUserTools:
    def test_check_status_bar_default(self, telecom_tools: TelecomUserTools):
        status = telecom_tools.check_status_bar()
        assert "Status Bar:" in status
        assert f"{telecom_tools.device.battery_level}%" in status

    def test_check_status_bar_airplane_mode(self, telecom_tools: TelecomUserTools):
        telecom_tools.device.airplane_mode = True
        status = telecom_tools.check_status_bar()
        assert "✈️ Airplane Mode" in status
        assert f"{telecom_tools.device.battery_level}%" in status

    def test_toggle_airplane_mode(self, telecom_tools: TelecomUserTools):
        initial_state = telecom_tools.device.airplane_mode
        result = telecom_tools.toggle_airplane_mode()

        assert f"Airplane Mode is now {'ON' if not initial_state else 'OFF'}" in result
        assert telecom_tools.device.airplane_mode is not initial_state

        # Toggle back
        telecom_tools.toggle_airplane_mode()
        assert telecom_tools.device.airplane_mode is initial_state

    def test_turn_airplane_mode_on_off(self, telecom_tools: TelecomUserTools):
        telecom_tools.turn_airplane_mode_on()
        assert telecom_tools.device.airplane_mode is True
        status = telecom_tools.check_status_bar()
        assert "✈️ Airplane Mode" in status

        telecom_tools.turn_airplane_mode_off()
        assert telecom_tools.device.airplane_mode is False
        status = telecom_tools.check_status_bar()
        assert "✈️ Airplane Mode" not in status

    def test_check_network_status(self, telecom_tools: TelecomUserTools):
        status_str = telecom_tools.check_network_status()
        assert "Airplane Mode: OFF" in status_str
        assert (
            f"SIM Card Status: {telecom_tools.device.sim_card_status.value}"
            in status_str
        )
        assert (
            f"Cellular Signal: {telecom_tools.device.network_signal_strength.value}"
            in status_str
        )

    def test_check_sim_status(self, telecom_tools: TelecomUserTools):
        telecom_tools.device.sim_card_status = SimStatus.ACTIVE
        assert "SIM card is active" in telecom_tools.check_sim_status()

        telecom_tools.device.sim_card_missing = True
        assert "No SIM card detected" in telecom_tools.check_sim_status()
        telecom_tools.device.sim_card_missing = False

        telecom_tools.device.sim_card_status = SimStatus.LOCKED_PIN
        assert "locked with a PIN" in telecom_tools.check_sim_status()

    def test_reseat_sim_card(self, telecom_tools: TelecomUserTools):
        telecom_tools.unseat_sim_card()
        assert telecom_tools._check_sim_status() == SimStatus.MISSING
        telecom_tools.reseat_sim_card()
        assert telecom_tools._check_sim_status() != SimStatus.MISSING
        # Assuming reseating triggers a network search and connects if possible
        assert telecom_tools.device.network_connection_status == NetworkStatus.CONNECTED

    def test_toggle_data(self, telecom_tools: TelecomUserTools):
        initial_data_state = telecom_tools.device.data_enabled
        result = telecom_tools.toggle_data()
        assert telecom_tools.device.data_enabled is not initial_data_state
        assert (
            f"Mobile Data is now {'ON' if not initial_data_state else 'OFF'}" in result
        )

    def test_toggle_roaming(self, telecom_tools: TelecomUserTools):
        initial_roaming_state = telecom_tools.device.roaming_enabled
        result = telecom_tools.toggle_roaming()
        assert telecom_tools.device.roaming_enabled is not initial_roaming_state
        assert (
            f"Data Roaming is now {'ON' if not initial_roaming_state else 'OFF'}"
            in result
        )

    def test_set_network_mode_preference(self, telecom_tools: TelecomUserTools):
        result = telecom_tools.set_network_mode_preference(
            NetworkModePreference.FOUR_G_ONLY
        )
        assert "Preferred Network Mode set to: 4g_only" in result
        assert (
            telecom_tools.device.network_mode_preference
            == NetworkModePreference.FOUR_G_ONLY
        )
        # Check if network search simulates a change (simplified check)
        assert (
            telecom_tools.device.network_technology_connected
            == NetworkTechnology.FOUR_G
        )

        result = telecom_tools.set_network_mode_preference("invalid_mode")
        assert "Failed to set network mode" in result

    def test_check_apn_settings(self, telecom_tools: TelecomUserTools):
        default_apn = APNSettings()
        telecom_tools.device.active_apn_settings = default_apn
        settings_str = telecom_tools.check_apn_settings()
        assert f"Current APN Name: {default_apn.apn_name.value}" in settings_str
        assert (
            f"MMSC URL (for picture messages): {default_apn.mmsc_url}" in settings_str
        )

    def test_set_apn_settings(self, telecom_tools: TelecomUserTools):
        # Test setting APN with APNSettings object
        new_apn = APNSettings(
            apn_name=APNNames.INTERNET,
            mmsc_url="http://mms.new.com",
            mms_apn="mms",
            reset_at_reboot=False,
        )
        result = telecom_tools.set_apn_settings(new_apn)
        assert f"APN settings set to: {APNNames.INTERNET.value}" in result
        assert "Status Bar:" in result
        assert telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET
        assert telecom_tools.device.active_apn_settings.mmsc_url == "http://mms.new.com"
        # Network search should be triggered
        assert telecom_tools.device.network_connection_status == NetworkStatus.CONNECTED

        # Test setting APN with dict
        result = telecom_tools.set_apn_settings(
            {
                "apn_name": APNNames.INTERNET,
                "mmsc_url": "http://mms.new.com",
                "mms_apn": "mms",
                "reset_at_reboot": False,
            }
        )
        assert f"APN settings set to: {APNNames.INTERNET.value}" in result
        assert "Status Bar:" in result
        assert telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET
        # Network search should be triggered again
        assert telecom_tools.device.network_connection_status == NetworkStatus.CONNECTED

    def test_reset_apn_settings(self, telecom_tools: TelecomUserTools):
        # Set custom APN settings
        custom_apn = APNSettings(
            apn_name=APNNames.INTERNET,
            mmsc_url="http://mms.new.com",
            mms_apn="mms",
            reset_at_reboot=False,
        )
        telecom_tools.device.active_apn_settings = custom_apn
        assert telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET
        assert not telecom_tools.device.active_apn_settings.reset_at_reboot

        # Call reset_apn_settings
        result = telecom_tools.reset_apn_settings()
        assert "APN settings will reset at reboot" in result
        assert telecom_tools.device.active_apn_settings.reset_at_reboot is True
        # APN settings should not be reset yet
        assert telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET

        # Now reboot to trigger the actual reset
        telecom_tools.reboot_device()
        assert (
            telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET
        )  # Default APN name
        assert not telecom_tools.device.active_apn_settings.reset_at_reboot

    def test_check_wifi_status(self, telecom_tools: TelecomUserTools):
        telecom_tools.device.wifi_enabled = False
        assert "Wi-Fi is turned OFF" in telecom_tools.check_wifi_status()

        telecom_tools.device.wifi_enabled = True
        telecom_tools.device.wifi_connected = False
        assert "Wi-Fi is ON but not connected" in telecom_tools.check_wifi_status()

        telecom_tools.device.wifi_connected = True
        telecom_tools.device.wifi_ssid = "MyHomeWiFi"
        telecom_tools.device.wifi_signal_strength = SignalStrength.GOOD
        status_str = telecom_tools.check_wifi_status()
        assert "Wi-Fi is ON and connected to 'MyHomeWiFi'" in status_str
        assert "Signal strength: good" in status_str

    def test_toggle_wifi(self, telecom_tools: TelecomUserTools):
        telecom_tools.device.airplane_mode = False  # Ensure wifi can be toggled
        initial_wifi_state = telecom_tools.device.wifi_enabled
        result = telecom_tools.toggle_wifi()
        assert telecom_tools.device.wifi_enabled is not initial_wifi_state
        assert f"Wi-Fi is now {'ON' if not initial_wifi_state else 'OFF'}" in result

        # Test when airplane mode is ON
        telecom_tools.device.airplane_mode = True
        telecom_tools.device.wifi_enabled = False  # Try to toggle wifi on
        result = telecom_tools.toggle_wifi()
        assert "Cannot change Wi-Fi settings while Airplane Mode is ON" in result
        assert telecom_tools.device.wifi_enabled is False  # State should not change

    def test_check_vpn_status(self, telecom_tools: TelecomUserTools):
        telecom_tools.device.vpn_enabled_setting = False
        telecom_tools.device.vpn_connected = False
        assert "VPN is turned OFF" in telecom_tools.check_vpn_status()

        telecom_tools.device.vpn_enabled_setting = True
        assert (
            "VPN is turned ON in settings, but currently not connected"
            in telecom_tools.check_vpn_status()
        )

        telecom_tools.device.vpn_connected = True
        telecom_tools.device.vpn_details = VpnDetails(
            server_address="1.2.3.4", protocol="TestVPN"
        )
        status_str = telecom_tools.check_vpn_status()
        assert "VPN is ON and connected. Details:" in status_str
        assert "'server_address': '1.2.3.4'" in status_str  # Check for detail presence

    def test_connect_disconnect_vpn(self, telecom_tools: TelecomUserTools):
        # Connect VPN
        telecom_tools.device.vpn_enabled_setting = True  # Assume setting is on
        result = telecom_tools.connect_vpn()
        assert "VPN connected successfully" in result
        assert telecom_tools.device.vpn_connected is True
        assert telecom_tools.device.vpn_details is not None
        assert (
            telecom_tools.device.vpn_details.server_address
            == telecom_tools.default_vpn_details.server_address
        )

        # Try connecting again
        result = telecom_tools.connect_vpn()
        assert "VPN already connected" in result

        # Disconnect VPN
        result = telecom_tools.disconnect_vpn()
        assert "VPN disconnected successfully" in result
        assert telecom_tools.device.vpn_connected is False
        assert telecom_tools.device.vpn_details is None

        # Try disconnecting again
        result = telecom_tools.disconnect_vpn()
        assert "No active VPN connection to disconnect" in result

    def test_check_installed_apps(self, telecom_tools: TelecomUserTools):
        apps_str = telecom_tools.check_installed_apps()
        assert "messaging" in apps_str
        assert "browser" in apps_str

    def test_check_app_status(self, telecom_tools: TelecomUserTools):
        status_str = telecom_tools.check_app_status("messaging")
        assert "Status for App: messaging" in status_str
        assert (
            "Permissions: None granted" in status_str
        )  # Default permissions are all False

        status_str = telecom_tools.check_app_status("browser")
        assert "network" in status_str

        status_str = telecom_tools.check_app_status("nonexistent_app")
        assert "App 'nonexistent_app' not found" in status_str

    def test_check_app_permissions(self, telecom_tools: TelecomUserTools):
        perms_str = telecom_tools.check_app_permissions("messaging")
        assert "App 'messaging' currently has no permissions granted" in perms_str

        telecom_tools.device.app_statuses["messaging"].permissions.storage = True
        perms_str = telecom_tools.check_app_permissions("messaging")
        assert "App 'messaging' has permission for: storage" in perms_str

    def test_grant_app_permission(self, telecom_tools: TelecomUserTools):
        app_name = "messaging"
        permission = "storage"

        assert telecom_tools.device.app_statuses[app_name].permissions.storage is False
        result = telecom_tools.grant_app_permission(app_name, permission)
        assert f"Permission '{permission}' granted to app '{app_name}'" in result
        assert telecom_tools.device.app_statuses[app_name].permissions.storage is True

        result = telecom_tools.grant_app_permission(app_name, "invalid_permission")
        assert "Permission 'invalid_permission' not tracked" in result

        result = telecom_tools.grant_app_permission("nonexistent_app", permission)
        assert "App 'nonexistent_app' not found" in result

    def test_remove_app_permission(self, telecom_tools: TelecomUserTools):
        app_name = "browser"  # browser has network=True by default in fixture
        permission_to_remove = "network"

        assert telecom_tools.device.app_statuses[app_name].permissions.network is True
        success, message = telecom_tools.remove_app_permission(
            app_name, permission_to_remove
        )
        assert success is True
        assert (
            f"Permission '{permission_to_remove}' removed from app '{app_name}'"
            in message
        )
        assert telecom_tools.device.app_statuses[app_name].permissions.network is False

        telecom_tools.device.app_statuses[app_name].permissions.storage = False
        # Try removing a permission that is already false
        success, message = telecom_tools.remove_app_permission(
            app_name, "storage"
        )  # storage is False
        assert success is True
        assert telecom_tools.device.app_statuses[app_name].permissions.storage is False

    def test_reboot_device(self, telecom_tools: TelecomUserTools):
        # Test APN reset functionality
        telecom_tools.device.active_apn_settings.reset_at_reboot = True
        telecom_tools.device.active_apn_settings.apn_name = APNNames.INTERNET
        result = telecom_tools.reboot_device()
        assert "Resetting APN settings..." in result
        assert (
            telecom_tools.device.active_apn_settings.apn_name == APNNames.INTERNET
        )  # Default APN name
        assert not telecom_tools.device.active_apn_settings.reset_at_reboot

        # Test network service restart
        telecom_tools.device.network_connection_status = NetworkStatus.CONNECTED
        telecom_tools.device.network_technology_connected = NetworkTechnology.FOUR_G
        telecom_tools.device.network_signal_strength = SignalStrength.GOOD

        result = telecom_tools.reboot_device()
        assert "Restarting network services..." in result
        assert telecom_tools.device.network_connection_status == NetworkStatus.CONNECTED

    def test_can_send_mms(self, telecom_tools: TelecomUserTools):
        # Setup for successful MMS
        telecom_tools.device.network_connection_status = NetworkStatus.CONNECTED
        telecom_tools.device.data_enabled = True
        telecom_tools.surroundings.mobile_data_usage_exceeded = False
        telecom_tools.device.network_technology_connected = NetworkTechnology.FOUR_G
        telecom_tools.device.wifi_calling_enabled = False
        telecom_tools.device.active_apn_settings.mmsc_url = "http://mms.example.com"
        telecom_tools.device.app_statuses["messaging"].permissions.sms = True
        telecom_tools.device.app_statuses["messaging"].permissions.storage = True
        assert (
            "Your messaging app can send MMS messages." in telecom_tools.can_send_mms()
        )

        # Test various failure conditions
        telecom_tools.device.network_connection_status = NetworkStatus.NO_SERVICE
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.device.network_connection_status = (
            NetworkStatus.CONNECTED
        )  # Reset

        telecom_tools.device.data_enabled = False
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.device.data_enabled = True  # Reset

        telecom_tools.surroundings.mobile_data_usage_exceeded = True
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.surroundings.mobile_data_usage_exceeded = False  # Reset

        telecom_tools.device.network_technology_connected = NetworkTechnology.TWO_G
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.device.network_technology_connected = (
            NetworkTechnology.FOUR_G
        )  # Reset

        telecom_tools.device.wifi_calling_enabled = True
        telecom_tools.device.wifi_calling_mms_over_wifi = (
            True  # Carrier does not support
        )
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.device.wifi_calling_enabled = False  # Reset

        telecom_tools.device.active_apn_settings.mmsc_url = None
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )
        telecom_tools.device.active_apn_settings.mmsc_url = (
            "http://mms.example.com"  # Reset
        )

        telecom_tools.device.app_statuses["messaging"].permissions.sms = False
        assert (
            "Your messaging app cannot send MMS messages."
            in telecom_tools.can_send_mms()
        )

    def test_run_speed_test(self, telecom_tools: TelecomUserTools):
        # Basic connected state
        telecom_tools.device.airplane_mode = False
        telecom_tools.device.network_signal_strength = SignalStrength.GOOD
        telecom_tools.device.network_connection_status = NetworkStatus.CONNECTED
        telecom_tools.device.data_enabled = True
        telecom_tools.surroundings.mobile_data_usage_exceeded = False
        telecom_tools.device.network_technology_connected = NetworkTechnology.FOUR_G
        telecom_tools.device.data_saver_mode = False
        telecom_tools.device.vpn_connected = False

        result = telecom_tools.run_speed_test()
        assert "Mbps" in result
        assert "Good" in result  # 4G with Good signal

        # No connection
        telecom_tools.device.network_signal_strength = SignalStrength.NONE
        result = telecom_tools.run_speed_test()
        assert "Speed test failed: No Connection" in result
        telecom_tools.device.network_signal_strength = SignalStrength.GOOD  # Reset

        # Data saver mode
        telecom_tools.device.data_saver_mode = True
        result = telecom_tools.run_speed_test()
        # Speed should be lower, potentially affecting description
        # This needs careful checking based on the _run_speed_test logic
        assert "Mbps" in result
        telecom_tools.device.data_saver_mode = False  # Reset

        # Poor VPN
        telecom_tools.device.vpn_connected = True
        telecom_tools.device.vpn_details = VpnDetails(
            server_performance=PerformanceLevel.POOR
        )
        result = telecom_tools.run_speed_test()
        assert "Mbps" in result  # Speed should be very low
        telecom_tools.device.vpn_connected = False  # Reset

        # 5G Excellent
        telecom_tools.device.network_technology_connected = NetworkTechnology.FIVE_G
        telecom_tools.device.network_signal_strength = SignalStrength.EXCELLENT
        result = telecom_tools.run_speed_test()
        assert "Excellent" in result
