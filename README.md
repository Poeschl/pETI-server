# pETI-server

Create and manage your eti sync server with the help of a snake and a whale.

This is an alternative to the [official eti sync server](https://www.eti-lan.xyz/sync_server.php), but with some additional features.
I try to keep it as close to the official server as possible, so that you can use it without issues with the official eti lan-launcher.

# Changes / Additions

The main difference to the official server is that it runs only in a docker environment.

The additional features are:

* configuration as yaml file
* completely running in containers
* deny list for games which should not be synced in config file
* "Offline mode" which disables Resilio's trackers to disable downloading from new peers

# Usage

As a starting point, you can use the provided `docker-compose.yaml` file in the `deploy` folder.
With that a basic setup is created, which you can then adapt to your needs.

# Disclaimer

This project is not affiliated with the official eti sync server or the eti lan-launcher.
It is an independent project that aims to provide a similar functionality with some additional features.
