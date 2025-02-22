import json
import math
import os
import re
import time

from gigachat import GigaChat
import pyperclip


# ---------------------------------
# SETTINGS
# ---------------------------------
settings = {}


def update_settings_from_json() -> None:
    global settings
    try:
        with open("settings.json", "r") as file:
            settings = json.load(file)
            return None
    except:
        with open("settings.json", "r") as file:
            old_settings = file.read()
        with open("old_settings.txt", "w") as file:
            file.write(old_settings)
    make_default_settings_file_json()
    with open("settings.json", "r") as file:
        settings = json.load(file)
    return None


def apply_settings():
    global settings
    with open("settings.json", "w") as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)


def make_default_settings_file_json() -> None:
    default_settings = {"language": "english"}
    with open("settings.json", "w") as file:
        json.dump(default_settings, file, ensure_ascii=False, indent=4)
    return None


def was_settings_file_corrupted() -> bool:
    return "old_settings.txt" in os.listdir()


def get_styles_files():
    return [style for style in os.listdir("styles") if style.endswith(".css")]


update_settings_from_json()

# ---------------------------------
# LOCALISATION
# ---------------------------------packages = []
language = ""
language_packages = []


class LocalisationDict(dict):
    def __missing__(self, key):
        return f"{key}"


def init_localisation_packages():
    global language_packages
    global language
    files = os.listdir("Localisation")
    language_packages = [file for file in files if file[:2] == "I_"]
    try:
        language = settings["language"] if f"I_{settings['language']}.json" in language_packages else ""
    except KeyError:
        pass
    language = language or "english" if any("english" in package for package in language_packages) else \
        language_packages[0][2:-5]
    update_settings_from_json()
    return None


def load_language_package():
    with open(f".\Localisation\I_{language}.json", 'r', encoding='utf-8') as file:
        data = json.load(file)
    return LocalisationDict(**data)


#intervals
def find_r(s, t):
    return "{}%".format(round(math.e ** (-t / s) * 100, 1))


def find_new_s(s, phi, n):
    if phi >= 0.5:
        alpha = 1 - 0.5 / (1 + math.e ** -(n - 3))
        return math.ceil(s * phi * alpha)
    else:
        return math.ceil(s * (phi + 0.1))


g_notes = {}


def update_and_init_notes():
    """Update resources.notes dict with with folders and notes from Notes"""
    global g_notes
    folders = [folder for folder in os.listdir(r".\Notes") if os.path.isdir(rf".\Notes\{folder}")]
    g_notes = {folder: {note: list() for note in os.listdir(rf".\Notes\{folder}")} for folder in folders}
    return None


def update_interval_info_about_note(folder, note, _, s, t, n):
    """Update data of single note in resources.notes"""
    global g_notes
    r = find_r(s, (time.time() - t) / 43200)

    g_notes[folder][note] = [r, s, t, n]


def update_notes_data():
    """Update resources.notes with corresponding data from <note>.json"""
    global g_notes

    try:
        with open("notes.json", "r") as file:
            json_data = json.load(file)
    except:
        with open("notes.json", "w") as file:
            json_data = json.dump(g_notes, file, ensure_ascii=False, indent=4)

    for (folder, notes) in g_notes.items():
        for note in notes.keys():
            try:
                update_interval_info_about_note(folder, note, *json_data[folder][note])
            except:
                g_notes[folder][note] = "NDY"

    with open("notes.json", "w") as file:
        json.dump(g_notes, file, ensure_ascii=False, indent=4)
    return None


def direct_upload_notes():
    global g_notes
    with open("notes.json", "w") as file:
        json.dump(g_notes, file, ensure_ascii=False, indent=4)


def get_note(folder, note):
    with open(rf".\Notes\{folder}\{note}", "r", encoding='utf-8') as file:
        data = file.read()
    return data


#Tests reading
tests = []
collocations = {}


def update_and_init_tests():
    """Update resources.tests list with exiting <test>.json from Tests"""
    global tests
    tests = [file for file in os.listdir(r".\Tests") if file.endswith(".json")]
    return None


def get_tests_files_for_note(note):
    global tests
    return [test for test in tests if re.fullmatch(rf"{note}\.\d+\.json", test)]


def note_name_handler(note, md_postfix=True):
    name = re.search(".+\.md (?=|)", note)[0]
    return name[:-1] if md_postfix else name[:-4]


def get_tests_names_for_note(note):
    names = []
    note = note_name_handler(note, False)
    tests_in_scope = get_tests_files_for_note(note)
    for test in tests_in_scope:
        names.append(collocations[test])
    return names


