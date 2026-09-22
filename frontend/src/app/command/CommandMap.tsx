"use client";
import { MapContainer, TileLayer, Polygon, Marker, Popup, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix leaflet icon issue in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const shelterIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

const depotIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-orange.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41]
});

export default function CommandMap({ wards, shelters, depots }: { wards: any[], shelters: any[], depots: any[] }) {
  if (!wards || wards.length === 0) return <div>Loading map...</div>;

  const center = [wards[0].lat, wards[0].lon];

  const getColor = (state: string) => {
    if (state === 'Confirmed') return '#ef4444'; // red
    if (state === 'Reported') return '#f59e0b'; // amber
    return '#3b82f6'; // blue (Predicted / default)
  };

  return (
    <MapContainer center={center as any} zoom={12} style={{ height: '100%', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />

      {wards.map((w: any) => {
        if (!w.polygon) return null;
        
        // Convert GeoJSON coords to Leaflet [lat, lon]
        const positions = w.polygon.coordinates[0].map((coord: any) => [coord[1], coord[0]]);
        
        return (
          <Polygon 
            key={w.ward_id} 
            positions={positions} 
            pathOptions={{ 
              color: getColor(w.state), 
              fillColor: getColor(w.state),
              fillOpacity: 0.3,
              dashArray: w.state === 'Predicted' ? '5, 10' : undefined
            }}
          >
            <Tooltip sticky>
              <strong>{w.name}</strong><br/>
              Risk: {w.risk_score}<br/>
              State: {w.state}
            </Tooltip>
          </Polygon>
        );
      })}

      {shelters.map((s: any) => (
        <Marker key={`sh-${s.id}`} position={[s.lat, s.lon]} icon={shelterIcon}>
          <Tooltip>
            <strong>{s.name}</strong><br/>
            Capacity: {s.occupancy} / {s.capacity}
          </Tooltip>
        </Marker>
      ))}

      {depots.map((d: any) => (
        <Marker key={`dp-${d.id}`} position={[d.lat, d.lon]} icon={depotIcon}>
          <Tooltip>
            <strong>{d.name} (Depot)</strong><br/>
            {d.resources.map((r: any) => (
              <div key={r.type}>{r.type}: {r.available}</div>
            ))}
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
