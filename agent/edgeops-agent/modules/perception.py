import json
import math
import time
from statistics import mean, median, stdev


def _safe_get(d, *keys, default=None):
    v = d
    try:
        for k in keys:
            v = v[k]
        return v
    except Exception:
        return default


def _ptc_type_label(ptc_type):
    try:
        n = int(ptc_type)
    except Exception:
        return "U"
    return {
        1: "M",
        2: "nonM",
        3: "P",
        0: "U"
    }.get(n, "U")


def analyze_rsm(payload, max_speed_threshold=3000):
    """对 rsm/up 消息做基础感知分析。

    返回结构：{
      'summary': {...},
      'objects': [ {id, ptcType, pos, speed, heading, bbox, anomalies: []}, ... ]
    }

    假设输入 payload 已为 dict（MQTT 客户端在收到时会尝试解析 JSON）。
    """
    if not isinstance(payload, dict):
        return {"error": "payload is not a dict"}

    rsms = payload.get("rsms") or []
    objs = []
    speeds = []

    for rsm in rsms:
        participants = rsm.get("participants") or []
        # try to capture a frame-level timestamp if present
        frame_ts = rsm.get('ts') or rsm.get('timestamp') or rsm.get('frame_ts') or None
        for p in participants:
            # keep both globalId and ptcId; front-end prefers ptcId
            gid = p.get("globalId")
            pid = p.get("ptcId")
            pos = p.get("pos") or {}
            lon = _safe_get(p, "pos", "lon", default=None)
            lat = _safe_get(p, "pos", "lat", default=None)
            speed = p.get("speed")
            heading = p.get("heading")
            size = p.get("size") or {}

            ptc_type = p.get("ptcType")
            obj = {
                "id": gid,
                "ptcId": pid,
                "ptcType": ptc_type,
                "type_label": _ptc_type_label(ptc_type),
                "type": p.get("type") or _ptc_type_label(ptc_type),
                "pos": {"lon": lon, "lat": lat},
                "speed": speed,
                "heading": heading,
                "size": size,
                "frame_ts": frame_ts,
                "anomalies": []
            }

            # basic checks
            if lon is None or lat is None:
                obj["anomalies"].append("missing_position")
            else:
                if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
                    obj["anomalies"].append("position_out_of_bounds")

            if speed is None:
                obj["anomalies"].append("missing_speed")
            else:
                try:
                    sp = float(speed)
                    speeds.append(sp)
                    if sp < 0 or sp > max_speed_threshold:
                        obj["anomalies"].append("speed_out_of_range")
                except Exception:
                    obj["anomalies"].append("bad_speed_value")

            if heading is None:
                obj["anomalies"].append("missing_heading")
            else:
                try:
                    hd = float(heading)
                    # heading unit unknown; flag extreme values outside 0..65535
                    if hd < 0 or hd > 65535:
                        obj["anomalies"].append("heading_out_of_range")
                except Exception:
                    obj["anomalies"].append("bad_heading_value")

            # size sanity
            w = size.get("width") if isinstance(size, dict) else None
            l = size.get("length") if isinstance(size, dict) else None
            if w is not None and l is not None:
                try:
                    if w <= 0 or l <= 0:
                        obj["anomalies"].append("invalid_size")
                except Exception:
                    obj["anomalies"].append("bad_size")

            # build a simple axis-aligned bbox around pos using size (approximate)
            bbox = None
            try:
                if lon is not None and lat is not None and l and w:
                    # approximate degrees per meter (very rough, valid for small areas)
                    meters_per_deg_lat = 111320
                    meters_per_deg_lon = 40075000 * math.cos(math.radians(lat)) / 360.0
                    half_len_deg = (l / 2.0) / meters_per_deg_lon if meters_per_deg_lon else (l / 2.0) / 111320
                    half_wid_deg = (w / 2.0) / meters_per_deg_lat
                    bbox = [
                        [lon - half_len_deg, lat - half_wid_deg],
                        [lon - half_len_deg, lat + half_wid_deg],
                        [lon + half_len_deg, lat + half_wid_deg],
                        [lon + half_len_deg, lat - half_wid_deg],
                        [lon - half_len_deg, lat - half_wid_deg]
                    ]
            except Exception:
                bbox = None

            obj["bbox"] = bbox
            objs.append(obj)

    summary = {
        "total": len(objs),
        "by_ptcType": {},
        "avg_speed": None,
        "median_speed": None,
        "speed_std": None
    }

    for o in objs:
        k = str(o.get("ptcType"))
        summary["by_ptcType"][k] = summary["by_ptcType"].get(k, 0) + 1

    if speeds:
        try:
            summary["avg_speed"] = mean(speeds)
            summary["median_speed"] = median(speeds)
            summary["speed_std"] = stdev(speeds) if len(speeds) > 1 else 0.0
        except Exception:
            pass

    # further anomaly: mark speed outliers (z-score > 3)
    if speeds and len(speeds) > 1:
        mu = summary.get("avg_speed")
        sigma = summary.get("speed_std") or 0.0
        if sigma > 0:
            for o in objs:
                try:
                    if o.get("speed") is not None:
                        z = (float(o.get("speed")) - mu) / sigma
                        if abs(z) > 3:
                            if "speed_outlier" not in o["anomalies"]:
                                o["anomalies"].append("speed_outlier")
                except Exception:
                    continue

    result = {"summary": summary, "objects": objs, "timestamp": int(time.time())}
    return result


