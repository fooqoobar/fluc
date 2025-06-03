import os
import tarfile
import re


excluded = []


existing_versions = [
    f for f in os.listdir('versions')
    if f.startswith('fluc') and f.endswith('.tar')
]


if existing_versions:
    version = max(
        int(re.search(r'fluc(\d+)\.tar', f).group(1)) 
        for f in existing_versions 
        if re.search(r'fluc(\d+)\.tar', f)
    )

else:
    version = 0


with tarfile.open(f'versions/fluc{version + 1}.tar', 'w') as tar:
    for root, dirs, files in os.walk(os.getcwd()):
        dirs[:] = [d for d in dirs if d not in excluded]
        files = [f for f in files if f not in excluded]
        for file in files:
            tar.add(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), os.getcwd()))
