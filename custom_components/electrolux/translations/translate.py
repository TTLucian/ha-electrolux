"""Translation script using deep-translator for all languages."""

import json
import os
import re
import time

from deep_translator import GoogleTranslator

NO_TRANSLATION_FOUND = "No translation was found using the current translator"


def load_en_data():
    """Load English translations."""
    base_dir = os.path.dirname(__file__)
    en_path = os.path.join(base_dir, "en.json")
    with open(en_path, encoding="utf-8") as file:
        return json.load(file)


def translate_text(text, translator, cache):
    """Translate text to destination language while preserving placeholders.

    Placeholders like {variable} are extracted before translation and restored
    after, ensuring they remain in their original form with English names.
    Text entirely enclosed in braces is skipped from translation.
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

    try:
        result = translator.translate(working_text)
        if not result:
            cache[text] = text
            return text

        # Restore original placeholders
        for marker, placeholder in placeholder_map.items():
            result = result.replace(marker, placeholder)

        cache[text] = result
        return result
    except Exception as e:
        # Some short labels are not translatable for certain language pairs.
        # Keep the original source text without treating this as fatal.
        if NO_TRANSLATION_FOUND in str(e):
            cache[text] = text
            return text
        print(f"Translation failed for '{text[:50]}...': {e}")
        cache[text] = text
        return text


def translate_value(value, translator, cache):
    """Translate nested values recursively while preserving non-string types."""
    if isinstance(value, dict):
        translated = {}
        for key, nested_value in value.items():
            translated[key] = translate_value(nested_value, translator, cache)
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        return translated

    if isinstance(value, list):
        return [translate_value(item, translator, cache) for item in value]

    if isinstance(value, str):
        return translate_text(value, translator, cache)

    return value


def main():
    """Main translation function."""
    # Read English translations
    en_data = load_en_data()

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
        "nl": ("nederlands", "nl"),
        "no": ("norsk", "no"),
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
        # Skip manually translated languages
        if language_code in manually_translated:
            print(f"Skipping {language_name} ({language_code}.json) - already manually translated")
            continue
        print(f"Translating {language_name} ({language_code}.json)")

        try:
            translator = GoogleTranslator(source="en", target=translator_target)
            cache = {}
            translated_data = translate_value(en_data, translator, cache)

            output_path = os.path.join(os.path.dirname(__file__), f"{language_code}.json")
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(translated_data, file, ensure_ascii=False, indent=4)

            print(f"✓ Completed {language_name}")

        except Exception as e:
            print(f"✗ Failed to translate {language_name}: {e}")
            # Fallback to English
            output_path = os.path.join(os.path.dirname(__file__), f"{language_code}.json")
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(en_data, file, ensure_ascii=False, indent=4)

    print("\n🎉 Translation completed for all languages!")


if __name__ == "__main__":
    main()
