from xml.etree import ElementTree
from pathlib import Path

import requests
import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox


BASE = Path(__file__).resolve().parent
CENTER = (46.299515, 28.657978)
DISTANCE = 400


def main():
    raw_dir = BASE / "data" / "raw"
    output_dir = BASE / "results"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    cache = raw_dir / (
        f"osm-{CENTER[0]}-{CENTER[1]}-{DISTANCE}m.geojson"
    )
    preview = output_dir / "comrat-map.png"

    if cache.exists():
        features = gpd.read_file(cache)
        print("Loaded saved geometry:", cache)
    else:
        ox.settings.log_console = True
        bbox = ox.utils_geo.bbox_from_point(
            CENTER, dist=DISTANCE
        )
        xml_file = cache.with_suffix(".osm")

        if not xml_file.exists():
            print(
                "Downloading the small OSM extract...",
                flush=True,
            )

            response = requests.get(
                "https://api.openstreetmap.org/api/0.6/map",
                params={"bbox": ",".join(map(str, bbox))},
                headers={
                    "User-Agent": "ChetreMurate academic map preview"
                },
                timeout=(10, 60),
            )
            response.raise_for_status()

            if ElementTree.fromstring(response.content).tag != "osm":
                raise ValueError(
                    "The server did not return OSM XML."
                )

            temporary = xml_file.with_suffix(".tmp")
            temporary.write_bytes(response.content)
            temporary.replace(xml_file)

            print(
                "Saved OSM extract:", xml_file,
                flush=True,
            )

        features = ox.features.features_from_xml(
            xml_file,
            polygon=ox.utils_geo.bbox_to_poly(bbox),
            tags={
                "building": True,
                "highway": True,
                "place": "square",
            },
        )

        columns = [
            column
            for column in (
                "name", "building", "highway", "place", "geometry"
            )
            if column in features.columns
        ]
        features = features[columns]

        temporary = cache.with_suffix(".tmp")
        temporary.write_text(features.to_json(), encoding="utf-8")
        temporary.replace(cache)

        print("Saved geometry:", cache)

    if features.empty or features.crs is None:
        raise ValueError(
            "The geometry file is empty or has no coordinate system."
        )

    features = ox.projection.project_gdf(features)
    assert features.crs.is_projected
    assert features.crs.axis_info[0].unit_name == "metre"

    for column in ("building", "highway", "place"):
        if column not in features.columns:
            features[column] = None

    polygons = features.geometry.geom_type.isin(
        ["Polygon", "MultiPolygon"]
    )
    lines = features.geometry.geom_type.isin(
        ["LineString", "MultiLineString"]
    )

    buildings = features[
        polygons & features["building"].notna()
    ]
    roads = features[
        lines & features["highway"].notna()
    ]
    squares = features[
        polygons & features["place"].eq("square")
    ]

    center = gpd.GeoSeries.from_xy(
        [CENTER[1]], [CENTER[0]], crs="EPSG:4326"
    ).to_crs(features.crs).iloc[0]

    fig, ax = plt.subplots(figsize=(9, 9))

    if not buildings.empty:
        buildings.plot(
            ax=ax, color="lightgray", edgecolor="gray"
        )
    if not roads.empty:
        roads.plot(
            ax=ax, color="steelblue", linewidth=1
        )
    if not squares.empty:
        squares.plot(
            ax=ax,
            facecolor="none",
            edgecolor="orange",
            linewidth=2,
        )

    ax.scatter(
        center.x, center.y,
        color="red", s=30, zorder=5,
    )
    ax.set_xlim(center.x - DISTANCE, center.x + DISTANCE)
    ax.set_ylim(center.y - DISTANCE, center.y + DISTANCE)
    ax.set_aspect("equal")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.set_xlabel("Easting (metres)")
    ax.set_ylabel("Northing (metres)")
    ax.set_title(
        "Comrat geometry preview — square boundary not yet verified"
    )

    fig.text(
        0.5, 0.055,
        "Gray: buildings | Blue: mapped roads/paths | "
        "Orange: square | Red: centre",
        ha="center", fontsize=8,
    )
    fig.text(
        0.5, 0.03,
        "© OpenStreetMap contributors · ODbL · "
        "https://www.openstreetmap.org/copyright",
        ha="center", fontsize=8,
    )

    fig.savefig(preview, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(
        f"Buildings: {len(buildings)}, "
        f"road/path segments: {len(roads)}"
    )
    print(f"Mapped square polygons: {len(squares)}")
    print("Preview:", preview)


if __name__ == "__main__":
    main()
