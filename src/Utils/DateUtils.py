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


def is_date_valid(date_to_check, reference, min_days=0):
    """
    Return True if date_to_check < (reference - min_days days).
    """
    if date_to_check is None:
        return False
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return date_to_check < (reference - timedelta(days=min_days))


def guess_date_from_filename(path, step_name="", log_level=None):
    """
    Try to guess a date from a filename (first from filename, then full filepath) and return it in ISO 8601 format with local timezone.
    If only year/month/day is found, missing parts are filled with 01.
    If no time is found, it defaults to 00:00:00.
    Timezone is set to the system's local timezone unless a timezone is detected in the pattern.

    Args:
        path: Full path or filename.
        step_name: Optional prefix for log messages.
        log_level: Optional logging level override.

    Returns:
        Tuple: (ISO date string or None, source: 'filename' | 'filepath' | None)
    """
    import re
    from pathlib import Path
    from datetime import datetime, timezone, timedelta
    from dateutil import tz

    with set_log_level(GV.LOGGER, log_level):
        local_tz = datetime.now().astimezone().tzinfo
        path = Path(path)
        candidates = [(path.name, "filename"), (str(path), "filepath")]

        # Patrones más inteligentes, con control de separadores y zonas horarias
        patterns = [
            # yyyymmdd con hora y opcional zona horaria (sin separadores)
            r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})(?P<month>\d{2})(?P<day>\d{2})[T_\-\. ]?(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?(?:\.(?P<millisec>\d{1,6}))?(?P<tz>Z|[+-]\d{2}:?\d{2})?(?![a-zA-Z])',
            # yyyy-mm-dd con hora y zona horaria
            r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})[-_. ](?P<month>\d{2})[-_. ](?P<day>\d{2})[T_\-\. ]?(?P<hour>\d{2})?[-_.:]?(?P<minute>\d{2})?[-_.:]?(?P<second>\d{2})?(?:\.(?P<millisec>\d{1,6}))?(?P<tz>Z|[+-]\d{2}:?\d{2})?(?![a-zA-Z])',
            # dd-mm-yyyy sin hora
            r'(?<![a-fA-F])(?P<day>\d{2})[-_](?P<month>\d{2})[-_](?P<year>19\d{2}|20\d{2})(?![a-zA-Z])',
            # año + mes (6 dígitos) si el mes es válido
            r'(?<!\d)(?P<year>19\d{2}|20\d{2})(?P<month>\d{2})(?!\d)',
            r'(?<!\d)(?P<month>\d{2})(?P<year>19\d{2}|20\d{2})(?!\d)',
            # año suelto (4 dígitos)
            r'(?<![a-fA-F\d])(?P<year>19\d{2}|20\d{2})(?![a-zA-Z\d])',
        ]

        for text, source in candidates:
            for pattern in patterns:
                match = re.search(pattern, text)
                if not match:
                    continue

                parts = match.groupdict()
                try:
                    year = int(parts.get("year") or 0)
                    month = int(parts.get("month") or 1)
                    day = int(parts.get("day") or 1)
                    hour = int(parts.get("hour") or 0)
                    minute = int(parts.get("minute") or 0)
                    second = int(parts.get("second") or 0)
                    microsecond = int((parts.get("millisec") or "0").ljust(6, "0"))

                    # Validaciones
                    if not (1900 <= year <= 2099): continue
                    if not (1 <= month <= 12): continue
                    if not (1 <= day <= 31): continue
                    if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59): continue

                    # Timezone
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

                    dt = datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tzinfo)
                    iso_str = dt.isoformat()
                    GV.LOGGER.debug(f"{step_name}🧠 Guessed ISO date {iso_str} from {source}: {text}")
                    return iso_str, source

                except Exception as e:
                    GV.LOGGER.warning(f"{step_name}⚠️ Error parsing date from {source} '{text}': {e}")
                    continue

        GV.LOGGER.debug(f"{step_name}❌ No date found in filename or path: {path}")
        return None, None

