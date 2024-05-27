

import os
import subprocess
import tkinter as tk
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tkinter import filedialog as file
from tkinter import messagebox as msg
from tkinter import simpledialog as dlg
from tkinter import ttk
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Union


from dynpy.service import EmbedPython, PythonPathFile, PythonSitePackage
from dynpy.ui import utils


class IPyConfService(Protocol):

    def embed_versions(self) -> List[EmbedPython]:
        ...

    def embed_python_by(self, name: str) -> Optional[EmbedPython]:
        ...

    def site_package_from(self, embed: EmbedPython) -> PythonSitePackage:
        ...

    def save_site_package(self, site: PythonSitePackage) -> None:
        ...

    def user_site_package_of(self, embed: EmbedPython) -> Path:
        ...


class Event(Enum):
    SELECTION = "selection_changed"
    PYTHON = "python_changed"
    PATH_ADD = "python_add"
    PATH_REMOVE = "python_remove"


@dataclass
class PathEntryViewModel:
    path: str
    parent_uuid: str
    uuid: str = ""
    changed: bool = False

    @property
    def name(self) -> str:
        return self.path


@dataclass
class PathFileViewModel:
    path: Path
    content: List[PathEntryViewModel]
    model_uuid: str = ""
    parent_uuid: str = ""
    changed: bool = False

    @property
    def is_empty(self) -> bool:
        return len(self.content) == 0

    @property
    def uuid(self) -> str:
        return self.model_uuid

    @uuid.setter
    def uuid(self, uuid: str) -> None:
        self.model_uuid = uuid
        for child in self.content:
            child.parent_uuid = uuid

    @property
    def name(self) -> str:
        return self.path.name

    def add(self, model: PathEntryViewModel) -> None:
        if model in self.content:
            return
        self.content.append(model)
        self.changed = True

    def remove(self, model: PathEntryViewModel) -> None:
        if model not in self.content:
            return
        self.content.remove(model)
        self.changed = True

    def create(self, path: str) -> PathEntryViewModel:
        model = PathEntryViewModel(
            parent_uuid=self.uuid, path=path, changed=True
        )
        self.add(model)
        return model


def create_view_model(file: PythonPathFile) -> PathFileViewModel:
    content = [
        PathEntryViewModel(parent_uuid="", path=path) for path in file.content
    ]
    return PathFileViewModel(file.path, content=content)


