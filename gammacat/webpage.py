# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Make gamma-cat webpage (in combination with Sphinx).
"""
import logging
import shutil
import urllib.parse
from gammapy.catalog import GammaCatResourceIndex
from .input import BasicSourceList
from .info import gammacat_info
from .utils import load_json, jinja_env, load_yaml
from pathlib import Path

__all__ = [
    'WebpageConfig',
    'WebpageMaker',
]

log = logging.getLogger(__name__)


class WebpageConfig:
    """Config options for webpage maker."""

    def __init__(self, *, out_path):
        self.out_path = out_path


class WebpageMaker:
    """Make rst-files for gamma-cat webpage."""

    def __init__(self, config):
        self.config = config

        self.resource_index_input = GammaCatResourceIndex.from_list(load_json(
            gammacat_info.in_path / 'input-datasets.json'
        ))
        self.resource_index_output = GammaCatResourceIndex.from_list(load_json(
            gammacat_info.out_path / 'gammacat-datasets.json'
        ))

        self.sources_data = self.make_sources_data()
        self.references_data = self.make_references_data()

    def make_sources_data(self):
        # TODO: we shouldn't be accessing stuff from the input folder
        # in the webpage generation! Change to use output folder.
        sources_data = BasicSourceList.read().to_dict()['data']
        # Add some infos that we will use from the website templates
        for source in sources_data:
            add_source_info_for_templates(source)
        return sources_data

    def make_references_data(self):
        reference_ids = self.resource_index_output.unique_reference_ids
        # At the moment this contains "basic source info" entries
        # which we don't want here. This is a hacky way to skip them
        # (not sure if it works properly or also skips other stuff accidentally)
        # TODO: implement this in a proper way
        del reference_ids[0]

        references_data = []
        for reference_id in reference_ids:
            references_data.append(make_reference_data(reference_id))

        return references_data

    def run(self):
        log.info('Make webpage ...')

        self.make_source_list_page()
        self.make_source_detail_pages()

        self.make_reference_list_page()
        self.make_reference_detail_pages()

        self.copy_data()
        self.copy_catalog()

    def make_source_list_page(self):
        ctx = {'sources': self.sources_data}

        template = jinja_env.get_template('source_list.txt')
        txt = template.render(ctx)

        path = gammacat_info.webpage_path / 'data/source_list.rst'
        log.info(f'Writing {path}')
        path.write_text(txt)

    def make_reference_list_page(self):
        ctx = {'references': self.references_data}

        template = jinja_env.get_template('reference_list.txt')
        txt = template.render(ctx)

        path = gammacat_info.webpage_path / 'data/reference_list.rst'
        log.info(f'Writing {path}')
        path.write_text(txt)

    def make_source_detail_pages(self):
        path = gammacat_info.webpage_path / 'data/sources/'
        path.mkdir(exist_ok=True)
        for source in self.sources_data:
            self.make_source_detail_page(source)

    def make_reference_detail_pages(self):
        path = gammacat_info.webpage_path / 'data/references/'
        path.mkdir(exist_ok=True)
        for reference in self.references_data:
            self.make_reference_detail_page(reference)

    def make_source_detail_page(self, source):
        resources = [
            self.make_resource_info_for_template(resource)
            for resource in self.resource_index_output.resources
            if resource.source_id == source['source_id']
        ]
        # The first resource is the basic source info
        # We have that separately, so we skip it here
        resources = resources[1:]

        ctx = {
            'source': source,
            'resources': resources,
        }
        template = jinja_env.get_template('source_detail.txt')
        txt = template.render(ctx)

        path = gammacat_info.webpage_path / f'data/sources/{source["source_id"]}.rst'
        log.info(f'Writing {path}')
        path.write_text(txt)

    def make_reference_detail_page(self, reference):
        resources = []
        for resource in (
                self.resource_index_output.query('reference_id == {!r}'.format(reference['reference_id']))).resources:
            resources.append(dict(self.make_resource_info_for_template(resource)))
        ctx = {'reference': reference, 'resources': resources}
        template = jinja_env.get_template('reference_detail.txt')
        txt = template.render(ctx)

        path = gammacat_info.webpage_path / f'data/references/{reference["reference_id"]}.rst'
        log.info(f'Writing {path}')
        path.write_text(txt)

    def make_resource_info_for_template(self, resource):
        input_resource = find_resource(self.resource_index_input, resource)

        # This is a bit of a hack: we need to URL encode the resource "location",
        # because for reference identifiers with a "&" character, the filename
        # contains "%26", and the "%" in that filename has to be URL encoded again
        # to get the right URL linking to that file, resulting in "%2526"
        # See https://en.wikipedia.org/wiki/Percent-encoding
        # or https://gamma-cat.readthedocs.io/contribute/details.html#reference-identifiers
        url_input = urllib.parse.quote(input_resource.location)
        url_output = urllib.parse.quote(resource.location)

        resource = resource.__dict__.copy()
        resource['url_input'] = url_input
        resource['url_output'] = url_output
        resource['url_input_github'] = f'https://github.com/gammapy/gamma-cat/tree/master/input/{url_input}'
        resource['url_output_github'] = f'https://github.com/gammapy/gamma-cat/tree/master/output/{url_output}'
        resource['url_webpage'] = f'../../output/{resource["url_output"]}'
        return resource

    def copy_data(self):
        """Copy output data folder to docs HTML output folder,
        so that the data files are available from the website
        """
        src = gammacat_info.out_path / 'data'
        dst = gammacat_info.webpage_path / '_build/html/output/data'

        # log.info(f'mkdir {dst}')
        # dst.mkdir(parents=True, exists_ok=True)
        if dst.is_dir():
            log.info(f'rm {dst}')
            shutil.rmtree(str(dst))

        log.info(f'cp {src} {dst}')
        shutil.copytree(str(src), str(dst))

    def copy_catalog(self):
        src = gammacat_info.out_path
        dst = gammacat_info.webpage_path / '_build/html/output/'
        
        shutil.copyfile(str(gammacat_info.out_path / 'gammacat.fits.gz'), str(dst / 'gammacat.fits.gz'))
        shutil.copyfile(str(gammacat_info.out_path / 'gammacat.ecsv'), str(dst / 'gammacat.ecsv'))
        shutil.copyfile(str(gammacat_info.out_path / 'gammacat.yaml'), str(dst / 'gammacat.yaml'))


def add_source_info_for_templates(source):
    source['basic_info_path'] = f'input/sources/tev-{source["source_id"]:06d}.yaml'
    source['basic_info_url'] = f'https://github.com/gammapy/gamma-cat/blob/master/{source["basic_info_path"]}'
    source['gamma_sky_url'] = f'http://gamma-sky.net/#/cat/tev/{source["source_id"]}'
    source['name_and_id'] = f'{source["common_name"]} (ID: {source["source_id"]})'
    source['source_title_underline'] = '-' * len(source['name_and_id'])
    source['tevcat_name_and_id'] = f'{source["tevcat_name"]} (ID: {source["tevcat_id"]})'
    source['tevcat_url'] = f'http://tevcat.uchicago.edu/?mode=1;id={source["tevcat_id"]}'

    source['ads_records'] = [make_ads_record(_) for _ in source['reference_ids']]


def make_reference_data(reference_id):

    subfolder = reference_id[:4]
    reference_id_folder = urllib.parse.quote(urllib.parse.quote(reference_id))
    input_url = f'input/data/{subfolder}/{reference_id_folder}'
    input_url_github = f'{gammacat_info.input_url}/data/{subfolder}/{reference_id_folder}'
    output_url = f'output/data/{subfolder}/{reference_id_folder}'
    output_url_github = f'{gammacat_info.output_url}/data/{subfolder}/{reference_id_folder}'

    info_path = gammacat_info.in_path / 'data' / f'{reference_id[:4]}/{urllib.parse.quote(reference_id)}' / 'info.yaml'
    info_data = load_yaml(info_path)

    return dict(
        reference_title_underline='-' * len(reference_id),
        reference_id=reference_id,
        ads_record=make_ads_record(reference_id),
        input_url=input_url,
        output_url=output_url,
        input_url_github=input_url_github,
        output_url_github=output_url_github,
        info_data=info_data,
    )


def make_ads_record(reference_id):
    return dict(
        reference_id=reference_id,
        url=f'https://ui.adsabs.harvard.edu/#abs/{reference_id}',
    )


def find_resource(resource_index, r):
    for r2 in resource_index.resources:
        if (
                (r.reference_id == r2.reference_id) and
                (r.source_id == r2.source_id) and
                (r.file_id == r2.file_id) and
                (r.type == r2.type)
        ):
            return r2
    else:
        log.error(f'Missing resource: {r}')
        r2 = r.__class__(**r.__dict__)
        r2.location = 'N/A'
        return r2
        # raise IndexError('Missing input resource!')