def update_collocations():
    """Create resources.collocations with names of tests and corresponding files of the tests"""

    global collocations

    for test in tests:
        try:
            with open(rf".\Tests\{test}", "r", encoding='utf-8') as file:
                test_file = json.load(file)
            collocations[test] = test_file["name"]
        except:
            os.remove(rf".\Tests\{test}")
    return None


def get_test_by_name(test_name):
    global collocations

    for file, file_test_name in collocations.items():
        if file_test_name == test_name:
            return file


def get_test_content(test_file):
    with open(rf".\Tests\{test_file}", "r", encoding="utf-8") as file:
        test_data = json.load(file)
    return test_data


##Neural
try:
    auth = settings["auth"]
except:
    pass

def generate_test(amount, topic, note):
    global auth
    with GigaChat(credentials=auth, verify_ssl_certs=False) as giga:
        prompt = "Создайте тест на тему {} с {} вопросами. Выведите результат в формате JSON. Не давай пояснений. Каждый вопрос должен иметь либо варианты ответов (не более 4), либо требовать текстовый ввод. Структура должна точно соответствовать следующему шаблону:".format(
            topic, amount)
        prompt += '''
        
        {
        "name": "Тест по теме {Петр I}",
        "1. Кто такой Петр 1?": {
        "options": {
        "a": "Император Польши",
        "b": "Император России",
        },
        "answer": "b"
        },
        "2. Кто такой Петр 1?": {
        "label": "Введите титул",
        "answer": "Император"
        }
        }
        
        {
        "name": "Тест по теме {тема}",
        "номер. Текст вопроса 1": {
        "options": {
        "a": "вариант ответа 1",
        "b": "вариант ответа 2",
        "c": "вариант ответа 3",
        "d": "вариант ответа 4"
        },
        "answer": "правильный вариант"
        },
        "номер. Текст вопроса 2": {
        "label": "Введите слово/фразу",
        "answer": "правильный ответ"
        }
        }
        Где:
        
        'name' - название теста
        'options' используется для вопросов с выбором ответа
        'label' используется для вопросов с текстовым вводом
        'answer' содержит правильный ответ
        '''
        prompt += "конспект для основы:"
        prompt += note
        response = giga.chat(prompt)
        return re.search("\{.+\}", response.choices[0].message.content, flags=re.DOTALL)[0]


def generate_temp(test):
    with open("temp.json", "w", encoding="utf-8") as file:
        file.write(test)


def get_temp():
    with open("temp.json", "r", encoding="utf-8") as file:
        return json.load(file)

def get_promt(amount, topic, note):
    prompt = "Создайте тест на тему {} с {} вопросами. Выведите результат в формате JSON. Не давай пояснений. Каждый вопрос должен иметь либо варианты ответов (не более 4), либо требовать текстовый ввод. Структура должна точно соответствовать следующему шаблону:".format(
            topic, amount)
    prompt += '''
        
        {
        "name": "Тест по теме {Петр I}",
        "1. Кто такой Петр 1?": {
        "options": {
        "a": "Император Польши",
        "b": "Император России",
        },
        "answer": "b"
        },
        "2. Кто такой Петр 1?": {
        "label": "Введите титул",
        "answer": "Император"
        }
        }
        
        {
        "name": "Тест по теме {тема}",
        "номер. Текст вопроса 1": {
        "options": {
        "a": "вариант ответа 1",
        "b": "вариант ответа 2",
        "c": "вариант ответа 3",
        "d": "вариант ответа 4"
        },
        "answer": "правильный вариант"
        },
        "номер. Текст вопроса 2": {
        "label": "Введите слово/фразу",
        "answer": "правильный ответ"
        }
        }
        Где:
        
        'name' - название теста
        'options' используется для вопросов с выбором ответа
        'label' используется для вопросов с текстовым вводом
        'answer' содержит правильный ответ
        '''
    prompt += "конспект для основы:"
    prompt += note
    pyperclip.copy(prompt)


# ---------------------------------
# ERRORS
# ---------------------------------
errors = {
    "settings_file_corrupted": "All settings have been reset to their default values. Please save any necessary "
                               "settings and delete the old_settings.txt file in the root folder to stop receiving this message",
    "access_to_localisation": "Can't get access to Localisation folder",
    "localisation_is_empty": "Localisation folder is empty",
    "missing_package_for_language": f"The language package for {language} is missing",
    "corrupted_package_for_language": f"Localisation file of {language} is empty or corrupted",
    "missing_readme": "Can't get access to readme.md",
    "missing_faq": "Can't get access to faq.md",
    "missing_notes": "Can't get access to Notes",
    "missed_tests": "Can't get access to Tests",
    "neural_error": "Something went wrong. Please, try again",
}
