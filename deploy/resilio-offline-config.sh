#!/usr/bin/with-contenv bash
# shellcheck shell=bash

CONFIG_BASE="/config/sync-base.conf"
CONFIG_FILE="/config/sync.conf"

# Create a copy of the base config
cp "$CONFIG_BASE" "$CONFIG_FILE"

# Wait for the hosts file to be available
sleep 2

# Set settings based on IS_ONLINE environment variable
if [ "$IS_ONLINE" = "false" ]; then
    echo "Offline mode detected, configuring Resilio for LAN-only operation"

    # Update JSON settings for offline mode
    sed -i 's/"folder_defaults.use_tracker":.*$/"folder_defaults.use_tracker": false,/g' "$CONFIG_FILE"
    sed -i 's/"folder_defaults.use_relay":.*$/"folder_defaults.use_relay": false,/g' "$CONFIG_FILE"
    sed -i 's/"service_folders.use_tracker":.*$/"service_folders.use_tracker": false,/g' "$CONFIG_FILE"
    sed -i 's/"service_folders.use_relay":.*$/"service_folders.use_relay": false,/g' "$CONFIG_FILE"

    # Block tracker and relay information in hosts
    echo "127.0.0.1  config.resilio.com" >> /etc/hosts

elif [ "$IS_ONLINE" = "true" ]; then
    echo "Online mode detected, configuring Resilio for internet connectivity"

    # Update JSON settings for online mode
    sed -i 's/"folder_defaults.use_tracker":.*$/"folder_defaults.use_tracker": true,/g' "$CONFIG_FILE"
    sed -i 's/"folder_defaults.use_relay":.*$/"folder_defaults.use_relay": true,/g' "$CONFIG_FILE"
    sed -i 's/"service_folders.use_tracker":.*$/"service_folders.use_tracker": true,/g' "$CONFIG_FILE"
    sed -i 's/"service_folders.use_relay":.*$/"service_folders.use_relay": true,/g' "$CONFIG_FILE"

    # Allow tracker and relay information in hosts
    sed -i '/config.resilio.com/d' /etc/hosts
else
    echo "Warning: IS_ONLINE environment variable not set to true or false. Using default configuration."
fi

cat "$CONFIG_FILE"

# Exit with success
exit 0
