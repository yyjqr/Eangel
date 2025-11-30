import os
import threading
import json
from flask import Flask, jsonify, request, abort, render_template_string

app = Flask(__name__)

# Configurable paths (set before starting)
_DATA_PATH = None
_SNAP_DIR = None

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Perception Live Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>#map { height: 100vh; width: 100%; }</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
let geojson = {"type":"FeatureCollection","features":[]};
const map = L.map('map');

// control panel (checkboxes)
const controlHtml = `
  <div style="position:absolute; top:8px; right:8px; background:rgba(255,255,255,0.95); padding:8px; border-radius:4px; z-index:1000; font-family:Arial, Helvetica, sans-serif; font-size:12px;">
    <label><input type="checkbox" id="showIds" checked> Show IDs</label><br>
    <label><input type="checkbox" id="showTypes" checked> Show Types</label><br>
    <label><input type="checkbox" id="showOnlyAnom"> Show Only Anomalies</label><br>
  </div>
`;
document.body.insertAdjacentHTML('beforeend', controlHtml);
// when checkboxes change, refresh immediately so tooltips/update reflect new choices
document.getElementById('showIds').addEventListener('change', refresh);
document.getElementById('showTypes').addEventListener('change', refresh);
document.getElementById('showOnlyAnom').addEventListener('change', refresh);

function initMap(coords){
  if(!coords) map.setView([0,0],2);
  else map.setView(coords,16);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
}

// layers for markers and tracks
const markersLayer = L.layerGroup().addTo(map);
const tracksLayer = L.layerGroup().addTo(map);

// in-memory trajectory history: id -> [{lat, lon, ts},...]
const history = {};
const trackMeta = {};
const MAX_HISTORY = 500;
const TRACK_TTL_MS = 20000; // drop tracks older than 20 seconds
function normalizeTimestamp(ts){
  if(ts === null || ts === undefined) return Date.now();
  if(typeof ts === 'string'){
    const parsed = Date.parse(ts);
    if(!Number.isNaN(parsed)) return parsed;
  }
  let num = Number(ts);
  if(Number.isNaN(num)) return Date.now();
  if(num < 1e12) num = num * 1000; // assume seconds
  return num;
}

function pruneStaleTracks(nowMs){
  const cutoff = nowMs - TRACK_TTL_MS;
  for(const id of Object.keys(history)){
    const filtered = history[id].filter(entry => (entry.tsMs || 0) >= cutoff);
    if(filtered.length === 0){
      delete history[id];
      delete trackMeta[id];
    }else{
      history[id] = filtered;
      if(trackMeta[id]) trackMeta[id].lastTsMs = filtered[filtered.length - 1].tsMs;
    }
  }
}

function styleForFeature(feature){
  const anomalies = (feature.properties && feature.properties.anomalies) || [];
  let radius = 6;
  try{
    const sz = feature.properties && feature.properties.size;
    const length = sz && (sz.length || sz.len || sz['length']);
    if(length && Number(length) > 680) radius = 10;
  }catch(e){}
  return { radius: radius, fillColor: anomalies.length? 'red':'blue', color:'#000', weight:1, opacity:1, fillOpacity:0.8 };
}

function getVisibleId(props){
  return props.ptcId || props.ptcID || props.ptc_id || props.id || props.ID || props.targetId || props.target_id || null;
}

function getEmojiForTarget(props){
  const size = props && props.size ? props.size : {};
  const rawLength = size.length ?? size.len ?? size['length'];
  const lengthVal = rawLength !== undefined ? Number(rawLength) : null;
  const isLarge = lengthVal !== null && !Number.isNaN(lengthVal) && lengthVal > 680;

  if(props && props.ptcType !== undefined && props.ptcType !== null){
    const n = Number(props.ptcType);
    if(n === 1){
      return isLarge ? '🚛' : '🚗';
    }
    if(n === 2) return '🚲';
    if(n === 3) return '🚶';
    if(n === 0) return '❓';
  }

  if(props && props.type){
    const t = String(props.type).toLowerCase();
    if(t.includes('car') || t.includes('vehicle') || t.includes('truck') || t.includes('bus')){
      return isLarge ? '🚛' : '🚗';
    }
    if(t.includes('bicycle') || t.includes('bike') || t.includes('non-motor')) return '🚲';
    if(t.includes('ped') || t.includes('person') || t.includes('walker')) return '🚶';
  }

  if(isLarge) return '🚛';
  return '❓';
}

