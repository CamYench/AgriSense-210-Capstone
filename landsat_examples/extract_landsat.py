import logging
import sys
import tarfile
from enum import Enum
from pathlib import Path

import typer
from rich import print
from typing_extensions import Annotated


class Product(str, Enum):
    ndvi = "NDVI"
    evi = "EVI"


def extract_tar_file(tar_path: Path, dest_dir: Path, product: Product):
    print(f"Extracting {tar_path.name}")
    with tarfile.open(tar_path, "r:gz") as tar:
        all_members = tar.getnames()
        for member in all_members:
            if product in member:
                print(f"Found {product.value} in {member}")
                tar.extract(member=member, path=dest_dir)


def extract_main(
    tar_path: Annotated[
        Path,
        typer.Argument(
            help="Path to the tar.gz file or directory of tar.gz files to extract"
        ),
    ],
    dest_dir: Annotated[
        Path,
        typer.Argument(help="Path to destination directory to place extracted files."),
    ],
    product: Annotated[
        Product,
        typer.Argument(help="Specific products to extract from the tar.gz files."),
    ],
):
    """Extracts products from the tar file at the tar_path to the dest_dir"""

    # check dest_dir exists
    dest_dir.mkdir(exist_ok=True)
    dest_tar_dir = dest_dir / product.value
    dest_tar_dir.mkdir(exist_ok=True)

    # check if the tar_path is a directory
    if tar_path.is_dir():
        extract_dir = typer.confirm(
            f"{tar_path} is a directory. Extract all tar.gz files in directory?"
        )
        # did not confirm, abort
        if not extract_dir:
            print("Not extracting")
            typer.Abort()
            sys.exit()

        # extract all tars in dir
        for tar_file in tar_path.iterdir():
            if tar_file.suffix == ".gz":
                extract_tar_file(tar_file, dest_dir=dest_tar_dir, product=product)

    # tar_path is not a dir, just a singular file
    else:
        extract_tar_file(tar_path=tar_path, dest_dir=dest_tar_dir, product=product)


if __name__ == "__main__":
    typer.run(extract_main)
