"""
Classes to read, validate and work with the input data files.
"""
from pprint import pprint
import logging
from pathlib import Path
import urllib.parse
import yaml
import json
from jsonschema import validate
from astropy.table import Table
from .info import gammacat_info

__all__ = [
    'BasicSourceInfo',
    'BasicSourceList',
    'PaperSourceInfo',
    'PaperInfo',
    'PaperList',
    'InputData',
]

log = logging.getLogger()


def load_json(path):
    path = Path(path)
    with path.open() as fh:
        data = json.load(fh)
    return data


def load_yaml(path):
    path = Path(path)
    with path.open() as fh:
        data = yaml.safe_load(fh)
    return data


class BasicSourceInfo:
    """All basic info for a source.
    """
    schema = load_yaml(gammacat_info.base_dir / 'input/schemas/basic_source_info.schema.yaml')
    # import IPython; IPython.embed(); 1/0

    def __init__(self, data):
        self.data = data

    @classmethod
    def read(cls, path):
        path = Path(path)
        data = yaml.safe_load(path.open())
        return cls(data=data)

    def __repr__(self):
        return 'BasicSourceInfo(id={})'.format(self.data.id)

    def pprint(self):
        return pprint(self.data)

    @property
    def yaml(self):
        return yaml.safe_dump(self.data, default_flow_style=False)

    def validate(self):
        validate(self.data, self.schema)


class PaperSourceInfo:
    """All info from one paper for one source.
    """

    def __init__(self, paper_id, source_id, data):
        self.paper_id = paper_id
        self.source_id = source_id
        self.data = data

    @classmethod
    def read(cls, path):
        path = Path(path)
        data = yaml.safe_load(path.open())
        return cls(paper_id=data['paper_id'], source_id=data['source_id'], data=data)

    def __repr__(self):
        return 'PaperInfo(id={})'.format(self.id)

    def validate(self):
        raise NotImplementedError


class PaperInfo:
    """All info for one paper.
    """

    def __init__(self, id, sources):
        self.id = id
        self.sources = sources

    @classmethod
    def read(cls, path):
        path = Path(path)
        id = urllib.parse.unquote(path.name)

        sources = []
        for source_path in path.glob('*.yaml'):
            source_info = PaperSourceInfo.read(source_path)
            sources.append(source_info)

        return cls(id=id, sources=sources)

    def __repr__(self):
        return 'PaperInfo(id={})'.format(self.id)

    def validate(self):
        raise NotImplementedError


class BasicSourceList:
    """
    List of `BasicSourceInfo` objects.
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def read(cls):
        path = gammacat_info.base_dir / 'input/sources'
        paths = path.glob('*.yaml')

        data = []
        for path in paths:
            if path.name in {'example.yaml'}:
                continue
            info = BasicSourceInfo.read(path)
            data.append(info)

        return cls(data=data)

    def to_table(self):
        """Convert info of `sources` list into a Table.
        """
        rows = self.to_dict()['data']
        # rows = [source.data for source in self.sources]
        # rows['papers'] = ','.join(rows)
        names = 'TODO'
        meta = dict(
            name='todo',
            version='todo',
            url='todo',
        )
        table = Table(rows=rows, names=names, meta=meta)
        return table

    def to_dict(self):
        """Format that jQuery DataTables can consume."""
        rows = []
        for source in self.data:
            data = source.data.copy()
            if data['papers'] is None or data['papers'][0] is None:
                data['papers'] = ''
            else:
                data['papers'] = ','.join(data['papers'])
            rows.append(data)
        return dict(data=rows)

    def validate(self):
        [_.validate() for _ in self.data]


class PaperList:
    """
    List of `PaperInfo` objects.
    """

    def __init__(self, data):
        self.data = data

    @classmethod
    def read(cls):
        path = gammacat_info.base_dir / 'input/papers'
        paths = path.glob('*')

        data = []
        for path in paths:
            info = PaperInfo.read(path)
            data.append(info)

        return cls(data=data)

    def validate(self):
        [_.validate() for _ in self.data]


class InputData:
    """
    Read all data from the `input` folder.

    Expose it as Python objects that can be validated and used.
    """

    def __init__(self, sources=None, papers=None):
        self.path = gammacat_info.base_dir / 'input'
        self.sources = sources
        self.papers = papers

    @classmethod
    def read(cls):
        """Read all data from disk.
        """
        sources = BasicSourceList.read()
        papers = PaperList.read()
        return cls(sources=sources, papers=papers)

    def __str__(self):
        ss = 'Input data summary:\n'
        ss += 'Path: {}\n'.format(self.path)
        ss += 'Number of sources: {}\n'.format(len(self.sources.data))
        ss += 'Number of papers: {}\n'.format(len(self.papers.data))
        return ss
