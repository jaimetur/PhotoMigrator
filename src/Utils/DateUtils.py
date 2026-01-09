import re
from datetime import datetime
from datetime import timezone, timedelta
from pathlib import Path

import tzlocal
from dateutil import parser as date_parser

import Core.GlobalVariables as GV
from Core.CustomLogger import set_log_level


# ==============================================================================
#                               DATE FUNCTIONS
# ==============================================================================
def is_date_outside_range(date_to_check):
    """
    Returns True if `date_to_check` is outside the configured filter range.

    It reads the boundaries from:
      - GV.ARGS['filter-from-date']
      - GV.ARGS['filter-to-date']

    All values are converted to epoch seconds using `parse_text_datetime_to_epoch`.

    Args:
        date_to_check (str | int | float | datetime): Date/time to evaluate.

    Returns:
        bool: True if the date is before 'filter-from-date' or after 'filter-to-date', otherwise False.
    """
    from_date = parse_text_datetime_to_epoch(GV.ARGS.get('filter-from-date'))
    to_date = parse_text_datetime_to_epoch(GV.ARGS.get('filter-to-date'))
    date_to_check = parse_text_datetime_to_epoch(date_to_check)
    if from_date is not None and date_to_check < from_date:
        return True
    if to_date is not None and date_to_check > to_date:
        return True
    return False


# ==============================================================================
#                               DATE PARSERS
# ==============================================================================
def parse_text_datetime_to_epoch(value):
    """
    Converts a datetime-like input into a UNIX epoch timestamp (in seconds).

    Priority for string parsing:
    1. ISO 8601 with timezone or 'Z'
    2. ISO format without timezone
    3. Year only (e.g., '2024') → '2024-01-01'
    4. Year and month (various formats) → 'YYYY-MM-01'
    5. Float or int string (epoch-like)

    Args:
        value (str | int | float | datetime): The input value to convert.

    Returns:
        int | None: The epoch timestamp in seconds, or None if parsing fails.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            # Priority 1: ISO with timezone or 'Z'
            dt = date_parser.isoparse(value)
            return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 2: ISO without timezone
            dt = datetime.fromisoformat(value)
            return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 3: Year only
            if re.fullmatch(r"\d{4}", value):
                dt = datetime(int(value), 1, 1)
                return int(dt.timestamp())
            # Priority 4: Year and month (various formats)
            match = re.fullmatch(r"(\d{4})[-/](\d{1,2})", value)
            if match:
                year, month = int(match.group(1)), int(match.group(2))
                dt = datetime(year, month, 1)
                return int(dt.timestamp())
            match = re.fullmatch(r"(\d{1,2})[-/](\d{4})", value)
            if match:
                month, year = int(match.group(1)), int(match.group(2))
                dt = datetime(year, month, 1)
                return int(dt.timestamp())
        except Exception:
            pass
        try:
            # Priority 5: float/int string
            return int(float(value))
        except Exception:
            return None
    if isinstance(value, datetime):
        return int(value.timestamp())
    return None


def parse_text_to_iso8601(date_str):
    """
    Tries to convert a date string to ISO 8601 format (UTC at midnight).

    Supported inputs:
      - Day/Month/Year (various formats)
      - Year/Month or Month/Year (e.g. '2024-03' or '03/2024')
      - Year only (e.g. '2024')

    Args:
        date_str (str): Input date string.

    Returns:
        str | None: ISO 8601 date string (UTC midnight) or None if conversion fails.
    """
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    # List of formats with day, month and year
    date_formats = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            continue
    # Year and month: YYYY-MM, YYYY/MM, MM-YYYY, MM/YYYY
    try:
        match = re.fullmatch(r"(\d{4})[-/](\d{1,2})", date_str)
        if match:
            year, month = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        match = re.fullmatch(r"(\d{1,2})[-/](\d{4})", date_str)
        if match:
            month, year = int(match.group(1)), int(match.group(2))
            dt = datetime(year, month, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
    except Exception:
        pass
    # Year only
    if re.fullmatch(r"\d{4}", date_str):
        try:
            dt = datetime(int(date_str), 1, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except Exception:
            pass
    return None


def iso8601_to_epoch(iso_date):
    """
    Converts an ISO 8601 datetime string to a UNIX epoch timestamp (seconds).

    Notes:
        - Marked as deprecated in the original code.
        - If `iso_date` is None, returns None.
        - If parsing fails, returns -1 (legacy behavior).

    Args:
        iso_date (str | None): ISO 8601 date string, possibly ending with 'Z'.

    Returns:
        int | None: Epoch seconds, None if input is None, -1 on parse error.
    """
    # Deprecated function
    if iso_date is None:
        return None
    try:
        if iso_date.endswith("Z"):
            iso_date = iso_date.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_date)
        return int(dt.timestamp())
    except Exception:
        # In case of unexpected error, return -1
        return -1


def epoch_to_iso8601(epoch):
    """
    Converts a UNIX epoch timestamp (seconds) to an ISO 8601 UTC string.

    Notes:
        - Marked as deprecated in the original code.
        - If `epoch` is None or empty string, returns "" (legacy behavior).
        - If conversion fails, returns "".

    Args:
        epoch (int | str | None): Epoch seconds.

    Returns:
        str: ISO 8601 UTC string (ending with 'Z') or "" on invalid input/error.
    """
    # Deprecated function
    if epoch is None or epoch == "":
        return ""

    try:
        epoch = int(epoch)
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        # In case of unexpected error, return the original legacy value
        return ""


def normalize_datetime_utc(dt):
    """
    Normalizes a datetime into an aware UTC datetime.

    Behavior:
      - If `dt` is naive (tzinfo is None), it is assumed to be UTC and made aware.
      - If `dt` is timezone-aware, it is converted to UTC.

    Args:
        dt (datetime): Input datetime.

    Returns:
        datetime: Timezone-aware datetime in UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)  # naive → UTC
    else:
        return dt.astimezone(timezone.utc)      # aware → UTC


