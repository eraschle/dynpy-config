

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Union


USER_SITE_PATH = Path(os.getenv("USERPROFILE", "")) / "AppData" / "Roaming" / "Python"


@dataclass(frozen=True)
class PythonPathFile:
    path: Path
    content: Iterable[str]

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_empty(self) -> bool:
        return len(list(self.content)) == 0


@dataclass(frozen=True)
class EmbedPython:
    path: Path
    major: int
    minor: Union[int, str]
    tag: Union[int, str] = field(compare=False)
    architecture: str = field(compare=False)

    @property
    def short_version(self) -> str:
        return f"{self.major}.{self.minor}"

    @property
    def long_version(self) -> str:
        return f"{self.major}.{self.minor}.{self.tag}"

    @property
    def full_name(self) -> str:
        return f"Python {self.long_version}"


@dataclass(frozen=True)
class PythonSitePackage:
    python: EmbedPython
    path_files: Iterable[PythonPathFile]


PYTHON_PATTERN = re.compile(
    r"python-(?P<major>\d+).(?P<minor>[0-9a-zA-Z]{,4}).(?P<tag>[0-9a-zA-Z]{,5})-embed-(?P<arch>.*).zip$"
)


def user_site_pkg_path(python: EmbedPython) -> Path:
    version = f"Python{python.major}{python.minor}"
    return USER_SITE_PATH / version / "site-packages"


def read_path_file(file: Path) -> List[str]:
    with file as f:
        content = f.read_text(encoding="utf-8")
        return content.splitlines(keepends=False)


def _get_path(path: str) -> str:
    wsl_mount = "/mnt/c/"
    if path.startswith(wsl_mount):
        path = path.removeprefix(wsl_mount)
        path = f"C:/{path}"
    return path.replace("\\", "/")


def write_path_file(path_file: PythonPathFile) -> None:
    lines = [_get_path(line) for line in path_file.content]
    content = "\n".join(lines)
    with path_file.path as f:
        f.write_text(data=content, encoding="utf-8")


def path_files_from(site_package: Path, extension: Optional[str] = None) -> Generator[PythonPathFile, None, None]:
    extension = extension or "*.pth"
    for path in site_package.glob(extension):
        content = read_path_file(path)
        yield PythonPathFile(path, content)


def site_package_from(python: EmbedPython, extension: Optional[str] = None) -> PythonSitePackage:
    site_package = user_site_pkg_path(python)
    return PythonSitePackage(
        python=python,
        path_files=path_files_from(site_package, extension)
    )


def save_site_package(site: PythonSitePackage) -> None:
    for path_file in site.path_files:
        if path_file.is_empty:
            os.remove(path_file.path)
        else:
            write_path_file(path_file)


def embed_versions(search_path: Path) -> List[EmbedPython]:
    versions = []
    for path in search_path.glob("*.zip"):
        match = PYTHON_PATTERN.match(path.name)
        if match is None:
            continue
        versions.append(
            EmbedPython(
                major=int(match.group("major")),
                minor=match.group("minor"),
                tag=match.group("tag"),
                architecture=match.group("arch"),
                path=path
            ))
    return versions


def _is_embed_python(name: str, embed: EmbedPython) -> bool:
    return embed.short_version in name


def embed_python_by(name: str, search_path: Path) -> Optional[EmbedPython]:
    for embed in embed_versions(search_path):
        if not _is_embed_python(name, embed):
            continue
        return embed
    return None


class PythonConfigService:
    # embed_path = Path(os.getenv("%LOCALAPPDATA%", ""))
    embed_path = Path(os.getenv("USERPROFILE", "")) / "AppData" / "Local"

    def embed_versions(self) -> List[EmbedPython]:
        return embed_versions(self.embed_path)

    def embed_python_by(self, name: str) -> Optional[EmbedPython]:
        if name is None or len(name.strip()) == 0:
            return None
        return embed_python_by(name, self.embed_path)

    def site_package_from(self, embed: EmbedPython) -> PythonSitePackage:
        return site_package_from(embed)

    def save_site_package(self, site: PythonSitePackage) -> None:
        return save_site_package(site)

    def user_site_package_of(self, embed: EmbedPython) -> Path:
        return user_site_pkg_path(embed)
