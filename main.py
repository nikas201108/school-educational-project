## У тебя часть функционала связана с label. При добавлении процента я поломал обращение через label
import os
import time
from math import floor
import re
import subprocess

from textual import work, on, messages, events
from textual.app import App, ComposeResult
from textual.containers import Center, Container, Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, Label, ListView, ListItem, Markdown, \
    MarkdownViewer, OptionList, TabbedContent, Select, Rule

import resources


class EducationControlApp(App):
    CSS_PATH = rf".\Styles\{resources.settings['css_path']}" if "css_path" in resources.settings else r".\Styles\default.css"

    def __init__(self):
        super().__init__()
        self.language_package = resources.LocalisationDict()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="main-container")
        yield Footer()

    @work
    async def on_mount(self):
        if resources.was_settings_file_corrupted():
            await self.push_screen_wait(WarningWindow(resources.errors["settings_file_corrupted"]))
        await self.init_and_load_localisation()

        #  Building screen
        self.title = self.language_package["title"]
        self.mount_buttons()

    async def init_and_load_localisation(self):
        """Responsible for correct localisation work (initialising of languages and loading language package as
        self.language_package"""

        try:  # trying to init
            resources.init_localisation_packages()
        except FileNotFoundError:
            await self.push_screen_wait(WarningWindow(resources.errors["access_to_localisation"]))
        except IndexError:
            await self.push_screen_wait(WarningWindow(resources.errors["localisation_is_empty"]))

        try:  # trying to load package file
            self.language_package = resources.load_language_package()
        except FileNotFoundError:
            await self.push_screen_wait(WarningWindow(resources.errors["missing_package_for_language"]))
        except:
            await self.push_screen_wait(WarningWindow(resources.errors["corrupted_package_for_language"]))
        self.language_package = self.language_package or resources.LocalisationDict()

    def mount_buttons(self):
        """Create buttons in main menu (#main-container)"""

        buttons = [
            ("take_test", "take_test"),
            ("read", "read"),
            ("settings", "settings"),
            ("faq", "faq"),
            ("credits", "credits"),
        ]
        main_container = self.query_one("#main-container")
        for label_key, button_id in buttons:
            button_label = self.language_package[label_key]
            main_container.mount(Button(button_label, id=button_id))

    def check_existence(self, file, error_key):
        return (file in os.listdir()) or not (self.app.push_screen(WarningWindow(resources.errors[error_key])))

    @on(Button.Pressed, "#credits")
    def open_credits(self):
        self.bell()
        if self.check_existence("readme.md", "missing_readme"):
            self.push_screen(CreditsWindow())

    @on(Button.Pressed, "#faq")
    def open_faq(self):
        self.bell()
        if self.check_existence("faq.md", "missing_faq"):
            self.push_screen(FAQWindow())

    @on(Button.Pressed, "#take_test")
    def open_file_inspector(self):
        self.bell()
        self.push_screen(FileInspector(), self.update_test)

    def update_test(self, status):
        if status == "update":
            self.push_screen(FileInspector(), self.update_test)

    @on(Button.Pressed, "#read")
    def open_reader(self):
        self.bell()
        if self.check_existence("Notes", "missing_notes"):
            self.push_screen(ReadWindow())

    @on(Button.Pressed, "#settings")
    def open_settings(self):
        self.bell()
        self.push_screen(SettingsWindow())


