
from dataclasses import asdict, dataclass
from tkinter import (Button, Entry, Frame, Label, Misc, StringVar, Tk,
                     Toplevel, Variable, Widget)
from tkinter.constants import DISABLED, EW, GROOVE, NORMAL, NSEW, W
from tkinter.ttk import Combobox, LabelFrame, Treeview
from typing import (Any, Callable, ClassVar, Dict, Iterable, Optional, Tuple,
                    Type, TypeVar, Union)

UiElement = Union[Button, Label, Entry]
UiWidget = Union[UiElement, Frame, Widget, Treeview]

TUi = TypeVar("TUi", bound=Widget)


@dataclass
class UiArgs:
    exclude_grid: ClassVar[Iterable[str]] = [
        'padx_east', 'west_min', 'east_min'
    ]

    row: int = 0
    column: int = 0
    columnspan: int = 1
    padx: int = 2
    pady: int = 2
    ipadx: int = 2
    ipady: int = 2
    padx_east: int = 0
    east_min: int = 140
    west_min: int = 140
    sticky: str = NSEW

    def __post_init__(self):
        self.padx_east = 3 * self.padx

    def reset(self, attr: Optional[Union[str, Iterable[str]]] = None):
        attr = [attr] if isinstance(attr, str) else attr
        for name, value in UiArgs().as_args().items():
            if attr is not None and name not in attr:
                continue
            setattr(self, name, value)

    def add_row(self):
        self.row += 1

    def add_column(self):
        self.column += 1

    def as_grid(self, **kwargs) -> Dict[str, Any]:
        args = self.as_args(**kwargs)
        for attr in self.exclude_grid:
            args.pop(attr)
        return args

    def as_args(self, **kwargs) -> Dict[str, Any]:
        args = asdict(self)
        for name, value in kwargs.items():
            args[name] = value
        return args


def enable(ui_element: UiElement) -> None:
    """
    Activates the ui element

    Parameters:
    ui_element(UiElement) the element to enable
    """
    if isinstance(ui_element, Combobox):
        ui_element.configure(state='readonly')
    else:
        ui_element.configure(state=NORMAL)


def disable(ui_element: UiElement) -> None:
    """
    Deactivates the ui element

    Parameters:
    ui_element(UiElement) the element to disable
    """
    ui_element.configure(state=DISABLED)


def is_disabled(ui_element: UiElement) -> bool:
    """
    Checks if the ui element is deactivated

    Parameters:
    ui_element(UiElement) the element to disable
    """
    return ui_element['state'] == DISABLED


def visible(ui_element: UiElement) -> None:
    """
    Shows ui element visible in the grid

    Parameters:
    ui_element(UiElement) the element to show
    """
    ui_element.grid()


def hide(ui_element: UiElement) -> None:
    """
    Hides the ui element in the grid but remembers the configuration

    Parameters:
    ui_element(UiElement) the element to hide
    """
    ui_element.grid_remove()


def get_sticky(element: UiWidget) -> str:
    if (isinstance(element, (Frame, LabelFrame)) or
            (isinstance(element, Label) and element['relief'] == GROOVE)):
        return NSEW
    return EW


def setup_grid(element: TUi, args: UiArgs, column: int = -1,
               row: int = -1, columnspan: int = 1) -> TUi:
    sticky = get_sticky(element)
    row = args.row if row < 0 else row
    column = args.column if column < 0 else column
    grid_args = args.as_grid(
        row=row, column=column, columnspan=columnspan, sticky=sticky
    )
    if isinstance(element, (Button, Frame, LabelFrame)):
        grid_args.pop("ipadx")
        grid_args.pop("ipady")
    element.grid(cnf=grid_args)
    return element


def setup_button(button: Button, text: Union[str, Variable], command: Callable,
                 label: Optional[Label] = None) -> None:
    button.configure(command=command)
    if isinstance(text, Variable):
        button.configure(textvariable=text)
    elif isinstance(text, str):
        button.configure(text=text)
    if label is None:
        return
    add_label_button_1(label, command)


def add_label_button_1(label: Label, command: Callable) -> None:
    label.bind('<Button-1>', lambda _: command())


def setup_label(label: Label, text: Union[str, Variable]) -> Label:
    label.configure(anchor=W)
    if isinstance(text, str) and len(text) > 0:
        label.configure(text=text)
    elif isinstance(text, Variable):
        label.configure(textvariable=text)
    return label


def setup_read_only_label(label: Label, variable: Optional[StringVar] = None) -> Label:
    setup_label(label, '')
    label.configure(relief=GROOVE)
    if variable is not None:
        label.configure(textvariable=variable)
    return label


def setup_label_entry(label: Label, text: str,
                      entry: Entry, string_var: Variable,
                      args: UiArgs, key_event: Optional[Callable[[Any], None]] = None) -> None:
    setup_label(label, text)
    label.grid(cnf=args.as_grid())

    entry.configure(textvariable=string_var)
    args.add_column()
    entry.grid(cnf=args.as_grid())
    if key_event is None:
        return
    entry.bind("<KeyRelease>", key_event)


TUi = TypeVar("TUi")


def get_entry(event, element: Type[TUi]) -> Optional[TUi]:
    entry = event.widget
    if not isinstance(entry, element):
        return None
    return entry


def get_button_frame(master: Misc, args: UiArgs,
                     okay_cmd: Callable, cancel_cmd: Optional[Callable]) -> Frame:
    frame = Frame(master)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, minsize=args.east_min)
    frame.grid_columnconfigure(2, minsize=args.east_min)
    if cancel_cmd is not None:
        btn_cancel = Button(frame, text='Cancel',
                            command=cancel_cmd)
        grid_args = args.as_grid(row=0, column=1, sticky=EW)
        btn_cancel.grid(cnf=grid_args)
        add_okay_cancel_key_event(btn_cancel, okay_cmd,
                                  cancel_cmd)
    btn_okay = Button(frame, text='Okay',
                      command=okay_cmd)
    grid_args = args.as_grid(row=0, column=2, sticky=EW)
    btn_okay.grid(cnf=grid_args)
    add_okay_cancel_key_event(btn_okay, okay_cmd,
                              cancel_cmd)
    return frame


def add_okay_cancel_key_event(widget: Widget, okay_command: Callable[[], None],
                              cancel_command: Optional[Callable[[], None]]):
    def okay_key_command(_):
        return okay_command()
    widget.bind('<Return>', okay_key_command)
    if cancel_command is None:
        return

    def cancel_key_command(_):
        return cancel_command()
    widget.bind('<Escape>', cancel_key_command)


def center_on_screen(window: Tk, width=900, height=800):
    # get screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # calculate position x and y coordinates
    x_coord = int((screen_width/2) - (width/2))
    y_coord = int((screen_height/2) - (height/2))
    window.geometry(f'{width}x{height}+{x_coord}+{y_coord}')


def center_on_frame(frame: Misc, dialog: Toplevel):
    points = center_points(frame)
    dialog.update_idletasks()
    top_width = dialog.winfo_width()
    top_height = dialog.winfo_height()
    top_x = int(points[0] - (top_width / 2))
    top_y = int(points[1] - (top_height / 2))
    dialog.geometry(f'+{int(top_x)}+{int(top_y)}')


def center_points(frame: Misc) -> Tuple:
    top = frame.winfo_toplevel()
    width = top.winfo_width()
    height = top.winfo_height()
    middle_x = int(top.winfo_x() + (width / 2))
    middle_y = int(top.winfo_y() + (height / 2))
    return (middle_x, middle_y)
