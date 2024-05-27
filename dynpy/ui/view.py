
import tkinter as tk
from tkinter import Misc, ttk
from typing import Iterable, Optional, Union

from dynpy.service import EmbedPython
from dynpy.ui import utils
from dynpy.ui.controller import (Event, PathEntryViewModel, PathFileViewModel,
                                 PythonConfigController)


class PathEntryFunctions(tk.Frame):

    def __init__(self, master: Misc | None, controller: PythonConfigController) -> None:
        super().__init__(master)
        self.controller = controller
        self.args = utils.UiArgs(sticky=tk.NSEW)
        self.btn_add = tk.Button(self, text="Add")
        self.btn_remove = tk.Button(self, text="Remove")
        self.btn_save = tk.Button(self, text="Save")
        self.btn_open = tk.Button(self, text="Open Explorer")

    def setup(self, args: utils.UiArgs):
        utils.setup_button(
            button=self.btn_add, text="Add", command=self.controller.path_entry_add_command
        )
        self.btn_add.grid(cnf=self.args.as_grid())
        self.args.add_row()
        utils.setup_button(
            button=self.btn_remove, text="Remove", command=self.controller.path_entry_remove_command
        )
        self.btn_remove.grid(cnf=self.args.as_grid())
        self.args.add_row()
        utils.setup_button(
            button=self.btn_save, text="Save", command=self.controller.path_entry_save_command
        )
        self.btn_save.grid(cnf=self.args.as_grid())
        self.args.add_row()
        utils.setup_button(
            button=self.btn_open, text="Open", command=self.controller.path_entry_open_command
        )
        self.btn_open.grid(cnf=self.args.as_grid())
        self.controller.register(Event.SELECTION, self.on_selection_changed)
        self._disable_buttons()
        self.grid(cnf=args.as_grid())

    def _disable_buttons(self):
        for name, value in self.__dict__.items():
            if not name.startswith("btn_") or not isinstance(value, tk.Button):
                continue
            utils.disable(value)

    def on_selection_changed(self, python: Optional[str], path: Optional[Union[PathFileViewModel, PathEntryViewModel]]):
        self._disable_buttons()
        if python is None or path is None:
            return
        utils.enable(self.btn_save)
        utils.enable(self.btn_add)
        if isinstance(path, PathFileViewModel):
            return
        utils.enable(self.btn_remove)
        utils.enable(self.btn_open)


class PythonVersionView(tk.Listbox):

    def __init__(self, master: Misc | None, controller: PythonConfigController) -> None:
        super().__init__(master)
        self.controller = controller
        self.args = utils.UiArgs(sticky=tk.NSEW)

    def setup(self, args: utils.UiArgs):
        self.bind('<<ListboxSelect>>', self.controller.on_version_select)
        self.grid(cnf=args.as_grid())

    def populate_python_versions(self):
        self.delete(0, tk.END)
        for version in self.controller.get_python_versions():
            self.insert(tk.END, version)


class SitePackageView(ttk.Treeview):

    def __init__(self, master: Misc | None, controller: PythonConfigController) -> None:

        super().__init__(master, show="tree", selectmode=tk.BROWSE)
        self.controller = controller
        self.args = utils.UiArgs(sticky=tk.NSEW)
        self.tag = "dynpy"
        self.file_icon = tk.PhotoImage(file="")
        self.dir_icon = tk.PhotoImage(file="")

    def setup(self, args: utils.UiArgs):
        self.tag_bind(
            self.tag, "<<TreeviewSelect>>", self.controller.python_path_selected
        )
        self.controller.register(Event.PYTHON, self.on_python_version_changed)
        self.controller.register(Event.PATH_ADD, self.add_item)
        self.controller.register(Event.PATH_REMOVE, self.on_path_file_remove)
        self.grid(cnf=args.as_grid(sticky=self.args.sticky))

    def on_path_file_remove(self, models: Iterable[Union[PathFileViewModel, PathEntryViewModel]]):
        model_ids = [model.uuid for model in models]
        model_ids = [uuid for uuid in model_ids if self.exists(uuid)]
        self.delete(*model_ids)

    def add_item(self, parent: str, model: Union[PathFileViewModel, PathEntryViewModel]) -> str:
        tree_id = self.insert(
            parent, tk.END, text=model.name, image="", tags=(self.tag,)
        )
        model.uuid = tree_id
        model.parent_uuid = parent
        self.controller.uuid[tree_id] = model
        return tree_id

    def _add_python_path_content(self, parent: str, models: Iterable[PathEntryViewModel]):
        for model in models:
            self.add_item(parent=parent, model=model)

    def _add_python_path_file(self, model: PathFileViewModel):
        parent = self.add_item(parent="", model=model)
        self._add_python_path_content(parent, model.content)

    def on_python_version_changed(self, python: EmbedPython):
        self.delete(*self.get_children())
        for model in self.controller.user_site_package_of(python):
            self._add_python_path_file(model)


class PythonConfigApp(tk.Tk):

    def __init__(self, controller: PythonConfigController):
        super().__init__()
        controller.master = self
        self.title("Dynamo Python Manager")
        self.geometry("800x600")
        self.args = utils.UiArgs()
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=5)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.python = PythonVersionView(self, controller)
        self.python.setup(self.args)
        self.args.add_column()
        self.site_package = SitePackageView(self, controller)
        self.site_package.setup(self.args)
        self.args.add_column()
        self.function = PathEntryFunctions(self, controller)
        self.function.setup(self.args)
        self.python.populate_python_versions()
