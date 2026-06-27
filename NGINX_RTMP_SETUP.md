# Nginx RTMP + HLS Streaming Setup

This repository now supports the following livestream flow:

OBS Studio -> RTMP -> Nginx RTMP server -> HLS -> Django website viewers

## 1. What was added

- `missions.models.Pastor.stream_key`
  - Each pastor now has a unique RTMP/HLS stream key.
- `missions/admin.py`
  - Pastor admin now shows `stream_key`.
- `missions/views.py`
  - `live_stream_view` now passes RTMP and HLS URL templates to the template.
  - `get_pastors_api` now returns `stream_key` with each pastor result.
  - `notify_rtmp_publish` endpoint receives Nginx RTMP publish notifications.
- `templates/live_stream.html`
  - Viewer page uses HLS.js to play `http://<host>/hls/<stream_key>.m3u8`
  - Pastors see OBS / RTMP setup instructions.
- `nginx_rtmp.conf`
  - Nginx configuration file for RTMP ingest and HLS output.

## 2. Nginx RTMP configuration

Use the provided `nginx_rtmp.conf` in an Nginx installation with the RTMP module enabled.

### Key settings

- RTMP port: `1935`
- RTMP application: `live`
- HLS output path: `/tmp/nginx-rtmp/hls`
- HLS playback endpoint: `http://<server>:8080/hls/<stream_key>.m3u8`
- Nginx hooks:
  - `on_publish` → notifies Django when OBS starts streaming
  - `on_publish_done` → notifies Django when OBS stops streaming

## 3. OBS Studio settings

For each pastor channel:

- Server / RTMP URL:
  - `rtmp://<your-server-host>/live`
- Stream key:
  - Use the pastor's `stream_key` shown on the live stream page

Example:

- RTMP URL: `rtmp://example.com/live`
- Stream key: `john-wb`

## 4. How the Django page works

### For pastors
- Select your pastor channel
- Copy the stream key shown on the page
- Start streaming from OBS
- Nginx RTMP will ingest the stream and output HLS
- The Django page will detect the live channel and enable playback

### For viewers
- Select a state and pastor channel
- Click `Tune In`
- The page polls Django for whether the stream is active
- If active, the page loads the HLS playlist via HLS.js

## 5. Migration and data update

The new `stream_key` field was added to the `Pastor` model and existing pastor records were populated automatically.

If you need to recreate the migration or verify the field, run:

```bash
python manage.py makemigrations missions
python manage.py migrate
```

## 6. Notes

- The Django app assumes the Nginx HLS server is available at the same host under port `8080`.
- If you use a different host or port, update `live_stream_view` and `nginx_rtmp.conf` accordingly.
- If you want to deploy to production, configure Nginx to proxy `/hls` and secure HTTP access.
