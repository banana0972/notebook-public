from __future__ import annotations

from io import BytesIO
from typing import List, Type, Optional

from common import auth_instances, Item, BaseFolder, type_mappings
from db import item_created, item_removed, find_children


class DriveFile(Item):
    def upload(self, b: BytesIO, mime_type=None):
        if mime_type is not None:
            self.gfile.UpdateMetadata({"mimeType": mime_type})
        self.gfile.content = b
        self.gfile.Upload()

    def delete(self):
        self.gfile.Trash()
        item_removed(self)

    def get_preview_url(self) -> str:
        return "https://docs.google.com/document/d/"+self.id+"/edit"


class Folder(BaseFolder):
    def list_items(self) -> List[Item]:
        return find_children(self.gfile['id'])

    def create_file(self, owner: str, name: str, b: BytesIO, mimetype = None) -> DriveFile:
        item = auth_instances[owner].CreateFile({"title": name, "parents": [self.gfile['id']]})
        item.Upload() # TODO Required to get id?
        file = DriveFile(owner=owner, id=item['id'], parent=self.gfile['id']) # TODO better
        file.upload(b, mimetype)
        item_created(file)
        return file


    def create_folder(self, owner, name) -> BaseFolder:
        item = auth_instances[owner].CreateFile({"title": name, "mimeType": "application/vnd.google-apps.folder", "parents": [self.gfile['id']]})
        item.Upload()
        folder = Folder(owner=owner, id=item['id'], parent=self.gfile['id'])
        item_created(folder)
        return folder

    def delete_child(self, child_id: str):
        for child in self.list_items():
            if child.id == child_id:
                child.gfile.Delete()
                item_removed(child)


# Has no parent folder, used to hold all folders that will exist
class ParentFolder(Folder):
    # parent: Optional[str] = None

    @staticmethod
    def make(owner: str, name: str):
        item = auth_instances[owner].CreateFile({"title": name, "mimeType": "application/vnd.google-apps.folder"})
        item.Upload()
        folder = ParentFolder.model_construct(owner=owner, id=item['id'], parent=None)
        item_created(folder)



    def delete_self(self):
        self.gfile.Trash()
        item_removed(self)


# Clones all items dropped into it, one for each user it holds
class CloneAllFolder(Folder):
    pass


registered_types: list[Type[Item]] = [DriveFile, Folder, ParentFolder]
type_mappings.update({t.__name__: t for t in registered_types})