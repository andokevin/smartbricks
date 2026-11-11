/** Carte de la tournée (react-leaflet, tuiles OpenStreetMap).
 * Si les tuiles ne se chargent pas (pas d'internet), on prévient le parent pour basculer sur le schéma SVG. */
import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect, useRef } from "react";
import { CircleMarker, MapContainer, Marker, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";

import type { City, Tour } from "../../api/types";

const ROUTE = "#1e5aa8";

function numberIcon(n: number, start: boolean): L.DivIcon {
  const bg = start ? "#004287" : "#ffffff";
  const fg = start ? "#ffffff" : "#004287";
  return L.divIcon({
    className: "",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<div style="width:30px;height:30px;border-radius:9999px;background:${bg};color:${fg};border:3px solid #004287;display:flex;align-items:center;justify-content:center;font:800 12px 'Plus Jakarta Sans Variable',sans-serif;box-shadow:0 2px 6px rgba(18,28,42,.25)">${n}</div>`,
  });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [48, 48], maxZoom: 8 });
  }, [map, points]);
  return null;
}

export function TourMap({ tour, cities, onTilesFailed }: { tour: Tour; cities: City[]; onTilesFailed: () => void }) {
  const errors = useRef(0);
  const stops: [number, number][] = tour.order.map((s) => [s.latitude, s.longitude]);
  const first = stops[0];
  const path = tour.closed && first ? [...stops, first] : stops;
  const visited = new Set(tour.order.map((s) => s.name));

  return (
    <MapContainer center={[-19, 47]} zoom={6} scrollWheelZoom={false} className="h-full w-full" attributionControl>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; contributeurs <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        eventHandlers={{
          tileerror: () => {
            errors.current += 1;
            if (errors.current === 3) onTilesFailed();
          },
        }}
      />
      <FitBounds points={stops} />
      {cities
        .filter((c) => !visited.has(c.name))
        .map((c) => (
          <CircleMarker key={c.id} center={[c.latitude, c.longitude]} radius={4} pathOptions={{ color: "#737782", weight: 1, fillOpacity: 0.5 }}>
            <Tooltip>{c.name}</Tooltip>
          </CircleMarker>
        ))}
      <Polyline positions={path} pathOptions={{ color: ROUTE, weight: 4, opacity: 0.9 }} />
      {tour.order.map((s, i) => (
        <Marker key={s.name} position={[s.latitude, s.longitude]} icon={numberIcon(s.step, i === 0)}>
          <Tooltip direction="right" offset={[16, 0]} permanent>
            <strong>{s.name}</strong>
            {i === 0 ? " (départ)" : ""}
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
