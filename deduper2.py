"""
Recursively scan filesystem looking for duplicates.

Second iteration of the script using sqlite.

Scan dir recursively for size. Determine md5 if size is not unique.
If md5s are not unique, report that.

This is a rewrite using sqlite for persistence and to save memory. It's
quite obvious that I dont have much experience with sql.
"""

import argparse
import hashlib
from pathlib import Path
#import pprint
import sqlite3

class Deduper2:
    # load cache if it exists
    # or start a new scan
    def __init__(self, *, cache_fn):
        self.init_db(cache_fn)
        #self.p = pprint.PrettyPrinter(indent=2)

    def add_md5(self):
        """
        In db, look for files with equal size and determine md5 for them.
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
        Check for files with non-unique md5s and report'em to STDOUT.
        """

        print ("*Checking for records with non-unique hash")
        
        cursor = self.con.execute(
            "SELECT md5 FROM Files GROUP BY md5 HAVING count(*) > 1"
        )
        for md5 in cursor.fetchall():
            if md5[0] is not None:
                cursor = self.con.execute(
                    "SELECT path FROM Files " +
                    "WHERE md5 = ?", (md5)
                )
                print("---")
                for path in cursor.fetchall():
                    print(path[0])
        
    def hash_file(self, path):
        """Return md5 for path"""
        
        #print(f"*hash*{path[0]}")
        with open(str(path), "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
            return file_hash.hexdigest()

    def init_db(self,db_fn):
        if Path(db_fn).exists():
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
        cursor = self.con.execute(
            "SELECT path FROM Files WHERE size = ? AND md5 IS NULL", size
        )
        
        #currently we update md5 even if md5 exists already
        #TODO: only update if mtime has changed
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

    #not currently used
    def read_db (self):
        cursor = self.con.cursor()
        print("read_db")
        rows = cursor.execute("SELECT path, size, mtime, md5 FROM Files").fetchall()
        print(rows)

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
        
        Not used anymore.
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
                    

if __name__ == "__main__":
    """
    USAGE
        deduper.py -c cache.db -s scan\dir
    """
    parser = argparse.ArgumentParser(description="Simple file deduper")
    parser.add_argument("-c", "--cache", required=True, help="Location of cache file")
    parser.add_argument("-s", "--scan_dir", help="Directory to scan")
    args = parser.parse_args()
    d = Deduper2(cache_fn=args.cache)
    if args.scan_dir:
        d.scan_cache(scan_dir=args.scan_dir)
        d.scan_dir(path=args.scan_dir)
        d.add_md5()
    d.check_md5() # at this point we report all dupes known to the db
    d.con.close() # could be from multiple scan_dirs; that's up to user
