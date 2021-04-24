"""
fox.py: Deduper's Red Companion. 

USAGE
    fox.py --task report.json -rule keep_shortest_path
    #manually proof-read and edit the task file 
    fox.py --move to/dir

fox.py processes the report file created by deduper and moves files 
according to the instruction in the report file (aka task file).

You can manually proof read and correct the report file before you
delete any dupes. 

Rules implemented so far:
    keep_shortest_path

"""
import argparse
import json
import shutil
from pathlib import Path

class Fox():
    def __init__(self, *, task): 
        self.task_fn = Path(task).resolve
        with open(task) as f:
            self.tasks = json.load(f)

    def move(self, *, target): 
        print(f"*move {target}")
        
        for group in self.tasks:
            for path in self.tasks[group]:
                try:
                    shutil.move(path, target)
                except shutil.Error as e:
                    print(e.args[0])
                    
    def rule(self, *, name): 
        if name == "keep_shortest_path": 
            self.keep_shortest_path()
        else:
            raise TypeError ("Error: Unknown rule!")
        self.write_json()

    def keep_shortest_path(self):
        print("*r:keep_shortest_path")

        for group in self.tasks:
            shortestPath = None
            ln = 10000        
            for path in self.tasks[group]:
                if len(path) < ln:
                    shortestPath = path
                    ln = len(path)
            for path in self.tasks[group]:
                if path != shortestPath:
                    self.tasks[group][path] = "rm"
        
    def write_json(self):
        print(f"*saving json {self.task_fn}")
        with open(str(self.task_fn), "w") as f:
            json.dump(self.tasks, f, sort_keys=True, indent=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduper's clever companion")
    parser.add_argument("-t", "--task", required=True, help="Location of report file")
    parser.add_argument("-m", "--move", help="Instead of deleting files move them to specified dir")
    parser.add_argument("-r", "--rule", help="Specify rule to apply to dupes listed in report file")
    args = parser.parse_args()
    
    f = Fox(task=args.task)
    if args.rule is not None:
        f.rule(name=args.rule)
    else:
        f.move(target=args.move)
        