# def guess_date_from_filename(path, step_name="", log_level=None):
#     """
#     Try to guess a date from a filename (first from filename, then full filepath) and return it in ISO 8601 format with local timezone.
#     If only year/month/day is found, missing parts are filled with 01.
#     If no time is found, it defaults to 00:00:00.
#     Timezone is set to the system's local timezone.
#
#     Args:
#         path: Full path or filename.
#         step_name: Optional prefix for log messages.
#         log_level: Optional logging level override.
#
#     Returns:
#         Tuple: (ISO date string or None, source: 'filename' | 'filepath' | None)
#     """
#     import re
#     from pathlib import Path
#     from datetime import datetime
#
#     with set_log_level(GV.LOGGER, log_level):
#         tz = datetime.now().astimezone().tzinfo
#         path = Path(path)
#         candidates = [(path.name, "filename"), (str(path.parent), "filepath")]
#
#         patterns = [
#             # yyyy mm dd [hh mm ss] sin separadores, ej: 20230715_153025
#             r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})(?P<month>\d{2})(?P<day>\d{2})[_\-T ]?(?P<hour>\d{2})?(?P<minute>\d{2})?(?P<second>\d{2})?(?![a-zA-Z])',
#             # yyyy-mm-dd_hh-mm-ss, con separadores, ej: 2023-07-15_15-30-25
#             r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})[.\-_ ](?P<month>\d{2})[.\-_ ](?P<day>\d{2})[^\d]?(?P<hour>\d{2})?[.\-_ ]?(?P<minute>\d{2})?[.\-_ ]?(?P<second>\d{2})?(?![a-zA-Z])',
#             # dd-mm-yyyy ej: 15-07-2023
#             r'(?<![a-fA-F])(?P<day>\d{2})[-_](?P<month>\d{2})[-_](?P<year>19\d{2}|20\d{2})(?![a-zA-Z])',
#             # Año solo aislado, ej: _2023_
#             r'(?<![a-fA-F])(?P<year>19\d{2}|20\d{2})(?!\d|[a-zA-Z])',
#             # Año + Mes aislado, ej: 202307 o 072023
#             r'(?<![a-fA-F])(?P<ym>\d{6})(?!\d|[a-zA-Z])',
#             # Año + Mes + Día aislado (8 dígitos), ej: 20230715 o 15072023
#             r'(?<![a-fA-F])(?P<ymd>\d{8})(?!\d|[a-zA-Z])',
#         ]
#
#         for text, source in candidates:
#             for pattern in patterns:
#                 match = re.search(pattern, text)
#                 if match:
#                     try:
#                         parts = match.groupdict()
#                         year = month = day = hour = minute = second = None
#
#                         if parts.get("year"):
#                             year = int(parts["year"])
#                             month = int(parts.get("month") or 1)
#                             day = int(parts.get("day") or 1)
#                             hour = int(parts.get("hour") or 0)
#                             minute = int(parts.get("minute") or 0)
#                             second = int(parts.get("second") or 0)
#
#                         elif parts.get("ymd"):
#                             digits = parts["ymd"]
#                             combos = [
#                                 (digits[0:4], digits[4:6], digits[6:8]),  # yyyy mm dd
#                                 (digits[4:8], digits[2:4], digits[0:2]),  # dd mm yyyy
#                                 (digits[2:6], digits[0:2], digits[6:8]),  # mm dd yyyy
#                             ]
#                             for y, m, d in combos:
#                                 if re.fullmatch(r"(19|20)\d{2}", y) and 1 <= int(m) <= 12 and 1 <= int(d) <= 31:
#                                     year = int(y)
#                                     month = int(m)
#                                     day = int(d)
#                                     break
#                             if year is None:
#                                 continue  # No combinación válida
#
#                             hour = minute = second = 0
#
#                         elif parts.get("ym"):
#                             digits = parts["ym"]
#                             combos = [
#                                 (digits[0:4], digits[4:6]),  # yyyy mm
#                                 (digits[2:6], digits[0:2]),  # mm yyyy
#                             ]
#                             for y, m in combos:
#                                 if re.fullmatch(r"(19|20)\d{2}", y) and 1 <= int(m) <= 12:
#                                     year = int(y)
#                                     month = int(m)
#                                     day = 1
#                                     hour = minute = second = 0
#                                     break
#                             if year is None:
#                                 continue  # No combinación válida
#
#                         if year and month and day:
#                             dt = datetime(year, month, day, hour, minute, second, tzinfo=tz)
#                             iso_str = dt.isoformat()
#                             GV.LOGGER.debug(f"{step_name}🧠 Guessed ISO date {iso_str} from {source.upper()}: {text}")
#                             return iso_str, source.upper()
#
#                     except Exception as e:
#                         GV.LOGGER.warning(f"{step_name}⚠️ Error parsing date from {source} '{text}': {e}")
#                         continue
#
#         GV.LOGGER.debug(f"{step_name}❌ No date found in filename or path: {path}")
#         return None, None