class FileInspector(ModalScreen):
    def __init__(self):
        super().__init__()
        self.highlighted_test = 0
        self.current_tab = 0

        if self.check_existence("Tests", "missed_tests"):
            resources.update_and_init_tests()
            resources.update_collocations()
        if self.check_existence("Notes", "missing_notes"):
            resources.update_and_init_notes()
            resources.update_notes_data()

    def check_existence(self, file, error_key):
        return (file in os.listdir()) or not (self.app.push_screen(ErrorWindow(resources.errors[error_key])))

    class NoteBrowser(Widget):
        def generate_content(self, folder):
            content = []
            for note, info in resources.g_notes[folder].items():
                label = f"{note} | {info if info == 'NDY' else info[0]}"
                content.append(label)
            content = sorted(content, key=self.custom_sort, reverse=True)
            return [ListItem(Label(x)) for x in content]

        def custom_sort(self, item):
            parts = item.split('|')
            value = parts[1].strip()
            if value == "NDY":
                return float('-inf')
            try:
                number = float(value.strip('%'))
                return -number
            except ValueError:
                return float('-inf')

        def compose(self) -> ComposeResult:
            with TabbedContent(*resources.g_notes.keys()):
                for folder in resources.g_notes.keys():
                    yield ListView(*self.generate_content(folder))

    class ButtonPanel(Widget):
        def compose(self) -> ComposeResult:
            with VerticalScroll():
                yield OptionList()
            with Container(id="start-generate-panel"):
                yield Button(self.app.language_package["start_test"], id="start-test-button")
                yield Button(self.app.language_package["generate_test"], id="generate-test-button")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.NoteBrowser()
        yield self.ButtonPanel()

        yield Container(classes="plug")

        with Container(id="file-inspector-exit-button-panel"):
            label = self.app.language_package["exit_inspector"]
            yield Button(label, id="file-inspector-exit-button")

        yield Container(classes="plug")
        yield Container(classes="plug")

        yield Footer()

    @on(Button.Pressed, "#file-inspector-exit-button")
    def exit(self):
        self.dismiss()

    def on_tabbed_content_tab_activated(self, event):
        self.tab = str(event.tab.label)

    def on_list_view_highlighted(self, event):
        self.highlighted_item = event.control.index
        self.note = event.control._nodes[self.highlighted_item].children[0].renderable
        names = resources.get_tests_names_for_note(self.note)
        self.update_option_list(names)

    def update_option_list(self, names):
        option_list_obj = self.query_one("ButtonPanel VerticalScroll OptionList")
        option_list_obj.clear_options()
        is_names_exists = bool(names)
        if is_names_exists:
            option_list_obj.add_options([f"---> {test}" for test in names])
        else:
            option_list_obj.add_option(self.app.language_package["no_data"])
        option_list_obj.can_focus = is_names_exists
        option_list_obj.can_focus_children = is_names_exists

    def on_option_list_option_highlighted(self, event):
        self.test = event.option.prompt[5:]

    @on(Button.Pressed, "#start-test-button")
    def start_test(self):
        try:
            test_file = resources.get_test_by_name(self.test)
            self.app.push_screen(Test(test_file), self.update_resources)
        except: pass


    @on(Button.Pressed, "#generate-test-button")
    def generate(self):
        try:
            test = resources.generate_test(5, resources.note_name_handler(self.note, False),
                                             resources.get_note(self.tab, resources.note_name_handler(self.note, True)))
            resources.generate_temp(test)
            test = resources.get_temp()
            self.app.push_screen(Test("temp"), self.update_resources)
        except FileNotFoundError:
            pass
        except:
            self.app.push_screen(WarningWindow(resources.errors["neural_error"]))

    def update_resources(self, phi):
        note = resources.note_name_handler(self.note, True)
        data = resources.g_notes[self.tab][note]
        try:
            new_s = resources.find_new_s(data[1], phi, data[3])
            resources.g_notes[self.tab][note] = ["100.0%", new_s, time.time(), (data[3] + 1) * floor(phi)]
        except:
            resources.g_notes[self.tab][note] = ["100.0%", resources.settings["s_standard"], time.time(), 0]
        resources.direct_upload_notes()
        self.dismiss("update")


