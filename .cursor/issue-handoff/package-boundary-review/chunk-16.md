# Chunk 16 — pools and shared

## Findings

- `nornir_pools` is the right home for `submit_bounded`. Segmentation `poolutil.submit_bounded` and `tile._submit_bounded` are the same window. Callers: stitch/mask jobs and per-tile pipeline tasks. Output: tasks yielded in submission order, at most `max_in_flight` queued.
- `run_process_jobs` is segmentation-specific (in-process when `workers <= 1`, `GetMultithreadingPool` otherwise). It can stay, and call the shared submit helper.
- `nornir_shared` correctly owns MQTT (`mqtt_telemetry`) and `prettyoutput`. The trainer already limits itself to that edge. Do not move image or catalog code into shared.
- `poolutil`’s comment that `GetMultithreadingPool` runs processes is a naming trap. The helper should document that at the pools call site, not grow a second pool type.

## Carry forward

One bounded-submit function in pools.
