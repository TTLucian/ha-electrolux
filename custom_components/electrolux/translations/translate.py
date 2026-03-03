"""Translation script using deep-translator for all languages."""

import json
import os
import time

from deep_translator import GoogleTranslator


def load_en_data():
    """Load English translations."""
    base_dir = os.path.dirname(__file__)
    en_path = os.path.join(base_dir, "en.json")
    with open(en_path, encoding="utf-8") as file:
        return json.load(file)


def translate_text(text, dest_language):
    """Translate text to destination language."""
    if not text or text.strip() == "":
        return text

    try:
        translator = GoogleTranslator(source="en", target=dest_language)
        result = translator.translate(text)
        return result
    except Exception as e:
        print(f"Translation failed for '{text[:50]}...' to {dest_language}: {e}")
        return text  # Return original text if translation fails


def translate_dict(data, dest_language):
    """Translate dictionary values recursively."""
    translated = {}
    for key, value in data.items():
        if isinstance(value, dict):
            translated[key] = translate_dict(value, dest_language)
        else:
            translated[key] = translate_text(value, dest_language)
        # Small delay to avoid rate limiting
        time.sleep(0.1)
    return translated


def main():
    """Main translation function."""
    # Read English translations
    en_data = load_en_data()

    # Define the target languages (excluding English)
    languages = {
        "български": "bg",
        "český": "cs",
        "Dansk": "da",
        "Deutsch": "de",
        "ελληνικός": "el",
        "Español": "es",
        "eesti": "et",
        "Suomi": "fi",
        "Français": "fr",
        "Hrvatski": "hr",
        "magyar": "hu",
        "Italiano": "it",
        "Lëtzebuergesch": "lb",
        "lietuvių": "lt",
        "latviešu": "lv",
        "nederlands": "nl",
        "norsk": "no",
        "polski": "pl",
        "Português Brasil": "pt_br",
        "Português": "pt",
        "Română": "ro",
        "русский": "ru",
        "slovenský": "sk",
        "slovenščina": "sl",
        "Svenska": "sv",
        "Türkçe": "tr",
        "Українська": "uk",
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
    for language_name, language_code in languages.items():
        if language_code == "en":
            continue
        # Skip manually translated languages
        if language_code in manually_translated:
            print(
                f"Skipping {language_name} ({language_code}.json) - already manually translated"
            )
            continue
        print(f"Translating {language_name} ({language_code}.json)")

        try:
            translated_data = translate_dict(en_data, language_code)

            output_path = os.path.join(
                os.path.dirname(__file__), f"{language_code}.json"
            )
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(translated_data, file, ensure_ascii=False, indent=4)

            print(f"✓ Completed {language_name}")

        except Exception as e:
            print(f"✗ Failed to translate {language_name}: {e}")
            # Fallback to English
            output_path = os.path.join(
                os.path.dirname(__file__), f"{language_code}.json"
            )
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(en_data, file, ensure_ascii=False, indent=4)

    print("\n🎉 Translation completed for all languages!")


if __name__ == "__main__":
    main()