class PythonConfigController:
    listeners: Dict[Event, List[Callable]] = {}

    def __init__(self, service: IPyConfService) -> None:
        self.service = service
        self.last_directory = os.getenv("USERPROFILE")
        self.uuid: Dict[str, Union[PathFileViewModel, PathEntryViewModel]] = {}
        self.deleted: List[str] = []
        self.current_id: Optional[str] = None
        self.python: Optional[EmbedPython] = None
        self.master: Optional[tk.Misc] = None

    def reset(self):
        self.uuid.clear()
        self.deleted.clear()
        self.current_id = None
        self.python = None

    def get_python_versions(self) -> List[str]:
        return [py.full_name for py in self.service.embed_versions()]

    def user_site_package_of(self, python: Optional[EmbedPython]) -> List[PathFileViewModel]:
        if python is None:
            return []
        site_package = self.service.site_package_from(python)
        return [create_view_model(file=file) for file in site_package.path_files]

    def register(self, event: Event, callback: Callable):
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)

    def fire_event(self, event: Event, *args, **kwargs):
        for callback in self.listeners.get(event, []):
            callback(*args, **kwargs)

    def fire_python_changed(self, version: str):
        python = self.service.embed_python_by(version)
        if python is None:
            raise Exception(f"Python {version} not found")
        if self.python == python:
            return
        self.reset()
        self.python = python
        self.fire_event(Event.PYTHON, python=python)
        self.fire_selection_changed()

    def fire_selection_changed(self):
        model = None
        if self.current_id is not None:
            model = self.uuid.get(self.current_id, None)
        self.fire_event(Event.SELECTION, python=self.python, path=model)

    def ask_safe_changes(self) -> bool:
        return msg.askyesno(
            parent=self.master,
            title="Änderungen speichern",
            message="Nicht gespeicherte Änderungen zuerst speichern?",
        )

    def contains_unsaved(self) -> bool:
        if len(self.deleted) > 0:
            return True
        if not any(model.changed for _, model in self.uuid.items()):
            return False
        return self.ask_safe_changes()

    def on_version_select(self, event: tk.Event):
        if self.python is not None and self.contains_unsaved():
            return
        box = utils.get_entry(event, tk.Listbox)
        if box is None:
            return
        index = box.curselection()
        if len(index) == 0:
            return
        selected = box.get(index)
        self.fire_python_changed(selected)

    def _get_selected_id(self, event: tk.Event) -> str:
        tree = utils.get_entry(event, ttk.Treeview)
        if tree is None:
            message = f"Except Treeview but got {type(event.widget)}"
            raise Exception(message)
        self.current_id = tree.selection()[0]
        return self.current_id

    def _current_model(self) -> Union[PathFileViewModel, PathEntryViewModel]:
        if self.current_id is None:
            raise Exception("Nothing selected")
        model = self.uuid.get(self.current_id)
        if model is None:
            raise Exception(f"No Model with {self.current_id}")
        return model

    def _current_parent(self, current: PathEntryViewModel) -> PathFileViewModel:
        model = self.uuid[current.parent_uuid]
        if isinstance(model, PathEntryViewModel):
            message = f"Except {PythonPathFile.__qualname__} but got {
                type(model).__qualname__}"
            raise Exception(message)
        return model

    def python_path_selected(self, event: tk.Event):
        self._get_selected_id(event)
        self.fire_selection_changed()

    def _add_path_file(self):
        if self.python is None:
            return
        name = dlg.askstring(
            parent=self.master,
            title="Neue Path Datei.",
            prompt="Bitte Namen für neue Python Path Datei eingeben."
        )
        if name is None:
            return
        site_path = self.service.user_site_package_of(self.python)
        path = site_path / f"{name}.pth"
        new_model = PathFileViewModel(path=path, content=[], changed=True)
        self.fire_event(Event.PATH_ADD, model=new_model, parent="")

    def select_directory(self) -> Optional[str]:
        directory = file.askdirectory(
            parent=self.master, initialdir=self.last_directory
        )
        if directory is None:
            return
        self.last_directory = directory
        return directory

    def _add_path_entry(self, model: PathFileViewModel):
        path = self.select_directory()
        if path is None:
            return
        self.fire_event(
            Event.PATH_ADD, model=model.create(path=path), parent=model.uuid
        )

    def path_entry_add_command(self):
        model = self._current_model()
        if isinstance(model, PathEntryViewModel):
            parent_model = self._current_parent(model)
            self._add_path_entry(parent_model)
        elif model.is_empty:
            self._add_path_entry(model)
        else:
            self._add_path_file()

    def _get_child_of(self, current: Union[PathFileViewModel, PathEntryViewModel]) -> List[PathEntryViewModel]:
        if isinstance(current, PathEntryViewModel):
            return []

        def is_parent(model: Union[PathFileViewModel, PathEntryViewModel]) -> bool:
            if isinstance(model, PathFileViewModel):
                return False
            return model.parent_uuid == current.uuid

        models = [model for _, model in self.uuid.items() if is_parent(model)]
        return [model for model in models if isinstance(model, PathEntryViewModel)]

    def _update_models_in_uuid_dict(self, models: Iterable[Union[PathFileViewModel, PathEntryViewModel]]):
        for model in models:
            self.uuid.pop(model.uuid)
            self.deleted.append(model.uuid)

    def _update_path_file_model(self, current: Union[PathFileViewModel, PathEntryViewModel],
                                models: Iterable[Union[PathFileViewModel, PathEntryViewModel]]):
        if isinstance(current, PathEntryViewModel):
            parent = self._current_parent(current)
            parent.remove(current)
        if isinstance(current, PathFileViewModel):
            for model in models:
                if not isinstance(model, PathEntryViewModel):
                    continue
                current.remove(model)

    def path_entry_remove_command(self):
        current = self._current_model()
        models = [current]
        models.extend(self._get_child_of(current))
        self.fire_event(Event.PATH_REMOVE, models=models)
        self._update_models_in_uuid_dict(models)
        self._update_path_file_model(current, models)

    def path_entry_open_command(self):
        model = self._current_model()
        if isinstance(model, PathFileViewModel):
            return
        self.show_in_explorer(model.path)

    def show_in_explorer(self, path: str):
        if not os.path.exists(path):
            return
        win_dir = os.getenv('WINDIR', "")
        explorer = os.path.join(win_dir, 'explorer.exe')
        path = os.path.normpath(path)
        subprocess.run([explorer, '/select,', path], check=False)

    def _create_py_path(self, model: PathFileViewModel) -> PythonPathFile:
        content = [model.path for model in self._get_child_of(model)]
        return PythonPathFile(path=model.path, content=content)

    def _path_file_models(self) -> List[PathFileViewModel]:
        return [model for _, model in self.uuid.items() if isinstance(model, PathFileViewModel)]

    def _create_python_path_files(self) -> List[PythonPathFile]:
        models = [self._create_py_path(model)
                  for model in self._path_file_models()]
        return models

    def path_entry_save_command(self):
        if self.python is None:
            return
        path_files = self._create_python_path_files()
        site = PythonSitePackage(python=self.python, path_files=path_files)
        self.service.save_site_package(site)
