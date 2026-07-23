# -*- coding: utf-8 -*-
"""Shared duplicate-keeper selection and review helpers."""

import json
import textwrap


PEOPLE_FIRST_CHRONOLOGY_STRATEGIES = {
    "more-people/tags-then-oldest": "oldest",
    "more-people/tags-then-newest": "newest",
}


_DUPLICATE_PREVIEW_METADATA_LABELS = {
    "albums": "Albums",
    "favorite": "Favorite",
    "description": "Description",
    "rating": "Rating",
    "visibility": "Visibility",
    "archived": "Archived",
    "date_time_original": "Date/time original",
    "location": "Location",
    "stack": "Stack",
    "tags": "Tags",
    "people": "People",
    "unassigned_faces": "Unassigned faces",
}


def _duplicate_asset_merge_metadata_preview(asset, display_names=None):
    """Return the merge-relevant Immich metadata shown before deletion."""
    asset = asset if isinstance(asset, dict) else {}
    display_names = display_names if isinstance(display_names, dict) else {}

    def reference_ids(key):
        values = asset.get(key) or []
        if not isinstance(values, list):
            return []

        def reference_id(item):
            if not isinstance(item, dict):
                return str(item or "").strip()
            if key == "people":
                person = item.get("person")
                person = person if isinstance(person, dict) else {}
                return str(
                    person.get("name") or item.get("name") or item.get("personName")
                    or item.get("personId") or person.get("id") or item.get("id") or ""
                ).strip()
            if key == "tags":
                return str(item.get("value") or item.get("name") or item.get("id") or "").strip()
            if key == "albums":
                return str(item.get("albumName") or item.get("name") or item.get("id") or "").strip()
            return str(item.get("id") or "").strip()

        ids = {
            reference_id(item)
            for item in values
            if reference_id(item)
        }
        names = display_names.get(key) if isinstance(display_names.get(key), dict) else {}
        return sorted(names.get(item_id, item_id) for item_id in ids)

    metadata = {}
    album_ids = reference_ids("albums")
    tag_ids = reference_ids("tags")
    if album_ids:
        metadata["albums"] = album_ids
    if tag_ids:
        metadata["tags"] = tag_ids
    if asset.get("isFavorite"):
        metadata["favorite"] = True
    description = str((asset.get("exifInfo") or {}).get("description") or asset.get("description") or "").strip()
    if description:
        metadata["description"] = description
    rating = (asset.get("exifInfo") or {}).get("rating", asset.get("rating"))
    try:
        if rating is not None:
            metadata["rating"] = int(rating)
    except (TypeError, ValueError):
        pass
    visibility = str(asset.get("visibility") or "").strip().upper()
    if visibility:
        metadata["visibility"] = visibility
    if asset.get("isArchived"):
        metadata["archived"] = True
    date_time_original = asset.get("dateTimeOriginal") or (asset.get("exifInfo") or {}).get("dateTimeOriginal")
    if date_time_original:
        metadata["date_time_original"] = date_time_original
    latitude = asset.get("latitude")
    longitude = asset.get("longitude")
    if latitude is None:
        latitude = (asset.get("exifInfo") or {}).get("latitude")
    if longitude is None:
        longitude = (asset.get("exifInfo") or {}).get("longitude")
    if latitude is not None and longitude is not None:
        metadata["location"] = {"latitude": latitude, "longitude": longitude}
    stack = asset.get("stack")
    if isinstance(stack, dict) and stack.get("id"):
        metadata["stack"] = {
            "id": stack.get("id"),
            "primary_asset_id": stack.get("primaryAssetId"),
        }
    people = reference_ids("people")
    if people:
        metadata["people"] = people
    if asset.get("unassignedFaces"):
        metadata["unassigned_faces"] = len(asset.get("unassignedFaces") or [])
    return metadata


def _format_duplicate_preview_value(key, value):
    """Render one metadata value compactly inside a duplicate-review table cell."""
    if value in (None, ""):
        return "-"
    if isinstance(value, list):
        if key in {"albums", "tags", "people"}:
            label = {"albums": "album(s)", "tags": "tag(s)", "people": "person(s)"}[key]
            return f"{len(value)} {label}\n" + "\n".join(str(item) for item in value)
        return "\n".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if key in {"favorite", "archived"}:
        return "Yes" if value else "No"
    return str(value)


