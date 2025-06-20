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
