# -*- coding: utf-8 -*-
"""Shared duplicate-keeper selection helpers."""


PEOPLE_FIRST_CHRONOLOGY_STRATEGIES = {
    "more-people/tags-then-oldest": "oldest",
    "more-people/tags-then-newest": "newest",
}


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
