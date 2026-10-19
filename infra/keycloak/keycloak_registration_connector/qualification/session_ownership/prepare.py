#!/usr/bin/env python3
"""Prepare exact native job/context source and preserved controls; never deploy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import types


def prepare(source,output,mode,qualification_root=None):
    if mode not in {"native","limited","integrated"} or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("Reviewed mode and separate owned output required")
    fixture=Path(__file__).resolve().parent
    shared=qualification_root if qualification_root is not None else fixture.parent
    inputs=json.loads((fixture/"inputs.json").read_text())
    for root,rows in [(source,inputs["native_sources"]),(shared,inputs["reused_files"])]:
        for row in rows:
            p=root/row["path"]
            if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest()!=row["sha256"]:
                raise ValueError("Unreviewed native source or prior control bytes")
    recipe=shared/"native_abort/prepare.py"
    module=types.ModuleType("reviewed_native_abort_prepare");module.__file__=str(recipe)
    exec(compile(recipe.read_bytes(),str(recipe),"exec"),module.__dict__)
    module.prepare(source,output,mode,qualification_root=shared)
    shutil.copyfile(fixture/"pom.xml",output/"pom.xml")
    shutil.copytree(fixture/"src",output/"src",dirs_exist_ok=True)
    for row in inputs["native_sources"]:
        dest=output/"src/main/java"/row["path"].split("/src/main/java/",1)[1]
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/row["path"],dest)
    record=dict(mode=mode,new_native_overlay=False,exact_additional_native_sources=inputs["native_sources"],prior_native_abort_controls_and_negative_oracles_unchanged=True,mandatory_ownership_or_enforceable_exclusion_proved=False,complete_cleanup_SQL_JTA_HTTP_or_durable_admission_proved=False)
    (output/"session-ownership-overlay.json").write_text(json.dumps(record,indent=2)+"\n")
    return record


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path);parser.add_argument("output",type=Path)
    parser.add_argument("mode",choices=["native","limited","integrated"])
    args=parser.parse_args();print(json.dumps(prepare(args.source,args.output,args.mode),sort_keys=True))
