import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
from shapely.ops import unary_union

from prepare_map import BASE, CENTER, DISTANCE


SOURCE_ID = "('way', 1434157802)"
METRIC_CRS = "EPSG:32635"


def candidate_geometry(square, obstacles):
    if square.is_empty or not square.is_valid:
        raise ValueError(
            "The source square must be non-empty and valid."
        )

    if any(not obstacle.is_valid for obstacle in obstacles):
        raise ValueError(
            "Inspect invalid building geometry before continuing."
        )

    candidate = square.difference(unary_union(obstacles))

    if (
        candidate.is_empty
        or not candidate.is_valid
        or candidate.geom_type not in ("Polygon", "MultiPolygon")
    ):
        raise ValueError(
            "No valid polygonal candidate area remains."
        )

    return candidate


def check_derivation():
    square = box(0, 0, 10, 10)

    inside = candidate_geometry(square, [box(2, 2, 4, 4)])
    assert abs(inside.area - 96) < 1e-9

    touching = candidate_geometry(square, [box(-2, 2, 0, 4)])
    assert abs(touching.area - 100) < 1e-9

    split = candidate_geometry(square, [box(4, 0, 6, 10)])
    assert split.geom_type == "MultiPolygon"
    assert len(split.geoms) == 2

    try:
        candidate_geometry(square, [square])
    except ValueError:
        pass
    else:
        raise AssertionError(
            "A fully blocked square must be rejected."
        )


def main():
    check_derivation()

    raw = BASE / "data" / "raw" / (
        f"osm-{CENTER[0]}-{CENTER[1]}-{DISTANCE}m.geojson"
    )
    features = gpd.read_file(raw).to_crs(METRIC_CRS)

    selected = features[features["id"].eq(SOURCE_ID)]
    if len(selected) != 1:
        raise ValueError(
            f"Expected exactly one square with ID {SOURCE_ID}."
        )

    square = selected.geometry.iloc[0]

    polygons = features.geometry.geom_type.isin(
        ["Polygon", "MultiPolygon"]
    )
    buildings = features[
        polygons & features["building"].notna()
    ]

    candidate = candidate_geometry(
        square, list(buildings.geometry)
    )

    lines = features.geometry.geom_type.isin(
        ["LineString", "MultiLineString"]
    )
    roads = features[
        lines & features["highway"].notna()
    ]
    traffic = roads[
        ~roads["highway"].isin(
            ["footway", "pedestrian", "path", "steps"]
        )
        & roads.intersects(candidate)
    ]

    output = (
        BASE / "data" / "processed" / "candidate-square.geojson"
    )
    preview = BASE / "results" / "comrat-candidate.png"

    output.parent.mkdir(parents=True, exist_ok=True)
    preview.parent.mkdir(parents=True, exist_ok=True)

    result = gpd.GeoDataFrame(
        [{
            "source_id": SOURCE_ID,
            "status": "candidate_not_verified",
            "area_m2": candidate.area,
            "geometry": candidate,
        }],
        crs=METRIC_CRS,
    )
    result.to_crs("EPSG:4326").to_file(
        output, driver="GeoJSON"
    )

    fig, ax = plt.subplots(figsize=(7, 9))

    result.plot(
        ax=ax,
        color="palegreen",
        edgecolor="darkgreen",
        alpha=0.7,
    )
    if not roads.empty:
        roads.plot(
            ax=ax, color="steelblue", linewidth=1
        )
    if not buildings.empty:
        buildings.plot(
            ax=ax, color="lightgray", edgecolor="gray"
        )
    if not traffic.empty:
        traffic.plot(
            ax=ax, color="red", linewidth=2
        )

    left, bottom, right, top = candidate.bounds
    ax.set_xlim(left - 60, right + 60)
    ax.set_ylim(bottom - 30, top + 30)
    ax.set_aspect("equal")
    ax.ticklabel_format(style="plain", useOffset=False)
    ax.locator_params(axis="x", nbins=4)
    ax.set_xlabel("Easting (metres)")
    ax.set_ylabel("Northing (metres)")
    ax.set_title("Candidate area — not verified walkable")

    fig.text(
        0.5, 0.045,
        "Green: candidate | Gray: buildings | Blue: roads/paths\n"
        "Red: road access or exclusion needs review",
        ha="center", fontsize=8,
    )
    fig.text(
        0.5, 0.01,
        "© OpenStreetMap contributors · ODbL\n"
        "https://www.openstreetmap.org/copyright",
        ha="center", fontsize=8,
    )

    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(preview, dpi=150)
    plt.close(fig)

    print(
        f"Candidate area: {candidate.area:.2f} m² "
        "— NOT verified usable area"
    )
    print(
        f"Road/path segments needing review: {len(traffic)}"
    )
    print("Geometry:", output)
    print("Preview:", preview)


if __name__ == "__main__":
    main()