def generate_map_geojson(objects):
    """将分析后的 objects 列表转为 GeoJSON FeatureCollection，用于可视化。

    每个 object 的 geometry 使用点（pos），properties 包含 anomalies 和 id。
    """
    features = []
    for o in objects:
        lon = _safe_get(o, "pos", "lon")
        lat = _safe_get(o, "pos", "lat")
        if lon is None or lat is None:
            continue
        props = {
            "id": o.get("id"),
            "ptcId": o.get("ptcId"),
            "ptcType": o.get("ptcType"),
            "type": o.get("type") or o.get("type_label"),
            "size": o.get("size"),
            "frame_ts": o.get("frame_ts"),
            "speed": o.get("speed"),
            "heading": o.get("heading"),
            "anomalies": list(o.get("anomalies", []))
        }
        color = "red" if props["anomalies"] else "blue"
        props["marker-color"] = color
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props
        })

    return {"type": "FeatureCollection", "features": features}


def save_map_html(geojson, out_path="/tmp/perception_map.html", title="Perception Map"):
    """生成一个简单的 Leaflet HTML 地图文件，显示 GeoJSON，异常目标为红色。"""
    try:
        geojson_str = json.dumps(geojson)
    except Exception:
        geojson_str = "{}"

    html_template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>%%TITLE%%</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>#map { height: 100vh; width: 100%; }</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  const data = %%GEOJSON%%;
  const map = L.map('map');
  const features = data.features || [];
  if (features.length === 0) {
    map.setView([0,0], 2);
  } else {
    const first = features[0].geometry.coordinates;
    map.setView([first[1], first[0]], 16);
  }
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
  function styleFeature(feature){
    const anomalies = feature.properties.anomalies || [];
    return { radius: 6, fillColor: anomalies.length? 'red':'blue', color: '#000', weight:1, opacity:1, fillOpacity:0.8 }
  }
  L.geoJSON(data, {
    pointToLayer: function(feature, latlng){
      return L.circleMarker(latlng, styleFeature(feature));
    },
    onEachFeature: function(feature, layer){
      const p = feature.properties || {};
      layer.bindPopup(JSON.stringify(p));
    }
  }).addTo(map);
