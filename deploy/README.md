# Usage

Start the `docker-compose.yaml` service with the following command:

```bash
docker-compose up -d
```

After pulling two containers are started and the sync server is available at `http://localhost:8080`.

To log into the sync server, use the following credentials:
- **Username**: `user`
- **Password**: `dummy`

Those can be changed in the `resilio-config.conf` file in the `webui` section.
After changing the credentials, please also adjust the `eti-config.yaml` file.

## Predefined Hosts Mode

When using `predefined_hosts` in your `eti-config.yaml`, you may want to disable tracker servers to rely solely on direct peer connections. To do this, set the `USE_PREDEFINED_HOSTS_ONLY` environment variable to `true` in the `docker-compose.yaml`:

```yaml
environment:
  USE_PREDEFINED_HOSTS_ONLY: "true"
```

This will disable tracker servers while keeping relay servers active. If you want to disable both trackers and relay servers (full offline mode), use `IS_ONLINE: "false"` instead.

## Advanced Usage

To clean up installed games and data of the sync server the container can be started with a alternative command:

```bash
docker run --rm -it ghcr.io/poeschl/peti-server:latest --config /path/to/eti-config.yaml cleanup
```

After a security question, the sync server will be cleaned up and all data will be removed.
