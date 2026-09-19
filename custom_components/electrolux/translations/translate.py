"""Translation script using deep-translator for all languages."""

import json
import os
import re
import sys
import time

from deep_translator import GoogleTranslator, MyMemoryTranslator

NO_TRANSLATION_FOUND = "No translation was found using the current translator"

# MyMemory uses the "{lang}-{region}" code format (e.g. bg-BG, pt-BR), unlike
# Google's plain two-letter codes. Map the script's book codes to MyMemory's.
_MYMEMORY_TARGETS = {
    "bg": "bg-BG",
    "cs": "cs-CZ",
    "da": "da-DK",
    "de": "de-DE",
    "el": "el-GR",
    "et": "et-EE",
    "fi": "fi-FI",
    "fr": "fr-FR",
    "hr": "hr-HR",
    "hu": "hu-HU",
    "it": "it-IT",
    "lv": "lv-LV",
    "lt": "lt-LT",
    "lb": "lb-LU",
    "nb": "nb-NO",
    "nl": "nl-NL",
    "nn": "nn-NO",
    "pl": "pl-PL",
    "pt": "pt-PT",
    "pt_br": "pt-BR",
    "ro": "ro-RO",
    "ru": "ru-RU",
    "sk": "sk-SK",
    "sl": "sl-SI",
    "es": "es-ES",
    "sv": "sv-SE",
    "tr": "tr-TR",
    "uk": "uk-UA",
}


def _make_translator(backend: str, target: str):
    """Build a translator for the given backend and target-language code."""
    if backend == "mymemory":
        # Free, no API key. Note: anonymous quota is limited (~5k chars/day per IP),
        # so it is best for topping up a handful of missing keys.
        mm_target = _MYMEMORY_TARGETS.get(target) or target
        return MyMemoryTranslator(source="en-GB", target=mm_target)
    return GoogleTranslator(source="en", target=target)


# Google's free, unauthenticated endpoint allows roughly 5 requests/second per
# IP. Stay comfortably below that to avoid HTTP 429 rate limiting. Increase if a
# run is interrupted by "too many requests" errors over an extended period.
RATE_LIMIT_DELAY = 0.4  # seconds to wait after each translation request
RATE_LIMIT_MAX_RETRIES = 4  # retries for transient rate-limit/server errors
RATE_LIMIT_RETRY_BACKOFF = 2.0  # base seconds for exponential backoff
# Abort a language once this many *consecutive* keys fail as rate-limited, instead
# of grinding through every remaining key and sleeping the full backoff each time.
RATE_LIMIT_ABORT_AFTER = 3


class TranslationError(Exception):
    """Raised when a value cannot be translated after retries.

    This is distinct from "not translatable" (Google returns no translation): it
    signals a transient/external failure (rate limit, server error) so callers can
    skip writing the key and retry it on a later run.

    ``rate_limited`` is True when the failure was a retryable rate-limit/server
    error (as opposed to some other unexpected error).
    """

    def __init__(self, message, rate_limited=False):
        super().__init__(message)
        self.rate_limited = rate_limited


class RateLimitError(TranslationError):
    """Raised to stop translating a language after repeated rate-limited keys.

    Lets the script move on (and leave the file unchanged) instead of hammering an
    already-rate-limited IP and sleeping the full backoff for every remaining key.
    """


# Set to True by --debug to print per-request diagnostics.
_DEBUG_ENABLED = False


def _debug(msg):
    """Print a diagnostic line when --debug is enabled."""
    if _DEBUG_ENABLED:
        print(f"[debug] {msg}")


def _probe(translator):
    """One fast (non-retried) request to check whether the backend is reachable.

    Returns ``(ok, message)``. Used to abort a rate-limited run immediately instead
    of waiting through per-key retries/backoff across every language.
    """
    try:
        translator.translate("ok")
        return True, ""
    except Exception as e:
        return False, str(e)


def load_en_data():
    """Load English translations."""
    base_dir = os.path.dirname(__file__)
    en_path = os.path.join(base_dir, "en.json")
    with open(en_path, encoding="utf-8") as file:
        return json.load(file)


def _throttle():
    """Sleep between translation requests to respect the provider rate limit."""
    time.sleep(RATE_LIMIT_DELAY)


def _is_transient_error(error: str) -> bool:
    """Return True when an exception message looks like a retryable failure."""
    lowered = error.lower()
    return (
        "too many requests" in lowered
        or "server error" in lowered
        or "429" in error
        or "5 0" in error  # HTTP 5xx "50x"
    )


