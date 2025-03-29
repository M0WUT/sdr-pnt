# Standard library imports
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Third-party library imports

# Local imports


def conditional_path_file_handler(
    filename: str, mode: str = "a", encoding=None, *args, **kwargs
):
    # Preferred location is on M.2 SSD to reduce wear on eMMC
    # If /mnt/media/nvme exists, the log will be put there
    # otherwise it will be in the folder the script runs from
    ssd_path = Path("/") / "mnt" / "media" / "nvme"
    logfile_path = ssd_path / filename if ssd_path.exists() else Path(filename)
    logfile_path.parent.mkdir(parents=True, exist_ok=True)

    return RotatingFileHandler(
        filename=logfile_path, mode=mode, encoding=encoding, *args, **kwargs
    )
