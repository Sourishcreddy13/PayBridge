import ast
from pathlib import Path


def test_all_acceptance_ids_are_represented():
    text=''.join(p.read_text() for p in Path('tests').rglob('*.py'))
    for i in range(1,11):
        assert f'AC_{i:02d}' in text