def _translate_with_retry(working_text, translator):
    """Call the translator, retrying transient errors with exponential backoff.

    Returns the translated string. On "no translation found" returns the source
    (working) text. Raises ``TranslationError`` when the request keeps failing
    after retries, with ``rate_limited`` set for rate-limit/server failures.
    """
    last_transient = False
    for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
        try:
            result = translator.translate(working_text)
            _debug(f"translated {working_text[:40]!r} -> {result[:40]!r}")
            _throttle()
            return result
        except Exception as e:
            error = str(e)
            _debug(f"request {working_text[:40]!r} attempt {attempt} error: {type(e).__name__}: {error}")
            if NO_TRANSLATION_FOUND in error:
                # Some short labels genuinely aren't translatable for a pair.
                _throttle()
                return working_text
            last_transient = _is_transient_error(error)
            if attempt < RATE_LIMIT_MAX_RETRIES and last_transient:
                wait = RATE_LIMIT_RETRY_BACKOFF * (2**attempt)
                _debug(f"transient failure detected; backoff {wait:.1f}s")
                time.sleep(wait)
                continue
            _throttle()
            raise TranslationError(f"Could not translate: {error}".strip(), rate_limited=last_transient)
    raise TranslationError(f"Could not translate: {working_text[:50]!r}", rate_limited=last_transient)


def translate_text(text, translator, cache):
    """Translate text to destination language while preserving placeholders.

    Placeholders like {variable} are extracted before translation and restored
    after, ensuring they remain in their original form with English names.
    Text entirely enclosed in braces is skipped from translation.

    Raises ``TranslationError`` when a value could not be translated after retries
    (rate limiting / server error), so the caller can leave the key missing for a
    later retry instead of silently writing the English source.
    """
    if not isinstance(text, str) or text.strip() == "":
        return text

    if text in cache:
        return cache[text]

    # If the entire text is enclosed in braces, skip translation
    if re.match(r"^\{.*\}$", text.strip()):
        return text

    # Extract all placeholders like {variable} and store them.
    # We keep the exact placeholder text to avoid changing placeholder names.
    placeholders = re.findall(r"\{[^{}]+\}", text)

    # Replace placeholders with unique markers to avoid translation
    working_text = text
    placeholder_map = {}
    for i, placeholder in enumerate(placeholders):
        marker = f"__PH_{i}__"
        placeholder_map[marker] = placeholder
        working_text = working_text.replace(placeholder, marker, 1)

    result = _translate_with_retry(working_text, translator)

    # Restore original placeholders
    for marker, placeholder in placeholder_map.items():
        result = result.replace(marker, placeholder)

    cache[text] = result
    return result


def translate_value(value, translator, cache):
    """Translate nested values recursively while preserving non-string types.

    A ``TranslationError`` from a failing ``translate_text`` call propagates to the
    caller (used by ``translate_missing`` to skip a key and by ``--force`` mode to
    abort safely).
    """
    if isinstance(value, dict):
        return {key: translate_value(nested_value, translator, cache) for key, nested_value in value.items()}

    if isinstance(value, list):
        return [translate_value(item, translator, cache) for item in value]

    if isinstance(value, str):
        return translate_text(value, translator, cache)

    return value


def translate_missing(en_value, existing_value, translator, cache, stats=None):
    """Translate only values missing (or broken/empty) relative to the English source.

    Walks the English catalog (``en_value``) and the existing translation file
    (``existing_value``) together:

    * A leaf that already has a valid, non-empty translation is kept verbatim.
    * A leaf that is missing, empty (``""``), or ``{}`` is translated and added.
    * ``RateLimitError`` is never swallowed: once too many consecutive keys fail as
      rate-limited, it propagates so ``main()`` can abort the language and leave the
      file unchanged. Other transient failures skip the key (it stays missing and is
      retried next run). English is never written as a substitute.
    """
    if isinstance(en_value, dict):
        existing = existing_value if isinstance(existing_value, dict) else {}
        result = {}
        for key, en_nested in en_value.items():
            if isinstance(en_nested, dict):
                sub = translate_missing(en_nested, existing.get(key), translator, cache, stats)
                # Only keep non-empty sub-dicts so we never emit `{}` for a
                # translation group whose leaves failed / are still missing.
                if sub:
                    result[key] = sub
            else:
                val = _translate_leaf(en_nested, existing.get(key), translator, cache, stats)
                if val is not _MISSING:
                    result[key] = val
        return result

    if isinstance(en_value, list):
        existing = existing_value if isinstance(existing_value, list) else None
        if isinstance(existing, list) and len(existing) == len(en_value):
            return [translate_missing(e, x, translator, cache, stats) for e, x in zip(en_value, existing)]
        out = []
        for item in en_value:
            val = _translate_leaf(item, None, translator, cache, stats)
            if val is not _MISSING:
                out.append(val)
        return out

    # Non-dict, non-list leaf reached directly (only happens on non-catalog input).
    return _translate_leaf(en_value, existing_value, translator, cache, stats)