def is_date_valid(date_to_check, reference, min_days=0):
    """
    Returns True if `date_to_check` is valid and sufficiently old compared to `reference`.

    Rules:
      - `date_to_check` must not be None
      - year must be between 1970 and 2100 inclusive
      - `date_to_check` must be older than (reference - min_days)

    Args:
        date_to_check (datetime | None): Date to validate.
        reference (datetime): Reference datetime (naive is assumed UTC).
        min_days (int): Minimum age (in days) required.

    Returns:
        bool: True if valid, otherwise False.
    """
    if date_to_check is None:
        return False
    if date_to_check.year < 1970 or date_to_check.year > 2100:
        return False
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return date_to_check < (reference - timedelta(days=min_days))


def guess_date_from_filename(path, step_name="", log_level=None):
    """
    Try to guess a date from a filename (first from filename, then path folders) and return it in ISO 8601 format.

    Search strategy:
      1) Start with the filename.
      2) Then check the parent folder name.
      3) Optionally check the grandparent folder name ONLY if the parent folder name looks like a month (01..12).

    Anti-false-positive strategy:
      - Detect UUID/hash-like tokens and skip them entirely before applying regex patterns
        (prevents interpreting hash numbers as dates).

    Supported patterns (strongest to weakest, applied in order):
      - YYYYMMDD with optional time and timezone
      - YYYY-MM-DD (or similar separators) with optional time and timezone
      - DD-MM-YYYY without time
      - YYYYMM / MMYYYY (6 digits) when year is 19xx/20xx and month is valid
      - Isolated year (19xx/20xx) delimited by non-alnum boundaries

    Time handling:
      - If no time is found, defaults to 00:00:00.
      - If partial time is found, missing parts default to 00.
      - Milliseconds are supported (1..6 digits), padded to microseconds.

    Timezone handling:
      - If a timezone is found ("Z" or ±HHMM/±HH:MM), it is applied.
      - Otherwise, local timezone is used.

    Args:
        path (str | Path): Full path or filename.
        step_name (str): Optional prefix for log messages.
        log_level: Optional logging level override.

    Returns:
        tuple[str | None, str | None]: (ISO date string, source) where source is 'filename' or 'filepath'.
    """
    import re
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    from dateutil import tz

    with set_log_level(GV.LOGGER, log_level):
        local_tz = datetime.now().astimezone().tzinfo
        path = Path(path)

        # Restrict search scope to filename, parent and grandparent folder names
        # NOTE: Only look at the grandparent if the parent folder is a month (01..12).
        candidates = [(path.name, "filename")]
        if path.parent and path.parent.name:
            candidates.append((path.parent.name, "filepath"))
            parent_name = path.parent.name
            if re.fullmatch(r'(0[1-9]|1[0-2])', parent_name) and path.parent.parent and path.parent.parent.name:
                candidates.append((path.parent.parent.name, "filepath"))

        # ---------- Heuristics to detect hash/UUID-like names (applied BEFORE any regex pattern) ----------
        # English rationale: if the whole text looks like a hash/UUID (or extremely hex-dense token),
        # we must skip ANY pattern (including yyyymmdd, yyyy-mm, loose year), because numbers are not meaningful dates there.
        uuid_like_re = re.compile(r'^[0-9a-fA-F]{8}[-_][0-9a-fA-F]{4}[-_][0-9a-fA-F]{4}[-_][0-9a-fA-F]{4}[-_][0-9a-fA-F]{12}$')

        def is_probably_hash(text):
            """
            Returns True if the provided text looks like a UUID or a hash-like token.

            The function applies multiple heuristics:
              1) UUID canonical pattern (with '-' or '_')
              2) High hex-density long alphanumeric string
              3) Long tokens (>=24 chars) that are almost all hex

            Args:
                text (str): Candidate text to analyze (filename/folder name).

            Returns:
                bool: True if hash/UUID-like, otherwise False.
            """
            # Normalize: strip extension for the main token check
            base = text.rsplit('.', 1)[0]

            # 1) UUID canonical pattern (with '-' or '_')
            if uuid_like_re.fullmatch(base):
                return True

            # 2) High hex-density long alphanumeric string → likely hash
            alnum = re.sub(r'[^0-9A-Za-z]', '', base)
            if len(alnum) >= 20:
                hex_count = len(re.findall(r'[0-9A-Fa-f]', alnum))
                hex_ratio = hex_count / len(alnum)
                vowels = len(re.findall(r'[AEIOUaeiou]', alnum))
                if hex_ratio >= 0.85 and vowels <= 1:
                    return True

            # 3) Any long token (>=24) that is ~all hex → likely hash
            tokens = re.split(r'[^0-9A-Za-z]+', base)
            for tk in tokens:
                if len(tk) >= 24:
                    hex_count = len(re.findall(r'[0-9A-Fa-f]', tk))
                    if hex_count / len(tk) >= 0.9:
                        return True

            return False

        # More robust patterns, with separator and timezone control
        # NOTE (English): Unified list; ordered from strongest/specific to weakest (loose year last).
        patterns = [
            # yyyymmdd with time and optional timezone (no separators)
            r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})(?P<month>\d{2})(?P<day>\d{2})[T_\-\. ]?(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?(?:\.(?P<millisec>\d{1,6}))?(?P<tz>Z|[+-]\d{2}:?\d{2})?(?![a-zA-Z])',
            # yyyy-mm-dd with time and timezone
            r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})[-_. ](?P<month>\d{2})[-_. ](?P<day>\d{2})[T_\-\. ]?(?P<hour>\d{2})?[-_.:]?(?P<minute>\d{2})?[-_.:]?(?P<second>\d{2})?(?:\.(?P<millisec>\d{1,6}))?(?P<tz>Z|[+-]\d{2}:?\d{2})?(?![a-zA-Z])',
            # dd-mm-yyyy without time
            r'(?<![a-fA-F])(?P<day>\d{2})[-_](?P<month>\d{2})[-_](?P<year>19\d{2}|20\d{2})(?![a-zA-Z])',
            # year + month (6 digits) if month is valid
            r'(?<!\d)(?P<year>19\d{2}|20\d{2})(?P<month>\d{2})(?!\d)',
            r'(?<!\d)(?P<month>\d{2})(?P<year>19\d{2}|20\d{2})(?!\d)',
            # isolated year (delimited by any non-alnum or string boundaries)
            r'(?:(?<=^)|(?<=[^0-9A-Za-z]))(?P<year>19\d{2}|20\d{2})(?=$|[^0-9A-Za-z])',
        ]

        def try_build_datetime_from_match(parts):
            """
            Builds a timezone-aware datetime from regex named groups.

            Missing date parts are defaulted:
              - month/day default to 1
              - hour/minute/second default to 0
              - millisec is padded to microseconds (0..999999)

            Validation:
              - year must be in [1900..2099]
              - month in [1..12]
              - day in [1..31]
              - time components in valid ranges

            Timezone:
              - 'Z' => UTC
              - ±HHMM or ±HH:MM => fixed offset
              - otherwise => local timezone

            Args:
                parts (dict): Named groups from the regex match.

            Returns:
                datetime | None: A timezone-aware datetime or None if validation fails.
            """
            # Build datetime with defaults and validate ranges
            year = int(parts.get("year") or 0)
            month = int(parts.get("month") or 1)
            day = int(parts.get("day") or 1)
            hour = int(parts.get("hour") or 0)
            minute = int(parts.get("minute") or 0)
            second = int(parts.get("second") or 0)
            microsecond = int((parts.get("millisec") or "0").ljust(6, "0"))

            if not (1900 <= year <= 2099): return None
            if not (1 <= month <= 12): return None
            if not (1 <= day <= 31): return None
            if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59): return None

            tz_str = parts.get("tz")
            if tz_str == "Z":
                tzinfo = timezone.utc
            elif tz_str and re.fullmatch(r"[+-]\d{2}:?\d{2}", tz_str):
                sign = 1 if tz_str.startswith("+") else -1
                hours = int(tz_str[1:3])
                minutes = int(tz_str[-2:])
                offset = timedelta(hours=hours, minutes=minutes)
                tzinfo = timezone(sign * offset)
            else:
                tzinfo = local_tz

            return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo)

        for text, source in candidates:
            # Skip entire candidate if it looks hash-like (applies to ALL patterns)
            if is_probably_hash(text):
                GV.LOGGER.debug(f"{step_name}↩️ Skipping candidate (hash-like text): {text}")
                continue

            # Single unified pass over all patterns, in order
            for pattern in patterns:
                match = re.search(pattern, text)
                if not match:
                    continue
                try:
                    dt = try_build_datetime_from_match(match.groupdict())
                    if dt:
                        iso_str = dt.isoformat()
                        GV.LOGGER.debug(f"{step_name}🧠 Guessed ISO date {iso_str} from {source}: {text}")
                        return iso_str, source
                except Exception as e:
                    GV.LOGGER.warning(f"{step_name}⚠️ Error parsing date from {source} '{text}': {e}")
                    continue

        GV.LOGGER.debug(f"{step_name}❌ No date found in filename or path: {path}")
        return None, None
