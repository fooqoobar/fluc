import os
import tarfile

from io import BytesIO

buffer = BytesIO()


with tarfile.open('archive', 'w') as archive:
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            archive.add(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), os.getcwd()))
