# -*- coding: utf-8 -*-

from __future__ import annotations

import logging
from abc import ABC, abstractmethod


class BaseMediaClient(ABC):
    """
    Shared public contract for photo-source / photo-target clients.

    This class documents and stabilizes the method signatures that are called
    polymorphically by features such as Automatic Migration. Backends may ignore
    context parameters they do not need, but they should still accept them so
    generic callers can interact with every client safely.
    """

    @abstractmethod
    def get_client_name(self, log_level=None):
        raise NotImplementedError

    @abstractmethod
    def create_album(self, album_name: str, shared: bool = False, log_level=None):
        raise NotImplementedError

    @abstractmethod
    def get_albums_owned_by_user(self, filter_assets=True, log_level=None):
        raise NotImplementedError

    @abstractmethod
    def get_albums_including_shared_with_user(self, filter_assets=True, log_level=None):
        raise NotImplementedError

    @abstractmethod
    def get_all_assets_from_album(
        self,
        album_id,
        album_name=None,
        type="all",
        album_scope=None,
        album_expected_count=None,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_all_assets_from_album_shared(
        self,
        album_id,
        album_name=None,
        type="all",
        album_passphrase=None,
        album_scope=None,
        album_expected_count=None,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_all_assets_without_albums(self, type="all", log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def get_all_assets_from_all_albums(self, log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def get_album_assets_size(
        self,
        album_id,
        album_name=None,
        type="all",
        album_passphrase=None,
        album_scope=None,
        log_level=None,
    ):
        raise NotImplementedError

    @abstractmethod
    def get_album_assets_count(
        self,
        album_id,
        album_name=None,
        type="all",
        album_passphrase=None,
        album_scope=None,
        log_level=None,
    ):
        raise NotImplementedError

    @abstractmethod
    def album_exists(self, album_name, shared=False, log_level=None):
        raise NotImplementedError

    @abstractmethod
    def get_assets_by_filters(
        self,
        type="all",
        is_not_in_album=None,
        is_archived=None,
        with_deleted=None,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def add_assets_to_album(self, album_id, asset_ids, album_name=None, log_level=None, return_details=False):
        raise NotImplementedError

    @abstractmethod
    def push_asset(self, file_path, log_level=None, resolve_duplicate_id=True):
        raise NotImplementedError

    @abstractmethod
    def pull_asset(
        self,
        asset_id,
        asset_filename,
        asset_time,
        download_folder="Downloaded",
        album_passphrase=None,
        album_id=None,
        album_scope=None,
        log_level=None,
    ):
        raise NotImplementedError

    @abstractmethod
    def push_albums(
        self,
        input_folder,
        subfolders_exclusion,
        subfolders_inclusion=None,
        remove_duplicates=True,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def push_no_albums(
        self,
        input_folder,
        subfolders_exclusion,
        subfolders_inclusion=None,
        remove_duplicates=True,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def push_all(self, input_folder, album_folders=None, remove_duplicates=False, log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def pull_albums(self, album_names="ALL", output_folder="Downloaded", log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def pull_no_albums(self, output_folder="Downloaded", log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def pull_all(self, output_folder="Downloaded", log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def remove_all_albums(
        self,
        remove_album_assets=False,
        request_user_confirmation=True,
        log_level=logging.WARNING,
    ):
        raise NotImplementedError

    @abstractmethod
    def remove_empty_albums(self, log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def remove_duplicates_albums(self, request_user_confirmation=True, log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def merge_duplicates_albums(self, strategy="count", request_user_confirmation=True, log_level=logging.WARNING):
        raise NotImplementedError

    @abstractmethod
    def remove_all_assets(self, log_level=logging.WARNING):
        raise NotImplementedError