function normalizeHeading(value){
  if(value === null || value === undefined) return null;
  let h = Number(value);
  if(Number.isNaN(h)) return null;
  if(h > 360 && h <= 36000) h = h / 100.0;
  h = h % 360;
  if(h < 0) h += 360;
  return h;
}

function bearingDeg(lat1, lon1, lat2, lon2){
  if(lat1 === undefined || lon1 === undefined || lat2 === undefined || lon2 === undefined) return null;
  const φ1 = Number(lat1) * Math.PI / 180.0;
  const φ2 = Number(lat2) * Math.PI / 180.0;
  const λ1 = Number(lon1) * Math.PI / 180.0;
  const λ2 = Number(lon2) * Math.PI / 180.0;
  if([φ1, φ2, λ1, λ2].some(v => Number.isNaN(v))) return null;
  const y = Math.sin(λ2 - λ1) * Math.cos(φ2);
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(λ2 - λ1);
  let brng = Math.atan2(y, x);
  brng = (brng * 180.0 / Math.PI + 360.0) % 360.0;
  return brng;
}

function haversineMeters(lat1, lon1, lat2, lon2){
  if(lat1 === undefined || lon1 === undefined || lat2 === undefined || lon2 === undefined) return null;
  const φ1 = Number(lat1) * Math.PI / 180.0;
  const φ2 = Number(lat2) * Math.PI / 180.0;
  const dφ = (Number(lat2) - Number(lat1)) * Math.PI / 180.0;
  const dλ = (Number(lon2) - Number(lon1)) * Math.PI / 180.0;
  if([φ1, φ2, dφ, dλ].some(v => Number.isNaN(v))) return null;
  const a = Math.sin(dφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(dλ / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return 6371000 * c;
}

function angleDiff(a, b){
  if(a === null || a === undefined || b === null || b === undefined) return null;
  let d = Math.abs(Number(a) - Number(b)) % 360;
  if(Number.isNaN(d)) return null;
  if(d > 180) d = 360 - d;
  return d;
}

function createRotatedIcon(emoji, heading, highlight){
  const rotation = heading === null || heading === undefined ? 0 : heading;
  let color = '#000';
  if(highlight === 'reverse') color = 'red';
  else if(highlight === 'other') color = '#ff9800';
  const html = `<div style="transform: rotate(${rotation}deg); font-size:24px; line-height:24px; color:${color}; text-shadow:0 0 2px #fff;">${emoji}</div>`;
  return L.divIcon({html: html, className: 'custom-div-icon', iconSize: [28,28], iconAnchor: [14,14]});
}

function bindFeatureTooltipAndPopup(layer, feature){
  const props = feature.properties || {};
  const showIds = document.getElementById('showIds').checked;
  const showTypes = document.getElementById('showTypes').checked;
  let tooltip = '';
  const visibleId = getVisibleId(props);
  if(showIds && visibleId) tooltip += 'ID:' + visibleId;
  if(showTypes && props.type){ if(tooltip) tooltip += ' '; tooltip += 'Type:' + props.type; }
  if(tooltip) layer.bindTooltip(tooltip, {permanent:true, direction:'top', offset:[0,-8]});

  let popup = '<div style="font-family:Arial, Helvetica, sans-serif; font-size:13px">';
  if(visibleId) popup += '<b>ptcId:</b> ' + visibleId + '<br/>';
  if(props.type) popup += '<b>Type:</b> ' + props.type + '<br/>';
  if(props.size){
    const s = props.size;
    const length = s.length || s.len || s['length'] || '';
    popup += '<b>Size (W×L×H):</b> ' + (s.width||s.w||'') + '×' + (length||'') + '×' + (s.height||s.h||'') + '<br/>';
    try{ if(Number(length) > 680) popup += '<b>Class:</b> 大车<br/>';}catch(e){}
  }
  if(props.anomalies && props.anomalies.length){
    popup += '<b style="color:red">Anomalies:</b><ul>';
    for(let i=0;i<props.anomalies.length;i++) popup += '<li>' + props.anomalies[i] + '</li>';
    popup += '</ul>';
  } else {
    popup += '<i>No anomalies</i>';
  }
  popup += '</div>';
  layer.bindPopup(popup);
}

// start time info box
const infoBox = L.control({position: 'topleft'});
let startTimeUTC = null;
infoBox.onAdd = function (){
  const div = L.DomUtil.create('div', 'infoBox');
  div.style.background = 'rgba(255,255,255,0.9)';
  div.style.padding = '6px';
  div.style.borderRadius = '4px';
  div.style.fontSize = '12px';
  div.id = 'startTimeBox';
  div.innerHTML = 'Start: -';
  return div;
};
infoBox.addTo(map);

function addDataWithOptions(data){
  const showOnlyAnom = document.getElementById('showOnlyAnom').checked;
  markersLayer.clearLayers();
  tracksLayer.clearLayers();
  try{
    const nowMs = Date.now();
    pruneStaleTracks(nowMs);
    const features = data.features || [];
    for(const feature of features){
      const props = feature.properties || {};
      const anomalies = Array.isArray(props.anomalies) ? props.anomalies.slice() : [];
      props.anomalies = anomalies;

      const coords = feature.geometry && feature.geometry.coordinates;
      if(!coords) continue;
      const lon = coords[0];
      const lat = coords[1];
      if(lon === undefined || lat === undefined) continue;

      const id = getVisibleId(props) || ('tmp_' + Math.random().toString(36).substr(2,5));
      const tsMs = normalizeTimestamp(props.frame_ts || props.ts || nowMs);
      const currentType = (props.ptcType !== undefined && props.ptcType !== null) ? Number(props.ptcType) : null;

      history[id] = history[id] || [];
      const prevEntry = history[id].length ? history[id][history[id].length - 1] : null;

      let movementBearing = null;
      if(prevEntry){
        const dist = haversineMeters(prevEntry.lat, prevEntry.lon, lat, lon);
        if(dist !== null && dist > 0.5){
          movementBearing = bearingDeg(prevEntry.lat, prevEntry.lon, lat, lon);
        }
        if(prevEntry.ptcType !== null && currentType !== null && prevEntry.ptcType !== currentType){
          if(!anomalies.includes('type_changed')) anomalies.push('type_changed');
        }
      }

      const reportedHeading = normalizeHeading(props.heading !== undefined ? props.heading : props.Heading);
      if(movementBearing !== null && reportedHeading !== null){
        const diff = angleDiff(movementBearing, reportedHeading);
        if(diff !== null && diff > 130 && !anomalies.includes('reverse_heading')){
          anomalies.push('reverse_heading');
        }
      }

      const entry = {
        lat: lat,
        lon: lon,
        tsMs: tsMs,
        heading: reportedHeading,
        ptcType: currentType
      };
      history[id].push(entry);
      if(history[id].length > MAX_HISTORY) history[id].shift();

      trackMeta[id] = {
        anomalies: anomalies.slice(),
        ptcType: currentType
      };

      if(showOnlyAnom && anomalies.length === 0){
        continue;
      }

      const emoji = getEmojiForTarget(props);
      const headingForIcon = (reportedHeading !== null && reportedHeading !== undefined) ? reportedHeading : movementBearing;
      const highlightMode = anomalies.includes('reverse_heading') ? 'reverse' : (anomalies.length > 0 ? 'other' : null);
      const icon = createRotatedIcon(emoji, headingForIcon, highlightMode);
      const marker = L.marker([lat, lon], {icon});
      bindFeatureTooltipAndPopup(marker, feature);
      marker.addTo(markersLayer);
    }

    for(const id in history){
      const pts = history[id].map(p => [p.lat, p.lon]);
      if(pts.length > 1){
        const meta = trackMeta[id] || {};
        const anomalies = meta.anomalies || [];
        if(showOnlyAnom && anomalies.length === 0) continue;
        let color = '#3388ff';
        if(anomalies.includes('reverse_heading')) color = 'red';
        else if(anomalies.length > 0) color = '#ff9800';
        L.polyline(pts, {color: color, weight: 2, opacity: 0.85}).addTo(tracksLayer);
      }
    }
  }catch(e){
    console.error('render error', e);
  }
}

function refresh(){
  fetch('/perception/data')
    .then(r=>r.json())
    .then(data=>{
      if(!data || !data.features) return;
      // set start time if not set
      if(!startTimeUTC){
        if(data.properties && data.properties.start_time) startTimeUTC = data.properties.start_time;
        else if(data.features.length>0 && data.features[0].properties && data.features[0].properties.frame_ts) startTimeUTC = data.features[0].properties.frame_ts;
        else startTimeUTC = new Date().toISOString();
        try{ document.getElementById('startTimeBox').innerText = 'Start: ' + (new Date(startTimeUTC).toUTCString()); }catch(e){}
      }
      addDataWithOptions(data);
    })
    .catch(err=>{
      // ignore
    });
}

fetch('/perception/data')
  .then(r=>r.json())
  .then(data=>{
    const coords = (data && data.features && data.features.length>0)? [data.features[0].geometry.coordinates[1], data.features[0].geometry.coordinates[0]]: null;
    initMap(coords);
    if(data) addDataWithOptions(data);
  })
  .catch(()=>initMap(null));

// refresh every second
setInterval(refresh, 1000);
</script>
</body>
</html>
"""


@app.route('/perception')
def perception_page():
    return render_template_string(HTML_TEMPLATE)


@app.route('/perception/data')
def perception_data():
    global _DATA_PATH
    if not _DATA_PATH or not os.path.exists(_DATA_PATH):
        return jsonify({"type":"FeatureCollection","features":[]})
    try:
        with open(_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({"type":"FeatureCollection","features":[]})


@app.route('/perception/snapshot', methods=['POST'])
def perception_snapshot():
    """保存当前 GeoJSON 与 HTML 快照。返回保存文件路径。
    可通过 POST param 'name' 指定文件名前缀。
    """
    global _DATA_PATH, _SNAP_DIR
    if not _DATA_PATH or not os.path.exists(_DATA_PATH):
        return abort(404, 'no data')
    name = request.args.get('name') or f"snapshot_{int(__import__('time').time())}"
    os.makedirs(_SNAP_DIR, exist_ok=True)
    geo_out = os.path.join(_SNAP_DIR, f'{name}.geojson')
    html_out = os.path.join(_SNAP_DIR, f'{name}.html')
    try:
        with open(_DATA_PATH, 'r', encoding='utf-8') as fr:
            data = fr.read()
        with open(geo_out, 'w', encoding='utf-8') as fw:
            fw.write(data)
        # create simple html that shows saved geojson text
        html_template = """
<!doctype html>
<html>
<head><meta charset="utf-8"/></head>
<body>
<h3>Perception Snapshot: %%NAME%%</h3>
<pre>%%DATA%%</pre>
</body>
</html>
"""
        html = html_template.replace('%%NAME%%', name).replace('%%DATA%%', data)
        with open(html_out, 'w', encoding='utf-8') as fh:
            fh.write(html)
        return jsonify({'geo': geo_out, 'html': html_out})
    except Exception as e:
        return abort(500, str(e))


def start_server(data_path, snap_dir='/tmp/perception_snapshots', host='0.0.0.0', port=5000):
    """Start Flask server in a background thread. Set global data path used for /perception/data.
    """
    global _DATA_PATH, _SNAP_DIR
    _DATA_PATH = data_path
    _SNAP_DIR = snap_dir

    def run():
        # disable flask logging to avoid clutter
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host=host, port=port, threaded=True)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t