class Test(ModalScreen):
    def __init__(self, test_file):
        super().__init__()
        if test_file != "temp":
            self.test_data = resources.get_test_content(test_file)
        else:
            self.test_data = resources.get_temp()
        self.answers = {}
        self.score = 0
        self.test_form = None
        self.test_form_questions = None

    class TestForm(Widget):
        def __init__(self, test_data):
            super().__init__()
            self.test_data = test_data
            self.questions = []

        def compose(self) -> ComposeResult:
            with Container(id="test-container"):
                with Center():
                    label = self.test_data["name"]
                    yield Label(label, classes="test-name")
                with Center():
                    with VerticalScroll():
                        for question in list(self.test_data.keys())[1:]:
                            yield from self.create_exercise(question)
                        yield Button(self.app.language_package["end_test"], id="end-test")

        def create_exercise(self, question):
            question_container = Vertical(classes="question-form")
            with question_container:
                yield Label(question)
                if "options" in self.test_data[question]:
                    yield from self.create_buttons_grid(question)
                elif "label" in self.test_data[question]:
                    yield Input(placeholder=self.test_data[question]["label"], classes="input-answer")

            self.questions.append([question_container, question])

        def create_buttons_grid(self, question):
            options_labels = [f"{i}. {option}" for (i, option) in self.test_data[question]["options"].items()]
            with Grid(classes="question-panel-button"):
                for option in options_labels:
                    current_option = Button(option)
                    yield current_option
                    if self.test_data[question]["answer"] == option[0]:
                        current_option.add_class("right-answer-missed-off")

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.TestForm(self.test_data)
        yield Footer()

    def on_mount(self):
        self.test_form = self.query_one("TestForm")
        self.test_form_questions = self.test_form.questions

    def clear_buttons(self, vertical):
        for button in vertical.query(f"Grid Button"):
            button.remove_class("wrong-answer-off")
            button.remove_class("chosen-answer")

    @on(Button.Pressed, ".question-panel-button Button")
    def answer_chosen(self, event):
        id = [event.button.parent.parent in vertical_and_question for vertical_and_question in
              self.test_form_questions].index(True)
        vertical = self.test_form_questions[id][0]
        answer = self.test_data[self.test_form_questions[id][1]]["answer"]

        self.clear_buttons(vertical)
        event.button.add_class("chosen-answer")
        if str(event.button.label[0]) != answer:
            event.button.add_class("wrong-answer-off")
        else:
            event.button.add_class("right-answer-off")

    def show_button_result(self):
        for button in self.query(".question-panel-button Button"):
            button.remove_class("chosen-answer")
            button.disabled = True
        self.query(".wrong-answer-off").toggle_class("wrong-answer")
        self.query(".right-answer-off").toggle_class("right-answer")
        self.query(".right-answer-missed-off").toggle_class("right-answer-missed")

    def show_label_result(self):
        def text_handler(string):
            return string.lower().replace(" ", "")

        for inp in self.query(".input-answer"):
            id = [inp.parent in vertical_and_question for vertical_and_question in
                  self.test_form_questions].index(True)
            answer = self.test_data[self.test_form_questions[id][1]]["answer"]
            inp_value = inp.value

            if text_handler(inp_value) == text_handler(answer):
                inp.toggle_class("input-answer-right")
            elif inp.value.lower() == "":
                inp.toggle_class("input-answer-missed")
                localistion = [self.app.language_package["empty"], self.app.language_package["right_answer"]]
                inp.value = f"{localistion[0]} | {localistion[1]}: {answer}"
            else:
                localistion = self.app.language_package["right_answer"]
                inp.value = f"{inp.value} | {localistion}: {answer}"
                inp.toggle_class("input-answer-wrong")
            inp.can_focus = False

    @on(Button.Pressed, "#end-test")
    def show_results(self, event):
        self.show_button_result()
        self.show_label_result()
        right_answers = len(self.query(".right-answer")) + len(self.query(".input-answer-right"))
        wrong_answers = len(self.query(".wrong-answer")) + len(self.query(".input-answer-wrong"))
        missed_answers = len(self.query(".right-answer-missed")) + len(self.query(".input-answer-missed"))
        try:
            self.score = right_answers / (wrong_answers + missed_answers)
        except ZeroDivisionError:
            self.score = 1
        event.button.remove()
        self.query_one(VerticalScroll).mount(Button(self.app.language_package["exit_test"], id="exit-test"))

    @on(Button.Pressed, "#exit-test")
    def exit(self):
        self.dismiss(self.score)


