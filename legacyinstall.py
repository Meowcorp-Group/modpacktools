import shutil
import zipfile
import json
import hashlib
import urllib.request
from urllib.parse import urlparse
from pathlib import Path
from typing import List, Dict

# configuration
ACCEPTED_DOMAINS = ['cdn.modrinth.com', 'github.com', 'raw.githubusercontent.com', 'gitlab.com']

cwd = Path.cwd() / 'modpacktools' / 'legacyinstall'

ResourceList = List[Dict[str, str]]

def loadModpack(modpack: Path) -> dict:
	if not modpack.exists():
		print('Error: File not found:', modpack)
		exit(1)

	# check if it's a zip file (extension may not be .zip)
	if not zipfile.is_zipfile(modpack):
		print('Error: Not a zip file:', modpack)
		exit(1)

	# make a directory for the modpack
	modpack_dir = cwd / modpack.stem / 'pack'
	if not modpack_dir.exists():
		modpack_dir.mkdir(parents=True)
		print('Created directory:', modpack_dir)
		# extract the zip file
		with zipfile.ZipFile(modpack, 'r') as zip_ref:
			zip_ref.extractall(modpack_dir)
			print('Extracted:', modpack)
	else:
		print('Directory already exists, skipping extract')

	# check for a `modrinth.index.json`
	index = modpack_dir / 'modrinth.index.json'
	if not index.exists():
		print('Error: Not a Modrinth modpack:', modpack)
		exit(1)

	# read the index file
	with index.open('r') as f:
		data = json.load(f)

	if data['formatVersion'] != 1:
		print('Error: Unsupported format version:', data['formatVersion'])
		print('Only format version 1 is supported, please open an issue.')
		exit(1)

	return data

def getMods(data: dict) -> ResourceList:
	resources: ResourceList = [] # [{url: "url", path: "path", hash: "hash"}]
	for file in data['files']:
		url = file['downloads'][0]
		path = file['path']
		hash = file['hashes']['sha1']

		domain = urlparse(url).netloc
		if domain not in ACCEPTED_DOMAINS:
			print('Error: Unsupported domain:', domain)
			print('Only the following domains are supported:', ACCEPTED_DOMAINS)
			exit(1)

		# append to get
		resources.append({'url': url, 'path': path, 'hash': hash})

	return resources

def downloadMods(modpack: Path, resources: ResourceList) -> None:
	installDir = cwd / modpack.stem / 'install'
	installDir.mkdir(parents=True, exist_ok=True)

	for resource in resources:
		url = resource['url']
		path = resource['path']
		hash = resource['hash']
		file = installDir / path

		file.parent.mkdir(parents=True, exist_ok=True)

		if file.exists():
			print('File already exists, skipping:', path)
			continue

		# download the file
		print('Downloading:', url)
		try:
			with urllib.request.urlopen(url) as response:
				data = response.read()
				# check hash
				digest = hashlib.sha1(data).hexdigest()
				print('SHA1:', digest)
				print('Expected:', hash)

				if digest != hash:
					print('Error: Hash mismatch:', path)
					exit(1)
				
				print('File OK')
				# write to file
				with file.open('wb') as f:
					f.write(data)
				
		except Exception as e:
			print('Error: Failed to download:', url)
			print(e)
			exit(1)

def copyOverrides (modpack: Path) -> None:
	pack = cwd / modpack.stem / 'pack'
	overrides =pack / 'overrides'
	if not overrides.exists():
		print('No overrides, skipping copy')
		return
	
	print('Copying overrides')
	installDir = cwd / modpack.stem / 'install'

	try:
		shutil.copytree(overrides, installDir, dirs_exist_ok=True)
	except Exception as e:
		print('Error: Failed to copy overrides')
		print(e)
		exit(1)

	# copy modrinth.index.json for reference
	shutil.copy(pack / 'modrinth.index.json', installDir / 'modrinth.index.json')


def main() -> None:
	print('legacyinstall: install modrinth modpack for legacy-based launchers')

	user = input('Drag the modpack file here and press enter: ')
	modpack = Path(user.strip().replace("'", '').replace('"', ''))

	cwd.mkdir(parents=True, exist_ok=True)

	index = loadModpack(modpack)
	resources = getMods(index)
	downloadMods(modpack, resources)
	copyOverrides(modpack)

	print('Done!')

if __name__ == '__main__':
	main()