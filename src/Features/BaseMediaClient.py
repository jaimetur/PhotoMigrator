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
