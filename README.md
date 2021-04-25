# Deduper
Simple file deduplication with the power of the fox.

Work in progress. This is early alpha.

Deduper helps you finding and getting rid of duplicate files ("dupes"), i.e. files that are exact duplicates content-wise. Dupes may have different names and metadata (such as mtime), but they have byte-for-byte identical content and have the same size.

# How to Proceed

First you analyze a directory using

	$deduper.py -c cache.db -s C:\some\dir      # writes results to cache.json

(You can inspect cache.db for debugging purposes, if you need to. It's a simple sqlite file.)

## Edit The Report/Task File
You will want to look at the results in cache.json using your favorite editor (see below, for file format). You get groups of files that are duplicates and you can decide which ones you want to keep (keep) and which ones should be moved (rm) using the corresponding strings at the end of the line.
The report file is also known as the *task file* since it contains instructions on how to act on individual files.

## The Fox
Use fox.py to automatically change "keep" to "rm" based on certain rules and then to move the dupes:

	$fox.py -t cache.json -r keep_shortest_path # changes cache.json on disk
	$fox.py -t cache.json -move C:\temp         # moves cache to temp

# Report File Format
A multi-dimensional dictionary where dupes are grouped together and associated with an instruction (keep, rm).
The md5 hashes are sorted, but otherwise not used by the fox.

```json
{
 "00a3528cc3dfbba37b918d8eb895fd5a": {
  "C:\\Users\\Win10 Pro x64\\CrossAsia-Turfan\\Turfan-Bilder\\tif\\4250807.TA 6576 1.tif": "rm",
  "C:\\Users\\Win10 Pro x64\\CrossAsia-Turfan\\Turfan-Bilder\\tif\\4250807.TA 6576.tif": "keep"
 },
 "01411fe4e3cf98f7fef133e941ea18af": {
  "C:\\Users\\Win10 Pro x64\\CrossAsia-Turfan\\Turfan-Akten\\Akten Bilder\\0139.jpg": "keep",
  "C:\\Users\\Win10 Pro x64\\CrossAsia-Turfan\\Turfan-Akten\\Akten Bilder\\Turfan Akten 26_1_2021\\AKTEN SCANS numerisch\\0139.jpg": "rm"
 }
}
```
 
