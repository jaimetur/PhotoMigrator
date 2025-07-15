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
    Intenta convertir una cadena de fecha a formato ISO 8601 (UTC a medianoche).

    Soporta:
    - Día/Mes/Año (varios formatos)
    - Año/Mes o Mes/Año (como '2024-03' o '03/2024')
    - Solo año (como '2024')

    Args:
        date_str (str): La cadena de fecha.

    Returns:
        str | None: Fecha en formato ISO 8601 o None si no se pudo convertir.
    """
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    # Lista de formatos con día, mes y año
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
    # Año y mes: YYYY-MM, YYYY/MM, MM-YYYY, MM/YYYY
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
    # Solo año
    if re.fullmatch(r"\d{4}", date_str):
        try:
            dt = datetime(int(date_str), 1, 1)
            return dt.strftime("%Y-%m-%dT00:00:00.000Z")
        except Exception:
            pass
    return None


def iso8601_to_epoch(iso_date):
    # Deprecated fucntion
    """
    Convierte una fecha en formato ISO 8601 a timestamp Unix (en segundos).
    Si el argumento es None o una cadena vacía, devuelve el mismo valor.

    Ejemplo:
        iso8601_to_epoch("2021-12-01T00:00:00Z") -> 1638316800
        iso8601_to_epoch("") -> -1
        iso8601_to_epoch(None) -> -1
    """
    if iso_date is None:
        return None
    try:
        if iso_date.endswith("Z"):
            iso_date = iso_date.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_date)
        return int(dt.timestamp())
    except Exception:
        # En caso de error inesperado, se devuelve -1
        return -1


def epoch_to_iso8601(epoch):
    # Deprecated fucntion
    """
    Convierte un timestamp Unix (en segundos) a una cadena en formato ISO 8601 (UTC).
    Si el argumento es None o una cadena vacía, devuelve el mismo valor.

    Ejemplo:
        epoch_to_iso8601(1638316800) -> "2021-12-01T00:00:00Z"
        epoch_to_iso8601("") -> ""
        epoch_to_iso8601(None) -> ""
    """
    if epoch is None or epoch == "":
        return ""

    try:
        # Asegura que sea un número entero
        epoch = int(epoch)
        dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except Exception:
        # En caso de error inesperado, se devuelve el valor original
        return ""


def normalize_datetime_utc(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)  # naive → UTC
    else:
        return dt.astimezone(timezone.utc)      # aware → UTC


def is_date_valid(file_date, reference_timestamp, min_days=1):
    if file_date is None:
        return False
    if reference_timestamp.tzinfo is None:
        reference_timestamp = reference_timestamp.replace(tzinfo=timezone.utc)
    return file_date < (reference_timestamp - timedelta(days=min_days))


def guess_date_from_filename(path, step_name="", log_level=None):
    """
    Try to guess a date from a filename (first from basename, then full path) and return it in ISO 8601 format with local timezone.
    If only year/month/day is found, missing parts are filled with 01.
    If no time is found, it defaults to 00:00:00.
    Timezone is set to the system's local timezone.

    Args:
        path: Full path or filename.
        step_name: Optional prefix for log messages.
        log_level: Optional logging level override.

    Returns:
        A string with date in format 'YYYY-MM-DDTHH:MM:SS±HH:MM', or None if not found.
    """
    import re
    from pathlib import Path
    from datetime import datetime
    import tzlocal

    with set_log_level(LOGGER, log_level):
        tz = tzlocal.get_localzone()
        path = Path(path)
        candidates = [path.name, str(path)]

        patterns = [
            r'(?P<year>20\d{2})(?P<month>\d{2})(?P<day>\d{2})[_\-T ]?(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?',   # 20230715_123456
            r'(?P<year>\d{4})[.\-_ ](?P<month>\d{2})[.\-_ ](?P<day>\d{2})[^\d]?(?P<hour>\d{2})?[.\-_ ]?(?P<minute>\d{2})?[.\-_ ]?(?P<second>\d{2})?',  # 2020.01.01_12-30-15
            r'(?P<day>\d{2})[-_](?P<month>\d{2})[-_](?P<year>\d{4})',  # 15-07-2023
            r'(?P<year>\d{4})',  # only year
        ]

        for text in candidates:
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        parts = match.groupdict()
                        year = int(parts.get("year"))
                        month = int(parts.get("month") or 1)
                        day = int(parts.get("day") or 1)
                        hour = int(parts.get("hour") or 0)
                        minute = int(parts.get("minute") or 0)
                        second = int(parts.get("second") or 0)

                        dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)
                        iso_str = dt.isoformat()
                        LOGGER.debug(f"{step_name}🧠 Guessed ISO date {iso_str} from text: {text}")
                        return iso_str
                    except Exception as e:
                        LOGGER.warning(f"{step_name}⚠️ Error parsing date from text '{text}': {e}")
                        continue

        LOGGER.debug(f"{step_name}❌ No date found in filename or path: {path}")
        return None

