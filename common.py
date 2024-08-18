from __future__ import annotations

from functools import cached_property
from io import BytesIO
from typing import Dict, List, Type, Optional

from pydantic import BaseModel, computed_field, ConfigDict, Field
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

auth_instances: Dict[str, GoogleDrive] = {}
type_mappings: Dict[str, Type[Item]] = {}


class Item(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    # TODO: This field is currently writeonly(?), it is only to be used when inserting into db. Figure out a way to lazy load this ig.
    parent: Optional[str] = None
    owner: str
    # TODO File id should be constant and can be cached somehow

    @computed_field(repr=False)
    @cached_property
    def gfile(self) -> GoogleDriveFile:
        return auth_instances[self.owner].CreateFile({'id': self.id})


    def can_read(self, user: str):
        return user == self.owner

    def can_write(self, user: str):
        return user == self.owner

    def switch_owner(self, new_owner: str):
        pass # Not important rn


    @property
    def filetype(self) -> str:
        return type(self).__name__


class BaseFolder(Item):
    def list_items(self) -> List[Item]:
        pass

    def create_file(self, owner: str, name: str, b: BytesIO, mimetype = None) -> Item: # TODO This should return a DriveFile but circular imports
        pass

    def create_folder(self, owner, name) -> BaseFolder:
        pass

    def delete_child(self, child_id: str):
        pass