_MISSING = object()


def _translate_leaf(en_nested, existing_value, translator, cache, stats):
    """Translate or keep a single leaf value, updating ``stats``.

    Returns ``_MISSING`` when the leaf could not be translated (so the caller omits
    it and leaves it missing for a later retry), or the translated/kept value.
    """
    if not isinstance(en_nested, str):
        # Non-string scalar (bool/int/float/None): no translation needed.
        return existing_value if existing_value is not None else en_nested

    # Keep an existing, valid, non-empty translation verbatim.
    if isinstance(existing_value, str) and existing_value != "":
        return existing_value

    try:
        translated = translate_value(en_nested, translator, cache)
    except RateLimitError:
        raise
    except TranslationError as err:
        if stats is not None:
            stats["skipped"] += 1
            if err.rate_limited:
                stats["rate_limited_run"] += 1
                _debug(f"skip (rate-limited) {en_nested[:40]!r} — {stats['rate_limited_run']} consecutive")
                if stats["rate_limited_run"] >= RATE_LIMIT_ABORT_AFTER:
                    raise RateLimitError(f"{stats['rate_limited_run']} consecutive rate-limited keys") from err
            else:
                stats["rate_limited_run"] = 0
                _debug(f"skip (non-transient) {en_nested[:40]!r}: {err}")
        return _MISSING

    if stats is not None:
        stats["added"] += 1
        stats["rate_limited_run"] = 0
    return translated


def missing_leaf_count(en_value, existing_value, prefix=""):
    """Count leaf paths needing (re)translation.

    A leaf counts as done only when the existing file already holds a non-empty
    string, so missing, ``{}``, and empty ``""`` values are all reported and thus
    (re-)translated.
    """
    if isinstance(en_value, dict):
        existing = existing_value if isinstance(existing_value, dict) else {}
        return sum(
            missing_leaf_count(en_nested, existing.get(key), f"{prefix}{key}.") for key, en_nested in en_value.items()
        )
    return 0 if isinstance(existing_value, str) and existing_value != "" else 1


