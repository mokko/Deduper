"""
Deduper.py - Simple File Deduplication With The Power Of The Fox

Deduper recursively scans directory looking for duplicates. It prepares 
a report of duplicate files (aka "dupes"). The fox helps with picking
which files should stay/be removed and carries out the (re)moving of the 
dupes.

Logarithm
-Scan dir recursively for size. Determine md5 only if size is not unique.
-Report cases where md5s are not unique.

This is a rewrite using sqlite for persistence and to save memory. It's
quite obvious that I dont have much experience with sql. Also report to
json for semi-automatic handling of deletes is being added.

USAGE
    deduper.py -c cache.db -s scan\dir # scans a new directory
    deduper.py -c cache.db             # writes report to cache.json
"""

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
#import pprint

class Deduper:
    def __init__(self, *, db_fn):
        self.db_fn = Path(db_fn).resolve()
        self.init_db(self.db_fn)
        #self.p = pprint.PrettyPrinter(indent=2)

    def add_md5(self):
        """
        In the db, look for files with equal size and determine md5 for them.
        """
        print("*non unique file sizes")
        cursor = self.con.cursor()
        sizes = cursor.execute(
            "SELECT size FROM Files GROUP BY size HAVING count(*) > 1"
        ).fetchall()
        #print(sizes)
        
        print("*filling in MD5")
        # sizes with multiple files
        for size in sizes: 
            self.update_existing_md5s(size)
            self.mk_missing_md5s (size) # only files without md5

    def check_md5(self):
        """
        Check for files with non-unique md5s and report'em to a json file,
        the report or task file.
        """

        print ("*Checking for records with non-unique hash")
        
        cursor = self.con.execute(
            "SELECT md5 FROM Files GROUP BY md5 HAVING count(*) > 1"
        )
        result = defaultdict(dict)
        for md5 in cursor.fetchall():
            if md5[0] is not None:
                cursor = self.con.execute(
                    "SELECT path FROM Files " +
                    "WHERE md5 = ?", (md5)
                )
                for path in cursor.fetchall():
                    result[md5[0]][path[0]] = "keep"
        self.write_report(result)
        
    def hash_file(self, path):
        """Return md5 for path"""
        
        #print(f"*hash*{path[0]}")
        with open(str(path), "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
            return file_hash.hexdigest()

    def init_db(self,db_fn):
        if db_fn.exists():
            print("*Loading existing db")
            self.con = sqlite3.connect(db_fn)
        else:
            print("*Making new db")
            self.con = sqlite3.connect(db_fn)
            self.con.execute("""
            CREATE TABLE Files(
                path TEXT PRIMARY KEY NOT NULL,
                size  INT NOT NULL,
                mtime INT NOT NULL,
                md5 TEXT);""")
    
    def mk_missing_md5s(self, size):
        """
        For files of a given size that have no md5, create md5s. 
        """
        cursor = self.con.execute(
            "SELECT path FROM Files WHERE size = ? AND md5 IS NULL", size
        )
        
        for file in cursor.fetchall():
            md5 = self.hash_file(file[0])
            #print(f"!!!{file[0]}:{md5}")
            cursor.execute(
                "UPDATE Files SET md5 = ? WHERE path = ?",(md5, file[0]) 
            )
        self.con.commit()
            
    def scan_cache(self, *, scan_dir):
        """
        Check if file representations in db still exist on disk. Delete 
        representations if file doesn't exist anymore.

        We do this only for paths inside scan_dir.
        """
        scan_dir = str(Path(scan_dir).resolve())
        expr = scan_dir+'%'
        print(f"scancache: {scan_dir}")
        cursor = self.con.execute(
            "SELECT path FROM Files WHERE path LIKE ?", (expr,)
        )
        
        for path in cursor.fetchall():
            if not Path(path[0]).exists():
                cursor = self.con.execute(
                    "DELETE FROM Files WHERE path = ?", (path,)
                )
        self.con.commit()
            # print(f"!cache: {path[0]}")
        
    def scan_dir(self, *, path):
        """
        Recursively scan dir files with a size > 0 bytes and save a list of 
        file to db. 
        """

        print(f"*Scan dir '{path}'")
        files = {p.resolve() for p in Path(path).glob("**/*")}
        for file in files:
            if file.stat().st_size > 0 and not file.is_dir():
                self.upsert2(file)

    def update_existing_md5s(self, size):
        """
        Check if files have changed since last run and update
        md5s if necessary.
        """
        cursor = self.con.execute(
            "SELECT path, mtime FROM Files WHERE md5 IS NOT NULL"
        )

        for (path, mtime) in cursor.fetchall():
            print(path, mtime)
            if mtime != Path(path).stat().st_mtime:
                md5 = self.hash_file(path)
                cursor.execute(
                    "UPDATE Files SET md5 = ? WHERE path = ? AND size = ?",(md5, path, size) 
                )                
        self.con.commit()
        
    def upsert(self, file):
        """
        Not actually an upsert, but close enough. Existing md5s get 
        overwritten.
        Problem with this upsert us that md5s get overwritten every time.
        
        Not used anymore. We keep it anyways for educational purposes.
        """
        cursor = self.con.cursor()
        print (f"upsert {file}")
        cursor.execute(
            "INSERT OR REPLACE INTO Files VALUES (?, ?, ?, NULL)",
            (str(file), file.stat().st_size, file.stat().st_mtime)
        )
        self.con.commit()
    
    def upsert2(self, file):
        """
        If file representation doesn't exist yet in db, make it. Update 
        existing file representation if file has changed. Keep existing 
        md5 if file has stayed the same, otherwise discard it.
        """
        
        print (f"upsert2 {str(file)}")
        cursor = self.con.cursor()
        mtime = cursor.execute(
            "SELECT mtime FROM Files WHERE path = ?", (str(file),)
        ).fetchone()
        if mtime:
            #print (f"file is represented in db already")
            if file.stat().st_mtime != mtime[0]:
                #print("Need to update representation")
                cursor.execute(
                    """UPDATE Files 
                    SET size = ?, mtime = ?, md5 = NULL 
                    WHERE path = ?""",
                    (file.stat().st_size, file.stat().st_mtime, str(file)) 
            )

        else:
            #print("Need to insert new representation")
            cursor.execute(
                "INSERT INTO Files VALUES (?,?,?, NULL)",
                (str(file), file.stat().st_size, file.stat().st_mtime)
            )
        self.con.commit()

    def write_report(self, report):
        """ 
        Writes report file (aka task file). Filename is derrived from
        cache file.
        """
        task_fn = self.db_fn.with_suffix('.json')
        print(f"*About to write report to {task_fn}")
        with open(task_fn, "w") as f:
            json.dump(report, f, sort_keys=True, indent=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple file deduper")
    parser.add_argument("-c", "--cache", required=True, help="Location of cache file")
    parser.add_argument("-s", "--scan_dir", help="Directory to scan")
    args = parser.parse_args()
    d = Deduper(db_fn=args.cache)
    if args.scan_dir:
        d.scan_cache(scan_dir=args.scan_dir)
        d.scan_dir(path=args.scan_dir)
        d.add_md5()
    d.check_md5() # at this point we report all dupes known to the db
    d.con.close() # could be from multiple scan_dirs; that's up to user
