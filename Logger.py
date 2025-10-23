# -*- coding: UTF-8 -*-
"""
Copyright (c) 2023 Gouvernement du Québec
SPDX-License-Identifier: LiLiQ-R-1.1
License-Filename: LICENSES/EN/LiLiQ-R11unicode.txt
"""
import logging
from pathlib import Path

class Logging:
    """Classe de logging qui écrit dans un fichier log les éléments spécifiquement mentionné 
    par log_message. Tous les messages visibles dans la console du terminal ne sont pas écrits 
    par défaut, du à l'élément "CustomLogger" dans l'initialisation.

    Raises:
        Exception: Si Logger n'a pas été instancié.
        ValueError: Lorsque le type de message n'est pas dans la liste de choix.
    """
    _logger = None  # Attribut de classe pour stocker l'instance de logger
    _output_name = None  # Attribut de classe pour le nom du fichier de log

    def __init__(self, output_name: str):
        # Reconfigurer le logger uniquement si le fichier change
        self.logs_directory = Path(__file__).parent / 'logs'
        self.log_file = self.logs_directory / output_name
        if Logging._output_name != self.log_file:
            Logging._output_name = self.log_file
            self._initialize_logger(self.log_file.as_posix())

    @classmethod
    def _initialize_logger(cls, output_name: str):
        # Si un logger existe déjà, fermer les handlers pour libérer le fichier précédent
        if cls._logger is not None:
            for handler in cls._logger.handlers:
                handler.close()
                cls._logger.removeHandler(handler)
        
        cls._logger = logging.getLogger("CustomLogger")
        file_handler = logging.FileHandler(output_name, mode="w")  # mode "w" pour écraser
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        cls._logger.addHandler(file_handler)
        cls._logger.setLevel(logging.INFO)
        cls._logger.info(f"Logging initialized. Output file: {output_name}")

    @classmethod
    def log_message(cls, level: str, message: str):
        """Permet d'écrire un message dans le fichier log en y associant un niveau de
        d'importance.

        Args:
            level (str): Le type d'importance (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message (str): Le message qui sera écrit dans le log

        Raises:
            Exception: Si Logger n'a pas été instancié.
            ValueError: Lorsque le type de message n'est pas dans la liste de choix.
        """
        if cls._logger is None:
            raise Exception("Logger has not been initialized. Instantiate Logging first.")

        # Choisir le niveau de log en fonction du paramètre level
        if level == "DEBUG":
            print(f'\033[92m{message}\033[0m')
            cls._logger.debug(message)
        elif level == "INFO":
            print(f'\033[96m{message}\033[0m')
            cls._logger.info(message)
        elif level == "WARNING":
            print(f'\033[93m{message}\033[0m')
            cls._logger.warning(message)
        elif level == "ERROR":
            print(f'\033[91m{message}\033[0m')
            cls._logger.error(message)
        elif level == "CRITICAL":
            print(f'\033[95m{message}\033[0m')
            cls._logger.critical(message)
        else:
            raise ValueError(f"{level} is not a valid level (DEBUG, INFO, WARNING, ERROR, or CRITICAL)")