def main():
    """Main translation function."""
    # Read English translations
    en_data = load_en_data()

    # Optional --force flag re-translates every key from scratch, ignoring
    # any existing translations.
    force = "--force" in sys.argv

    # Optional --lang {code} [{code} ...]: translate only these languages.
    only_langs = None
    if "--lang" in sys.argv:
        idx = sys.argv.index("--lang")
        only_langs = set()
        for tok in sys.argv[idx + 1 :]:
            if tok.startswith("-"):
                break
            only_langs.add(tok.lower())

    # Optional --delay SECONDS: override the per-request throttle. Use a lower
    # value (e.g. --delay 0.1) when your IP is not rate-limited; keep the default
    # otherwise.
    global RATE_LIMIT_DELAY
    if "--delay" in sys.argv:
        try:
            RATE_LIMIT_DELAY = max(0.0, float(sys.argv[sys.argv.index("--delay") + 1]))
        except ValueError, IndexError:
            pass

    # Optional --backend {google|mymemory}: which free provider to use.
    # Use "mymemory" to work around a Google IP rate limit (has its own, smaller
    # daily quota). Defaults to google.
    backend = "google"
    if "--backend" in sys.argv:
        idx = sys.argv.index("--backend")
        if idx + 1 < len(sys.argv):
            backend = sys.argv[idx + 1].lower()

    # Optional --debug: print per-request / per-key diagnostics.
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = "--debug" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print(
            "Usage: python translate.py [--force] [--lang it es de ...] [--delay 0.1] [--backend google|mymemory] [--debug]"
        )
        print("  --force         re-translate every key from scratch")
        print("  --lang CODE...  only translate the given language codes (e.g. it es de)")
        print("  --delay SECONDS override the per-request throttle (default 0.4s)")
        print("  --backend NAME  google (default) or mymemory (use if Google is rate-limiting you)")
        print("  --debug         print per-request diagnostics")
        return

    # Fast backend probe: if the provider is rate-limiting our IP, stop immediately
    # with the raw error instead of waiting through per-key backoff across 26 languages.
    try:
        probe_tr = _make_translator(backend, "bg")
        ok, probe_msg = _probe(probe_tr)
    except Exception as e:
        ok, probe_msg = False, str(e)
    if not ok:
        print("⛔ Translation backend is not responding:")
        print(f"   {probe_msg}")
        print("   This is a server-side rate limit on your IP.")
        print("   Wait for it to reset, or try a different backend: python translate.py --backend mymemory")
        print("   No translation files were changed.")
        return

    # Define the target languages (excluding English)
    languages = {
        "bg": ("български", "bg"),
        "cs": ("český", "cs"),
        "da": ("Dansk", "da"),
        "de": ("Deutsch", "de"),
        "el": ("ελληνικός", "el"),
        "es": ("Español", "es"),
        "et": ("eesti", "et"),
        "fi": ("Suomi", "fi"),
        "fr": ("Français", "fr"),
        "hr": ("Hrvatski", "hr"),
        "hu": ("magyar", "hu"),
        "it": ("Italiano", "it"),
        "lb": ("Lëtzebuergesch", "lb"),
        "lt": ("lietuvių", "lt"),
        "lv": ("latviešu", "lv"),
        "nb": ("bokmål", "nb"),
        "nl": ("nederlands", "nl"),
        "nn": ("nynorsk", "nn"),
        "pl": ("polski", "pl"),
        "pt_br": ("Português Brasil", "pt"),
        "pt": ("Português", "pt"),
        "ro": ("Română", "ro"),
        "ru": ("русский", "ru"),
        "sk": ("slovenský", "sk"),
        "sl": ("slovenščina", "sl"),
        "sv": ("Svenska", "sv"),
        "tr": ("Türkçe", "tr"),
        "uk": ("Українська", "uk"),
    }

    # Skip languages that are already manually translated
    manually_translated = [
        # "de",
        # "fr",
        # "es",
        # "it",
        # "nl",
        # "pl",
        # "sv",
        # "da",
        # "no",
        # "pt",
        # "ru",
    ]
    for language_code, (language_name, translator_target) in languages.items():
        if language_code == "en":
            continue
        if only_langs is not None and language_code.lower() not in only_langs:
            continue
        # Skip manually translated languages
        if language_code in manually_translated:
            print(f"Skipping {language_name} ({language_code}.json) - already manually translated")
            continue

        output_path = os.path.join(os.path.dirname(__file__), f"{language_code}.json")

        # Load any existing translations so only missing keys are re-translated.
        existing_data = {}
        if not force:
            try:
                with open(output_path, encoding="utf-8") as file:
                    existing_data = json.load(file)
            except OSError, json.JSONDecodeError:
                existing_data = {}

        # Skip languages that are already fully translated — no network / translator
        # work at all for them.
        if not force:
            missing = missing_leaf_count(en_data, existing_data)
            _debug(f"{language_code}: {missing} keys need translation")
            if missing == 0:
                print(f"⏭ {language_name} already up to date (no missing keys)")
                continue

        print(f"Translating {language_name} ({language_code}.json)")

        try:
            translator = _make_translator(backend, translator_target)
            cache = {}
            if force:
                translated_data = translate_value(en_data, translator, cache)
            else:
                stats = {"added": 0, "skipped": 0, "rate_limited_run": 0}
                translated_data = translate_missing(en_data, existing_data, translator, cache, stats)

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(translated_data, file, ensure_ascii=False, indent=4)

            if force:
                print(f"✓ Completed {language_name} (forced full re-translation)")
            elif stats["skipped"]:
                print(
                    f"✓ Completed {language_name} (+{stats['added']} new, "
                    f"{stats['skipped']} skipped — rerun to retry the skipped keys)"
                )
            else:
                print(f"✓ Completed {language_name} (+{stats['added']} new keys)")

        except RateLimitError as e:
            # The IP is almost certainly globally rate-limited; stop the whole run
            # rather than grinding through the remaining languages/keys.
            print(f"⏸ {language_name} paused — {e}. Wait a while, then rerun. (file left unchanged)")
            break
        except Exception as e:
            print(f"✗ Failed to translate {language_name}: {e} (file left unchanged)")

    print("\n🎉 Translation run finished!")


if __name__ == "__main__":
    main()