def _duplicate_preview_asset_size(asset):
    """Return the Immich asset size for the duplicate-review comparison table."""
    asset = asset if isinstance(asset, dict) else {}
    exif_info = asset.get("exifInfo") or {}
    for value in (exif_info.get("fileSizeInByte"), exif_info.get("fileSize"), asset.get("fileSize")):
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _duplicate_group_preview_table(ordered_assets, display_names=None, keeper_strategy=None):
    """Return an ASCII table that compares duplicate candidates column by column."""
    ordered_assets = [asset for asset in ordered_assets if isinstance(asset, dict)]
    if not ordered_assets:
        return []

    source_metadata_by_asset = [
        _duplicate_asset_merge_metadata_preview(asset, display_names)
        for asset in ordered_assets
    ]
    metadata_by_asset = []
    for asset, source_metadata in zip(ordered_assets, source_metadata_by_asset):
        metadata = dict(source_metadata)
        # The table always shows both states, without changing the compact
        # metadata dictionary used by the merge implementation and its tests.
        metadata["favorite"] = bool(asset.get("isFavorite"))
        metadata["archived"] = bool(asset.get("isArchived"))
        metadata_by_asset.append(metadata)
    metadata_keys = [
        key for key in _DUPLICATE_PREVIEW_METADATA_LABELS
        if any(key in metadata for metadata in source_metadata_by_asset)
    ]
    keeper_label = "Keeper"
    if str(keeper_strategy or "").strip():
        keeper_label = f"Keeper ({keeper_strategy})"
    headers = ["Field", keeper_label, *[f"Remove {index}" for index in range(1, len(ordered_assets))]]
    rows = [
        ("ID", [str(asset.get("id") or "") for asset in ordered_assets]),
        (
            "Size",
            [
                f"{size:,} bytes" if (size := _duplicate_preview_asset_size(asset)) is not None else "-"
                for asset in ordered_assets
            ],
        ),
        ("Uploaded", [str(asset.get("createdAt") or "") for asset in ordered_assets]),
        *[
            (
                _DUPLICATE_PREVIEW_METADATA_LABELS[key],
                [_format_duplicate_preview_value(key, metadata.get(key)) for metadata in metadata_by_asset],
            )
            for key in metadata_keys
        ],
    ]

    field_width = 20
    # Four 42-character asset columns plus the field column fit in the normal
    # dashboard terminal and keep UUIDs/timestamps on one line. Wider groups
    # can overflow horizontally rather than becoming unreadably narrow.
    candidate_width = 47
    widths = [field_width, *([candidate_width] * len(ordered_assets))]

    def border():
        return "+" + "+".join("-" * (width + 2) for width in widths) + "+"

    def wrapped(value, width):
        lines = []
        for source_line in str(value).splitlines() or [""]:
            lines.extend(
                textwrap.wrap(
                    source_line,
                    width=width,
                    break_long_words=True,
                    break_on_hyphens=True,
                ) or [""]
            )
        return lines

    def render(cells):
        wrapped_cells = [wrapped(value, width) for value, width in zip(cells, widths)]
        height = max(len(cell) for cell in wrapped_cells)
        return [
            "| " + " | ".join(
                wrapped_cells[column][line].ljust(widths[column])
                if line < len(wrapped_cells[column]) else " " * widths[column]
                for column in range(len(widths))
            ) + " |"
            for line in range(height)
        ]

    table_lines = [border(), *render(headers), border()]
    for label, values in rows:
        table_lines.extend(render([label, *values]))
        table_lines.append(border())
    return table_lines


def duplicate_asset_people_count(asset):
    """Return the number of distinct people exposed by a cloud asset payload."""
    asset = asset if isinstance(asset, dict) else {}
    raw_people = asset.get("people") or asset.get("persons") or asset.get("personIds") or []
    if isinstance(raw_people, (str, int)):
        raw_people = [raw_people]
    if not isinstance(raw_people, (list, tuple, set)):
        return 0
    identifiers = set()
    for person in raw_people:
        if isinstance(person, dict):
            nested_person = person.get("person") if isinstance(person.get("person"), dict) else {}
            identifier = (person.get("personId") or nested_person.get("id") or person.get("id")
                          or nested_person.get("name") or person.get("name"))
        else:
            identifier = person
        identifier = str(identifier or "").strip()
        if identifier:
            identifiers.add(identifier.casefold())
    if identifiers:
        return len(identifiers)

    # Google Takeout people imports are represented in Immich as people/<name>
    # tags. Use them when the backend response has no native face/person links.
    raw_tags = asset.get("tags") or []
    if not isinstance(raw_tags, (list, tuple, set)):
        return 0
    for tag in raw_tags:
        value = tag.get("value") or tag.get("name") if isinstance(tag, dict) else tag
        value = str(value or "").strip()
        if value.casefold().startswith("people/") and value.split("/", 1)[1].strip():
            identifiers.add(value.casefold())
    return len(identifiers)


