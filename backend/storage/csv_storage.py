"""Base CSV storage class for simple file-based persistence."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Generic, TypeVar, Optional, Callable

T = TypeVar('T')


class CSVStorage(Generic[T]):
    """Base class for CSV file storage.

    Provides generic CRUD operations for CSV files.
    """

    def __init__(
        self,
        file_path: Path,
        headers: List[str],
        row_to_dict: Callable[[T], dict],
        dict_to_row: Callable[[dict], T]
    ):
        """Initialize CSV storage.

        Args:
            file_path: Path to the CSV file
            headers: List of column headers
            row_to_dict: Function to convert domain object to dict
            dict_to_row: Function to convert dict to domain object
        """
        self.file_path = file_path
        self.headers = headers
        self.row_to_dict = row_to_dict
        self.dict_to_row = dict_to_row

        # Create parent directory if it doesn't exist
        self.file_path.parent.mkdir(parents=True exist_ok=True)

        # Create file with headers if it doesn't exist
        if not self.file_path.exists():
            self._create_file()

    def _create_file(self) -> None:
        """Create CSV file with headers."""
        with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writeheader()

    def _ensure_file_exists(self) -> None:
        """Ensure the file exists, create it if not."""
        if not self.file_path.exists():
            self._create_file()

    def load_all(self) -> List[T]:
        """Load all rows from the CSV file.

        Returns:
            List of domain objects
        """
        self._ensure_file_exists()

        items: List[T] = []
        with open(self.file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    item = self.dict_to_row(row)
                    items.append(item)
                except Exception:
                    # Skip malformed rows
                    continue
        return items

    def append(self, item: T) -> None:
        """Append a new item to the CSV file.

        Args:
            item: The item to append
        """
        self._ensure_file_exists()

        row_dict = self.row_to_dict(item)
        with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.headers)
            writer.writerow(row_dict)

    def filter(self, predicate: Callable[[T], bool]) -> List[T]:
        """Filter items by predicate.

        Args:
            predicate: Function that returns True for items to keep

        Returns:
            Filtered list of items
        """
        all_items = self.load_all()
        return [item for item in all_items if predicate(item)]

    def clear(self) -> None:
        """Clear all data and re-create file with headers."""
        self._create_file()

    def count(self) -> int:
        """Get the number of rows.

        Returns:
            Number of data rows (excluding header)
        """
        if not self.file_path.exists():
            return 0
        with open(self.file_path, 'r') as f:
            return max(0, sum(1 for _ in f) - 1)