</script>
</body>
</html>
"""

    html = html_template.replace('%%TITLE%%', title).replace('%%GEOJSON%%', geojson_str)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


if __name__ == "__main__":
    # 简单的自测：读取 sample.json（如果存在），生成 map
    try:
        import sys
        if len(sys.argv) > 1:
            path = sys.argv[1]
            with open(path, 'r', encoding='utf-8') as f:
                payload = json.load(f)
            res = analyze_rsm(payload)
            gj = generate_map_geojson(res.get('objects', []))
            out = f"/tmp/perception_map_{int(time.time())}.html"
            save_map_html(gj, out)
            print('map saved to', out)
    except Exception:
        pass


## ------------------ 跨帧追踪与 CSV 解析支持 ------------------
def _haversine_m(lon1, lat1, lon2, lat2):
    # 返回两点间近似米距离
    try:
        R = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except Exception:
        return None


class SimpleTracker:
    """简单的跨帧追踪器，基于 TargetID 建连。保持有限长度历史并检查一致性。"""
    def __init__(self, max_history=5, speed_jump_thresh=50.0, heading_diff_thresh=45.0):
        # tracks: target_id -> list of detections (dict)
        self.tracks = {}
        self.max_history = max_history
        self.speed_jump_thresh = speed_jump_thresh
        self.heading_diff_thresh = heading_diff_thresh

    def update(self, detections):
        """传入单帧 detections 列表，每项包含至少 'id','lon','lat','ts','speed','heading','type' 等字段。"""
        anomalies = {}
        for det in detections:
            tid = det.get('id')
            if tid is None:
                continue
            hist = self.tracks.get(tid, [])
            # append
            hist.append(det)
            if len(hist) > self.max_history:
                hist.pop(0)
            self.tracks[tid] = hist

            # run consistency checks against previous
            ann = []
            if len(hist) >= 2:
                prev = hist[-2]
                # compute dt
                try:
                    dt = float(det.get('ts', det.get('timestamp', 0))) - float(prev.get('ts', prev.get('timestamp', 0)))
                    if dt <= 0:
                        dt = None
                except Exception:
                    dt = None

                # position jump
                if prev.get('lon') is not None and prev.get('lat') is not None and det.get('lon') is not None and det.get('lat') is not None:
                    dist = _haversine_m(prev['lon'], prev['lat'], det['lon'], det['lat'])
                    if dist is not None and dt:
                        implied_speed = dist / dt if dt else None
                        # compare implied speed to reported speed
                        try:
                            rep_speed = float(det['speed'])
                        except Exception:
                            rep_speed = None
                        if implied_speed is not None and implied_speed > (self.speed_jump_thresh):
                            ann.append('position_jump')
                        if rep_speed is not None and implied_speed is not None and abs(implied_speed - rep_speed) > max(5.0, 0.5*rep_speed):
                            ann.append('speed_inconsistent')

                # heading change
                try:
                    h1 = float(prev.get('heading'))
                    h2 = float(det.get('heading'))
                    diff = abs((h2 - h1 + 180) % 360 - 180)
                    if diff > self.heading_diff_thresh:
                        ann.append('heading_jump')
                except Exception:
                    pass

                # type/category change
                if prev.get('type') is not None and det.get('type') is not None:
                    if str(prev.get('type')) != str(det.get('type')):
                        
                        ann.append('type_changed')

            anomalies[tid] = ann

        return anomalies


def parse_csv_frames(csv_text):
    """解析用户给出的 CSV 文本，按 FrameID 组织成 frames 列表。

    返回: list of frames, each frame is {frame_id: int, ts: float, detections: [ {id,lon,lat,ts,speed,heading,type,L,W,H} ] }
    """
    lines = [l.strip() for l in csv_text.strip().splitlines() if l.strip()]
    if not lines:
        return []
    header = [h.strip() for h in lines[0].split(',')]
    frames = {}
    for row in lines[1:]:
        parts = [p.strip() for p in row.split(',')]
        if len(parts) != len(header):
            # allow some malformed lines by skipping
            continue
        rec = dict(zip(header, parts))
        try:
            frame_id = int(rec.get('FrameID', rec.get('frameid', 0)))
        except Exception:
            frame_id = 0
        try:
            ts = float(rec.get('ts', rec.get('TS', 0)))
        except Exception:
            ts = None

        # extract fields
        try:
            lon = float(rec.get('Lon')) if rec.get('Lon') not in (None, '', '-1') else None
        except Exception:
            lon = None
        try:
            lat = float(rec.get('Lat')) if rec.get('Lat') not in (None, '', '-1') else None
        except Exception:
            lat = None
        try:
            speed = float(rec.get('Vel')) if rec.get('Vel') not in (None, '', '-1') else None
        except Exception:
            speed = None
        try:
            heading = float(rec.get('Heading')) if rec.get('Heading') not in (None, '', '-1') else None
        except Exception:
            heading = None
        tid = rec.get('TargetID') or rec.get('TargetId') or rec.get('Target')
        typ = rec.get('Type')
        try:
            L = float(rec.get('L')) if rec.get('L') not in (None, '', '-1') else None
        except Exception:
            L = None
        try:
            W = float(rec.get('W')) if rec.get('W') not in (None, '', '-1') else None
        except Exception:
            W = None
        try:
            H = float(rec.get('H')) if rec.get('H') not in (None, '', '-1') else None
        except Exception:
            H = None

        det = {
            'id': tid,
            'lon': lon,
            'lat': lat,
            'ts': ts,
            'speed': speed,
            'heading': heading,
            'type': typ,
            'L': L, 'W': W, 'H': H
        }
        frames.setdefault(frame_id, {'frame_id': frame_id, 'ts': ts, 'detections': []})['detections'].append(det)

    # return sorted frames
    return [frames[k] for k in sorted(frames.keys())]


def analyze_csv_frames(csv_text, tracker=None):
    """解析 CSV 并使用 SimpleTracker 做跨帧一致性检测。

    返回 { 'frames': [...], 'tracks': {...}, 'anomalies': {...} }
    """
    frames = parse_csv_frames(csv_text)
    if tracker is None:
        tracker = SimpleTracker()
    all_anomalies = {}
    for f in frames:
        dets = f.get('detections', [])
        anns = tracker.update(dets)
        all_anomalies[f['frame_id']] = anns

    # build tracks summary
    tracks_summary = {}
    for tid, hist in tracker.tracks.items():
        tracks_summary[tid] = {
            'history': hist,
            'last_seen': hist[-1].get('ts') if hist else None
        }

    return {
        'frames': frames,
        'tracks': tracks_summary,
        'anomalies': all_anomalies,
        'timestamp': int(time.time())
    }

