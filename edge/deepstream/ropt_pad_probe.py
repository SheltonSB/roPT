"""
ropt_pad_probe.py
DeepStream Python app with a pad probe that sends zone events to the backend.

This replaces running deepstream-app (demo-only) by attaching custom logic:
- compute "feet" point (bottom-center of person bbox)
- check zone membership with Shapely
- emit ENTER/EXIT events to FastAPI /events
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import requests
from shapely.geometry import Point, Polygon

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib  # noqa: E402

import pyds  # noqa: E402


@dataclass
class Zone:
    zone_id: str
    polygon: Polygon


@dataclass
class ProbeContext:
    backend_url: str
    zones: List[Zone]
    person_class_id: int
    inside_state: Dict[str, Dict[str, bool]] = field(default_factory=dict)


def load_zones(path: str) -> List[Zone]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    zones = []
    for z in data.get("zones", []):
        polygon = Polygon(z["polygon"])
        zones.append(Zone(zone_id=z["zone_id"], polygon=polygon))
    return zones


def fetch_zones(backend_url: str) -> List[Zone]:
    resp = requests.get(f"{backend_url.rstrip('/')}/zones", timeout=3)
    resp.raise_for_status()
    data = resp.json()
    zones = []
    for z in data.get("zones", []):
        polygon = Polygon(z["polygon"])
        zones.append(Zone(zone_id=z["zone_id"], polygon=polygon))
    return zones


def post_event(backend_url: str, evt: dict, retries: int = 5) -> None:
    url = f"{backend_url.rstrip('/')}/events"
    backoff_s = 0.5
    for attempt in range(retries):
        try:
            resp = requests.post(url, json=evt, timeout=2)
            resp.raise_for_status()
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(backoff_s)
            backoff_s = min(backoff_s * 2, 5.0)


def _ensure_actor_state(ctx: ProbeContext, actor_id: str) -> Dict[str, bool]:
    if actor_id not in ctx.inside_state:
        ctx.inside_state[actor_id] = {}
    return ctx.inside_state[actor_id]


def _emit_zone_transitions(ctx: ProbeContext, actor_id: str, foot: Tuple[float, float]) -> None:
    point = Point(foot[0], foot[1])
    state = _ensure_actor_state(ctx, actor_id)
    ts_ms = int(time.time() * 1000)

    for zone in ctx.zones:
        inside = zone.polygon.contains(point)
        prev_inside = state.get(zone.zone_id, False)
        # Bandwidth control: emit only on transitions (ENTER/EXIT), never per-frame.
        if inside == prev_inside:
            continue
        state[zone.zone_id] = inside
        event_type = "HUMAN_ENTERED_ZONE" if inside else "HUMAN_EXITED_ZONE"
        evt = {
            "event_type": event_type,
            "ts_ms": ts_ms,
            "actor_id": actor_id,
            "zone_id": zone.zone_id,
            "payload": {"foot_x": foot[0], "foot_y": foot[1]},
        }
        post_event(ctx.backend_url, evt)


def osd_sink_pad_buffer_probe(pad, info, ctx: ProbeContext):
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        return Gst.PadProbeReturn.OK

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        l_obj = frame_meta.obj_meta_list
        while l_obj:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            if obj_meta.class_id == ctx.person_class_id:
                rect = obj_meta.rect_params
                foot_x = rect.left + rect.width / 2.0
                foot_y = rect.top + rect.height
                actor_id = f"person_{obj_meta.object_id}"
                _emit_zone_transitions(ctx, actor_id, (foot_x, foot_y))

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def cb_newpad(decodebin, decoder_src_pad, data):
    caps = decoder_src_pad.get_current_caps()
    caps_struct = caps.get_structure(0)
    name = caps_struct.get_name()
    if "video" not in name:
        return
    bin_ = data
    ghost_pad = bin_.get_static_pad("src")
    ghost_pad.set_target(decoder_src_pad)


def create_source_bin(index: int, uri: str) -> Gst.Bin:
    bin_name = f"source-bin-{index}"
    bin_ = Gst.Bin.new(bin_name)
    if not bin_:
        raise RuntimeError("Unable to create source bin")

    uri_decode_bin = Gst.ElementFactory.make("uridecodebin", f"uri-decode-{index}")
    uri_decode_bin.set_property("uri", uri)
    uri_decode_bin.connect("pad-added", cb_newpad, bin_)

    Gst.Bin.add(bin_, uri_decode_bin)
    bin_.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
    return bin_


def build_pipeline(uri: str, pgie_config: str, mux_width: int, mux_height: int) -> Gst.Pipeline:
    pipeline = Gst.Pipeline.new("ropt-pipeline")

    streammux = Gst.ElementFactory.make("nvstreammux", "streammux")
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", mux_width)
    streammux.set_property("height", mux_height)
    streammux.set_property("batched-push-timeout", 33000)

    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    pgie.set_property("config-file-path", pgie_config)

    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvideo-converter")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    sink = Gst.ElementFactory.make("fakesink", "fake-sink")

    if not all([pipeline, streammux, pgie, nvvidconv, nvosd, sink]):
        raise RuntimeError("Failed to create GStreamer elements")

    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)

    source_bin = create_source_bin(0, uri)
    pipeline.add(source_bin)

    sinkpad = streammux.get_request_pad("sink_0")
    srcpad = source_bin.get_static_pad("src")
    srcpad.link(sinkpad)

    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(sink)

    return pipeline


def main():
    parser = argparse.ArgumentParser(description="roPT DeepStream pad probe")
    parser.add_argument("--backend-url", required=True, help="Backend base URL (http://127.0.0.1:8000)")
    parser.add_argument("--zones", help="Zones JSON file path")
    parser.add_argument(
        "--zones-from-backend",
        action="store_true",
        help="Fetch zones from backend /zones on startup",
    )
    parser.add_argument("--uri", required=True, help="Input URI (file:// or rtsp://)")
    parser.add_argument(
        "--pgie-config",
        default="/opt/nvidia/deepstream/deepstream-8.0/samples/configs/deepstream-app/config_infer_primary.txt",
        help="Primary GIE config file path",
    )
    parser.add_argument("--person-class-id", type=int, default=0, help="PGIE class id for person")
    parser.add_argument("--mux-width", type=int, default=1280)
    parser.add_argument("--mux-height", type=int, default=720)
    args = parser.parse_args()

    Gst.init(None)

    if args.zones_from_backend or not args.zones:
        zones = fetch_zones(args.backend_url)
    else:
        zones = load_zones(args.zones)
    if not zones:
        raise RuntimeError("No zones loaded. Provide zones JSON with a 'zones' array.")

    ctx = ProbeContext(
        backend_url=args.backend_url,
        zones=zones,
        person_class_id=args.person_class_id,
    )

    pipeline = build_pipeline(args.uri, args.pgie_config, args.mux_width, args.mux_height)

    osd_sink_pad = pipeline.get_by_name("onscreendisplay").get_static_pad("sink")
    osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, ctx)

    loop = GLib.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    main()
