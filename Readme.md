# Bleeder

Bleeder is a Python script for bleeding playing cards for print, and merging them into single pdf,
one card per page.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install depedencies.

```bash
pip install -r requirements
```

## Usage

```python
import bleeder

path = '' #path to your folder containing cards
Bleeder().run(path)
```

## Cards folder structure

- Allowed image extensions (for bleeding) are: ``*.jpg``, ``*.png``.
- Folder has to specify card back, this can be done in two ways:
  * by a file named ``_back.jpg``/``_back.png``, placed in a folder
  * by a setting a ``backfile`` property of a folder config (see ``config.ini`` section)
- Folders can have a config.ini file, for configuration (see ``config.ini`` section)
- Folders can be nested. Sub folders are inhering parent folder backside file, and config file.

## Config.ini

Folder may have a config.ini file, for overriding the default settings.
Config.ini should be json formatted file.
Accepted fields are:
- ``bleed``: for setting the bleed width (mm). Value: ``integer``.
- ``size``: for setting the size of a target card (mm). Value: ``Tuple(width, height)``.
- ``quantity``: every card repetitions per pdf. Value: ``Integer``
- ``output``: makes separate pdf out of a folder (and subfolders, unless subfolders have output set to True). Value: ``True/False``
- ``ignore``: skips folder. Value: ``True/False``
- ``backfile``: path to backfile used in folder (and subfolders, unless subfolders have own backfile setting set). Value: ``string``

Example config.ini file:
```json
{
    "bleed": 3,
    "size": (63, 92),
    "quantity": 3,
    "output": True,
    "ignore": False,
    "backfile": "/home/xx/backfiles/back.jpg"
}
```

## Issues

When encountering issues with bleeding & merging cards, consult ``log`` file in root dir.

## Contributing
not open yet.
