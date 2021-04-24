"""
Recursively scan filesystem looking for duplicates.

This script will start simple and grow from there as needed.

First, we'll work with an in-memory file cache, later 
we might add a database, depending on our own needs.

First phase: SCAN. scan dir and save state to json file.
Second phase: report duplicates. 

Identity test: files with same size and same md5

Duplicates are files

path, mtime, md5, size

cache={
    path: {
        "mtme": mtime,
        "md5": md5,
        "size": size,
    }
}
"""
import argparse
import json
import hashlib
from pathlib import Path
import pprint

class Deduper:
    # load cache if it exists
    # or start a new scan
    def __init__(self, *, cache_fn):
        self.cache = {}
        self.cache_fn = cache_fn
        if Path(self.cache_fn).exists():
            print("*Loading existing cache")
            with open(self.cache_fn) as f:
                self.cache = json.load(f)

    def scan_dir(self, *, path):
        """
        Recursively scan dir and save all files with a size > 0 bytes to a cache.

        """
        print(f"*Scan dir '{path}'")
        files = {p.resolve() for p in Path(path).glob("**/*")}
        for file in files:
            size = file.stat().st_size
            if size > 0 and not file.is_dir():
                # print (f"{file} {size}")
                self.cache[str(file)] = {"size": size, "mtime": file.stat().st_mtime}

        with open(self.cache_fn, "w") as f:
            json.dump(self.cache, f, sort_keys=True, indent=True)

    def check_identity(self):
        """
        In cache, look for files with equal size and determine md5 for them.
        """
        sizes = {}
        for path in self.cache:
            size = self.cache[path]["size"]
            if size in sizes: 
                sizes[size].append(path)
            else:
                sizes[size] = [path]     

        for size in sorted(sizes):
            if len(sizes[size]) > 1:
                #print(f"{len(sizes[size])} {sizes[size]}")
                for path in sizes[size]:
                    item = self.cache[path]
                    if item.get("md5") is None:
                        item["md5"] = self.hash_file(path)
                    #print (path)
                    #print (item)
        with open(self.cache_fn, "w") as f:
            json.dump(self.cache, f, sort_keys=True, indent=True)

        hashes = {}
        for path in self.cache:
            #print(path)
            if self.cache[path].get("md5") is not None:
                md5 = self.cache[path]["md5"]
                if md5 in hashes: 
                    hashes[md5].append(path)
                else:
                    hashes[md5] = [path]     

        pp = pprint.PrettyPrinter(indent=2)
        for md5 in sorted(hashes):
            if len(hashes[md5]) > 1:
                pp.pprint(hashes[md5])

    def hash_file(self, path):
        with open(path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
            #print(file_hash.digest())
            return file_hash.hexdigest()


if __name__ == "__main__":
    """
    USAGE
        deduper.py -c cache.json -s .
    """
    parser = argparse.ArgumentParser(description="Simple file deduper")
    parser.add_argument("-c", "--cache", required=True, help="Location of cache file")
    parser.add_argument("-s", "--scan_dir", help="Directory to scan")
    args = parser.parse_args()
    d = Deduper(cache_fn=args.cache)
    if args.scan_dir:
        d.scan_dir(path=args.scan_dir)
    d.check_identity()