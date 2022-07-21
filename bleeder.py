import os
import collections as col
from PIL import Image, ImageColor
from fpdf import FPDF
import json
import logging

FolderConfig = col.namedtuple("FolderConfig", ["bleed", "size", "quantity", "output", "ignore", "backfile"])
FolderContents = col.namedtuple("FolderContents", ["path", "config", "backfile", "images", "folders"])
FolderData = col.namedtuple('FolderData', ["path", "backfile", "items", "folders", "config"])

class Bleeder:
    DEFAULT_BLEED = 3
    DEFAULT_SIZE = (63, 89)
    DEFAULT_QUANTITY = 3
    BLEED_FILE_MARK = "__bleed__"
    BACK_FILE_NAME = "_back."
    CONFIG_FILE_NAME = "config.ini"
    ALLOWED_EXT = ['.jpg', '.jpeg', '.png']
    LOGFILE = "bleed_log"
    DEBUG_MODE = True

    _logger = None

    def __init__(self):
        # setting logger output / format
        self._logger = logging.getLogger('bleeder')
        self._logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.path.join(os.curdir, 'log'), 'w')
        formatter = logging.Formatter("%(asctime)s;%(levelname)s;%(message)s", "%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def run(self, path: str):
        """[summary]
        Runs bleeding operation in folder specified by path (recursively),
        and merging bleeded items to pdf document(s).
        Running cleanup operation before/after execution.

        Args:
            path (string): root folder to start with
        """
        self.cleanup_folder(path)
        bleeded = self.bleed_folder(path, None, None)
        self.merge_to_pdf(path, bleeded)
        self.cleanup_folder(path)

    def _bleed_file(self, path: str, bleed: int, size: tuple):
        """Bleeds single file.
        Output file is named [filename]__bleed.ext

        Args:
            path (string): file path
            bleed (int): bleed size (mm)
            size (tuple(width, height)): card size with bleed (mm)
        Returns:
            string: saved bleed file path
        """
        bgColor = ImageColor.getrgb("#ff07b0")
        iInput = Image.open(path)
        pxInput = iInput.load()
        ratio = int(iInput.size[0] / size[0])
        pxBleed = ratio * bleed
        iOutput = Image.new("RGB", (iInput.size[0] + 2 * pxBleed - 1, iInput.size[1] + 2 * pxBleed - 1), bgColor)
        iOutput.paste(iInput, (pxBleed, pxBleed))
        pxOutput = iOutput.load()

        bleed_range = range(0, pxBleed)
        x_range = range(0, iInput.size[0])
        y_range = range(0, iInput.size[1])
        x_max = iInput.size[0] - 1
        y_max = iInput.size[1] - 1

        treshold = 50
        right = iOutput.size[0] - pxBleed
        x_left = range(pxBleed, pxBleed + treshold)
        x_right = range(right - treshold, right)
        y_check = range(pxBleed, iOutput.size[1] - pxBleed)

        for y in y_check:
            for x in x_left:
                break

            for x in x_right:
                break

        for b in bleed_range:
            #top/down range
            for x in x_range:
                pxOutput[x + pxBleed, b] = pxInput[x, 0]
                pxOutput[x + pxBleed, b + y_max + pxBleed] = pxInput[x, y_max]

            #left/right range
            for y in y_range:
                pxOutput[b, y + pxBleed] = pxInput[0, y]
                pxOutput[b + x_max + pxBleed, y + pxBleed] = pxInput[x_max, y]

            #corners range
            for b2 in bleed_range:
                pxOutput[b, b2] = pxInput[0, 0]
                pxOutput[b + x_max + pxBleed, b2] = pxInput[x_max, 0]
                pxOutput[b + x_max + pxBleed, b2 + y_max + pxBleed] = pxInput[x_max, y_max]
                pxOutput[b, b2 + y_max + pxBleed] = pxInput[0, y_max]

        split = os.path.splitext(path)
        savePath = f'{split[0]}{self.BLEED_FILE_MARK}{split[1]}'
        iOutput.save(savePath)

        printSize = lambda size: f'{size[0]}x{size[1]}'
        self._printOutput(f'bleeding {path} --> bleed: {pxBleed}, ratio: {ratio}, {printSize(iInput.size)}, {printSize(iOutput.size)}')
        return savePath

    def bleed_folder(self, path: str, backfile: str, parentConfig: FolderConfig):
        """Bleeds all files in a folder.

        Args:
            path (string): folder path
        Returns:
            FolderData
        """
        self._printOutput(f"** bleeds starting in {path}")
        if os.path.isdir(path) == False: return None

        folders = []
        results = []

        items = self._get_folder_contents(path, False)
        config = self._load_config(items.config, parentConfig)
        if config.ignore:
            return None

        # prefer config.backfile over folder backfile
        back_path = config.backfile or items.backfile
        if back_path:
            backfile = self._bleed_file(config.backfile or items.backfile, config.bleed, config.size)

        if backfile:
            for img in items.images:
                results.append(self._bleed_file(img, config.bleed, config.size))
        else:
            self._printOutput(f"Backfile is missing. Skipping items in {path}")

        for folder in items.folders:
            data = self.bleed_folder(folder, backfile, config)
            if data:
                folders.append(data)

        return FolderData(path, backfile, results, folders, config)

    def _get_folder_contents(self, path: str, bleeds_only: bool):
        """ Scans the directory (by path), and finds all the folders, images, backfile, and configfile

        Args:
            path (str): folder path to scan
            bleeds_only (bool): if True then bleed files will be assigned to images result field. Otherwise original images will be set.
        Returns:
            FolderContents
        """
        _, dirs, files = next(os.walk(path))

        # gets first element from list, or None if empty
        def first_or_none(items, fnc):
            try:
                return list(filter(fnc, items))[0]
            except:
                return None

        # gets sort key int-based, from filename if able
        def get_sort_key(filename):
            try:
                return int(os.path.splitext(filename)[0])
            except:
                return 0

        # applies fnc to items, sorts by sort key, and returns file list with full file paths
        def filter_and_map(items, fnc, sort_key):
            iter = items
            if fnc:
                iter = filter(fnc, iter)
            if sort_key:
                iter = sorted(list(iter), key = sort_key)

            return list(map(lambda f: os.path.join(path, f), iter))

        back = None
        images = []

        files = filter_and_map(files, None, get_sort_key)   # files sorted, if able, with full paths
        directories = filter_and_map(dirs, None, None)  # directories with full paths
        config = first_or_none(files, lambda f: self.CONFIG_FILE_NAME in f)

        if bleeds_only:
            images = list(filter(lambda f: self.BLEED_FILE_MARK in f, files))
        else:
            images = list(filter(lambda f: any(ext in f for ext in self.ALLOWED_EXT), files))
            back = first_or_none(images, lambda f: self.BACK_FILE_NAME in f)
            if images and back: # if both elements aren't empty, remove back file from images list
                images.remove(back)

        return FolderContents(path, config, back, images, directories)

    def merge_to_pdf(self, path: str, bleeds: FolderData):
        """Merges bleeded file in a folder into single pdf.
        Output file is named [foldername]__merged.pdf suffix

        Args:
            path (string): folder path
        Returns:
            list(string): saved paths to merged files
        """
        self._printOutput(f'** Starting merging pdf')
        rootFolder = os.path.basename(path)
        results = []

        def merge_bleeds(pdf, folder):
            size = (folder.config.size[0] + 2 * folder.config.bleed, folder.config.size[1] + 2 * folder.config.bleed)
            root = pdf is None
            if pdf is None or folder.config.output:
                pdf = FPDF('P','mm', size)

            self._printOutput(f'** Merging folder {folder.path}')
            for item in folder.items:
                self._printOutput(f'Merging file {item}')
                for q in range(folder.config.quantity):
                    pdf.add_page()
                    pdf.image(item, 0, 0, size[0], size[1])
                    pdf.add_page()
                    pdf.image(folder.backfile, 0, 0, size[0], size[1])

            for subfolder in folder.folders:
                merge_bleeds(pdf, subfolder)

            if (folder.config.output or root) and len(pdf.pages) > 0:
                # create save path based on folder tree
                dir_diff = os.path.normpath(os.path.relpath(folder.path, path)).split(os.sep)
                dir_diff.insert(0, rootFolder)

                output = "-".join(dir_diff)
                output = os.path.join(path, f"{output}.pdf")

                if os.path.exists(output):
                    self._printOutput(f"Removing old merged pdf file {output}")
                    os.remove(output)

                self._printOutput(f"Saving pdf to {output}")
                pdf.output(output, 'F')
                results.append(output)

        merge_bleeds(None, bleeds)
        return results

    def cleanup_folder(self, path: str):
        """Cleans up single folder off of a created bleed files.

        Args:
            path (string): folder path
        """
        self._printOutput(f"** cleanup starting in {path}")
        data = self._get_folder_contents(path, True)
        for img in data.images:
            self._printOutput(f'Removing file {img}')
            os.remove(img)

        for folder in data.folders:
            self.cleanup_folder(folder)

    def _load_config(self, path: str, parentConfig: FolderConfig):
        """ Loads config for folder (path). Any values in new config file will override parent confg values (if parent config exits)
            or default values otherwise.

        Args:
            path (str): path to config file
            parentConfig (FolderConfig): parent folder config (if any). Used as a template for a new config (configs are inherited top/down)
        Returns:
            FolderConfig: inherited, folder specific, or default config values
        """
        def int_with_default(value: str, default: int):
            try:
                return int(value)
            except:
                return default

        def bool_with_default(value: str, default: bool):
            try:
                return bool(value)
            except:
                return default

        config = parentConfig or FolderConfig(self.DEFAULT_BLEED, self.DEFAULT_SIZE, self.DEFAULT_QUANTITY, False, False, None)
        if path != None:
            self._printOutput(f"** Loading config {path}")
            with open(path, "r") as json_data:
                data = json.loads(json_data.read())
                bleed = int_with_default(data.get("bleed"), config.bleed)
                width = int_with_default(data.get("width"), config.size[0])
                height = int_with_default(data.get("height"), config.size[1])
                quantity = int_with_default(data.get("quantity"), config.quantity)
                output = bool_with_default(data.get("output"), False)
                ignore = bool_with_default(data.get("ignore"), False)
                backfile = data.get("backfile") or None

                return FolderConfig(bleed, (width, height), quantity, output, ignore, backfile)

        return config

    def _printOutput(self, txt: str):
        """Prints debug info

        Args:
            txt (string): text to print
        """
        if self.DEBUG_MODE:
            print(txt)
        self._logger.info(txt)
