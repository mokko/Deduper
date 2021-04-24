# Deduper
Simple file deduplication with the power of the fox.

Work in progress. This is early alpha.

Deduper helps you finding and getting rid of duplicate files ("dupes"), i.e. files that are exact duplicates content-wise. Dupes may have different names and metadata (such as mtime), but they have byte for byte identical content and have the same size.

# How to Proceed

First you analyze a directory using

	$deduper.py -c cache.db -s C:\some\dir #writes results to cache.json

(You can inspect cache.db for debugging purposes, if you need to. It's a simple sqlite file.)

## Edit The Report/Task File
You will want to look at the results in cache.json using you favorite editor (see below, for file format). You get groups of files that are duplicates (same content) and you can decide which ones you want to keep (keep) and which ones should be moved (rm).

## The Fox
Use fox.py to automatically change "keep" to "rm" based on certain rules and then to move the dupes:

	$fox.py -t cache.json -r keep_shortest_path
	$fox.py -t cache.json -move C:\temp

#Report File Format
The report file is also known as the task file since it contains instructions which file are to
be moved and which ones can stay.

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
 
