import typing as t

# AssetTable is a dictionary of asset types mapped to dictionaries of xml:ids to hashes of the source of that xml:id.
AssetTable = t.Dict[str, str]
