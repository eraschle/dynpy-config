

from dynpy.service import PythonConfigService
from dynpy.ui.controller import PythonConfigController
from dynpy.ui.view import PythonConfigApp


def main():
    service = PythonConfigService()
    controller = PythonConfigController(service)
    app = PythonConfigApp(controller)
    app.mainloop()


if __name__ == '__main__':
    main()
