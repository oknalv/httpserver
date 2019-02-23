import mimetypes
import re


class FileGetter:
    """ Retrieves the app files.
    """
    __APP_FOLDER = "app/"

    __MAPPINGS = {}

    @staticmethod
    def get_file(file_path):
        """ Gets a file.
        
        Args:
            file_path (str): the name of the file.

        Returns:
            A `byte` containing the file and a `str` containing the mime type.
        """
        if file_path in FileGetter.__MAPPINGS:
            file_path = FileGetter.__MAPPINGS[file_path]
        file_path = FileGetter.__APP_FOLDER + file_path
        mime_type = mimetypes.guess_type(file_path, strict=True)[0]
        data = None
        with open(file_path, "rb") as f:
            data = f.read()

        return data, mime_type

    @staticmethod
    def set_app_folder(app_folder):
        """ Sets the app folder.

        Args:
            app_folder (str): the app folder path.

        Raises:
            AppFolderWrongSyntaxException: if the app folder has wrong syntax.
        """
        if app_folder is not None and re.match(r"^[^/]+/$", app_folder):
            FileGetter.__APP_FOLDER = app_folder

        else:
            raise AppFolderWrongSyntaxException(app_folder)

    @staticmethod
    def set_file_mappings(mappings):
        """ Sets the file mappings.

        Args:
            mappings (dict of str: str): the file mappings.

        Raises:
            FileMappingsWrongTypeException: if the file mapping object has an incorrect structure.
        """
        if isinstance(mappings, dict):
            for key in mappings:
                if isinstance(key, str) and isinstance(mappings[key], str):
                    FileGetter.__MAPPINGS = mappings

                else:
                    raise FileMappingsWrongTypeException(mappings)

        else:
            raise FileMappingsWrongTypeException(mappings)


class AppFolderWrongSyntaxException(Exception):
    """ Exception to be raised if the app folder has wrong syntax.
    """
    def __init__(self, folder):
        message = "App folder should end with '/' and contain at least one character, '{}' was given".format(folder)
        super().__init__(message)


class FileMappingsWrongTypeException(Exception):
    """ Exception to be raise if the file mapping object has an incorrect structure.
    """
    def __init__(self, mappings):
        message = "File mappings should be a `dict` of `str`: `str`, '{}' given".format(mappings)
        super().__init__(message)