class ReadWindow(ModalScreen):
    class OnlyMarkdownDirectoryTree(DirectoryTree):
        def filter_paths(self, folder):
            return [obj for obj in folder if obj.name.endswith(".md") or obj.is_dir()]

    def __init__(self):
        super().__init__()
        self.dir_tree = self.OnlyMarkdownDirectoryTree(r".\Notes")

    def compose(self) -> ComposeResult:
        with Container():
            yield self.dir_tree

            label = self.app.language_package["exit_notes"]
            yield Button(label)
        yield MarkdownViewer(r"", show_table_of_contents=True)

    def on_directory_tree_file_selected(self, file):
        with open(str(file.path), 'r', encoding='utf-8') as f:
            text = f.read()

        self.query_one(MarkdownViewer).remove()
        self.mount(MarkdownViewer(text, show_table_of_contents=True))

    def on_button_pressed(self):
        self.dismiss()


class SettingsWindow(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            with Center():
                yield Label(self.app.language_package["choose_another_theme"])
            with Center():
                try:
                    yield Select([(line[2:-5].capitalize(), line[2:-5].capitalize()) for line in resources.language_packages],
                                 value=resources.settings["language"].capitalize(), allow_blank=False, id="language-select")
                except: yield Label(resources.errors["access_to_localisation"])
            with Center():
                yield Select([(line, line) for line in resources.get_styles_files()], allow_blank=False, id="style-select")

            with Center():
                yield Input(placeholder="Enter Authority key from Gigachat", id='key-input')

            with Center():
                yield Input(placeholder="S value for you", id='s-input', type="integer")

            with Center():
                yield Button(self.app.language_package["apply_settings"])

        yield Footer()

    def on_mount(self):
        if "css_path" in resources.settings:
            self.query_one("#style-select").value = resources.settings["css_path"]
        else:
            self.query_one("#style-select").value = "default.css"

        if "auth" in resources.settings:
            self.query_one("#key-input").value = resources.settings["auth"]

        if "s-input" in resources.settings:
            self.query_one("#s-input").value = resources.settings["s-input"]
        else:
            self.query_one("#s-input").value = "3"


    @on(Select.Changed, "#language-select")
    def language_select_changed(self, event: Select.Changed) -> None:
        resources.settings["language"] = str(event.value).lower()

    @on(Select.Changed, "#style-select")
    def style_select_changed(self, event: Select.Changed) -> None:
        resources.settings["css_path"] = event.value

    @on(Input.Changed, "#key-input")
    def key_inp_changed(self, event: Select.Changed) -> None:
        resources.settings["auth"] = event.value

    @on(Input.Changed, "#s-input")
    def s_inp_changed(self, event: Select.Changed) -> None:
        try:
            resources.settings["s_standard"] = int(event.value)
        except:
            pass

    def on_button_pressed(self):
        resources.apply_settings()
        self.dismiss()

        self.app.push_screen(InfoWindow(self.app.language_package["setting_applied_info"]))


class FAQWindow(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield MarkdownContainerViewer("faq", r"faq.md")
        yield Footer()

    def on_button_pressed(self):
        self.dismiss()


class CreditsWindow(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield MarkdownContainerViewer("credits", r"readme.md")
        yield Footer()

    def on_button_pressed(self):
        self.dismiss()


class ErrorWindow(ModalScreen):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        yield Label(self.text)


class WarningWindow(ModalScreen):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Center():
            yield Label(self.text)
        with Center():
            yield Button("Ok")

    def on_button_pressed(self):
        self.dismiss()


class InfoWindow(ModalScreen):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def compose(self) -> ComposeResult:
        with Center():
            yield Label(self.text)
        with Center():
            yield Button("Ok")

    def on_button_pressed(self):
        self.dismiss()


class MarkdownContainerViewer(Widget):
    def __init__(self, belong, path):
        super().__init__()
        self.belong = belong
        with open(path, "r") as readme:
            self.data = readme.read()

    def compose(self) -> ComposeResult:
        with Container(id=f"{self.belong}-container"):
            with VerticalScroll():
                yield Markdown(self.data)
            button_label = self.app.language_package[f"exit_{self.belong}"]
            yield Button(button_label)


EducationControlApp().run()