def duplicate_asset_tag_count(asset):
    """Return the number of distinct tags exposed by a cloud asset payload."""
    asset = asset if isinstance(asset, dict) else {}
    raw_tags = asset.get("tags") or []
    if not isinstance(raw_tags, (list, tuple, set)):
        return 0
    identifiers = set()
    for tag in raw_tags:
        value = (tag.get("value") or tag.get("name") or tag.get("id")) if isinstance(tag, dict) else tag
        value = str(value or "").strip()
        if value:
            identifiers.add(value.casefold())
    return len(identifiers)


def select_people_then_chronology_keeper(group, strategy, timestamp_getter):
    """Select by people, then tags, then the requested chronology."""
    normalized_strategy = str(strategy or "newest").strip().lower()
    tie_breaker = PEOPLE_FIRST_CHRONOLOGY_STRATEGIES.get(normalized_strategy, normalized_strategy)
    if tie_breaker not in {"oldest", "newest"}:
        raise ValueError("keeper strategy must use oldest or newest chronology")
    candidates = list(group or [])
    if normalized_strategy in PEOPLE_FIRST_CHRONOLOGY_STRATEGIES and candidates:
        max_people = max(duplicate_asset_people_count(asset) for asset in candidates)
        candidates = [asset for asset in candidates if duplicate_asset_people_count(asset) == max_people]
        max_tags = max(duplicate_asset_tag_count(asset) for asset in candidates)
        candidates = [asset for asset in candidates if duplicate_asset_tag_count(asset) == max_tags]
    return sorted(
        candidates,
        key=lambda item: (timestamp_getter(item), str((item or {}).get("id") or "")),
        reverse=(tie_breaker == "newest"),
    )[0]


def run_duplicate_asset_cleanup(
    client,
    keeper_strategy="newest",
    request_user_confirmation=True,
    use_immich_detection=False,
    use_immich_deletion=False,
    is_immich_client=False,
    logger=None,
    confirm=None,
    log_level=None,
):
    """Run the safe duplicate cleanup workflow for one media client.

    The public client method owns this workflow; this helper merely avoids
    duplicating its common review and keeper-selection mechanics across
    backends.
    """
    is_immich = bool(is_immich_client or use_immich_detection or use_immich_deletion)
    if is_immich and use_immich_detection:
        groups = client.find_duplicate_assets_by_immich_detection(log_level=log_level)
    else:
        groups = client.find_duplicate_assets_by_name_and_size(log_level=log_level)
    if not groups:
        if logger:
            logger.info("No duplicate assets were found.")
        return 0, 0, 0

    if is_immich:
        groups = client.hydrate_duplicate_groups_metadata(
            groups, log_level=log_level, include_albums=False,
        )
        if not groups:
            if logger:
                logger.warning("No duplicate group could be fully loaded for safe metadata review. No assets were deleted.")
            return 0, 0, 0

        display_names = client.get_duplicate_metadata_display_names(
            groups, log_level=log_level,
        )
    else:
        display_names = {}

    if logger:
        duplicate_assets_count = sum(len(group) for group in groups)
        logger.info(
            f"Duplicate review: {len(groups)} duplicate group(s), "
            f"{duplicate_assets_count} duplicate asset(s)."
        )
        logger.info("Duplicate asset groups found:")
        for index, group in enumerate(groups, start=1):
            logger.info("")
            if is_immich and use_immich_detection:
                keeper = client._select_duplicate_asset_keeper(group, keeper_strategy)
            else:
                keeper = select_people_then_chronology_keeper(group, keeper_strategy, client._duplicate_asset_timestamp)
            filename = str(keeper.get("originalFileName") or keeper.get("filename") or keeper.get("id") or "")
            size = client._duplicate_asset_size(keeper)
            logger.info(f"  [{index}] {filename} ({size} bytes, {len(group)} candidate asset(s))")
            if is_immich:
                ordered_assets = [keeper, *[asset for asset in group if asset is not keeper]]
                for line in _duplicate_group_preview_table(
                    ordered_assets, display_names, keeper_strategy,
                ):
                    logger.info(f"      {line}")

    if request_user_confirmation and confirm and not confirm():
        if logger:
            logger.info("Exiting program without deleting duplicate assets.")
        return 0, len(groups), 0

    if is_immich and use_immich_deletion:
        return client.resolve_duplicate_asset_groups_with_immich(
            duplicate_groups=groups, keeper_strategy=keeper_strategy, log_level=log_level,
        )
    result = client.remove_duplicates_assets_by_name_and_size(
        keeper_strategy=keeper_strategy, duplicate_groups=groups, log_level=log_level,
    )
    return result if isinstance(result, tuple) else (int(result or 0), len(groups), 0)
