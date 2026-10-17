"""Build a valid, self-contained WordPress receiver 0.3.3 ZIP (no deployment)."""
from __future__ import annotations
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
PLUGIN=ROOT/"wordpress/business-analysis-snapshot-receiver"
FILES=("business-analysis-snapshot-receiver.php","rolling-retention.php")

def create_zip(output:Path)->Path:
    main=(PLUGIN/FILES[0]).read_text(encoding="utf8")
    if "Version: 0.3.3" not in main or "rolling-retention.php" not in main:
        raise ValueError("Plugin version/header does not match 0.3.3")
    output.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(output,"w",compression=ZIP_DEFLATED) as z:
        for filename in FILES:
            source=PLUGIN/filename
            if not source.is_file():
                raise ValueError("Required bundled PHP missing: "+filename)
            z.write(source,"business-analysis-snapshot-receiver/"+filename)
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,default=ROOT/"dist/business-analysis-snapshot-receiver-v0.3.3.zip")
    args=p.parse_args()
    result=create_zip(args.output)
    print(str(result))
if __name__=="__main__":main()
