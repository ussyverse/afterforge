"""Create inspectable Git revisions for the documented derived examples."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args=parser.parse_args()
    root=args.destination.resolve()
    root.mkdir(parents=True, exist_ok=False)
    examples=Path(__file__).resolve().parents[1]/'examples/derived'
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT).decode().strip()
    git('init','-q')
    git('config','user.name','Agent Fix Lab')
    git('config','user.email','fixtures@example.invalid')
    for variant in ('faulty','corrected'):
        shutil.copyfile(examples/f'{variant}.py',root/'regression_subject.py')
        git('add','regression_subject.py')
        git('commit','-qm',f'{variant}: derived assumptions, not original historical implementation')
        print(json.dumps({'variant':variant,'revision':git('rev-parse','HEAD')}))


if __name__=='__main__':
    main()
