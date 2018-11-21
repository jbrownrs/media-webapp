"""
Matterhorn record parsing

"""
import logging

from lxml import etree

from . import models
from .namespaces import MATTERHORN_NAMESPACE, OAI_NAMESPACE, MEDIAPACKAGE_NAMESPACE


LOG = logging.getLogger(__name__)


def ensure_matterhorn_record(record):
    """
    Ensure that a MatterhornRecord object exists for the passed Record. Like get_or_create, returns
    an object, created tuple.

    """
    if record.metadata_format.namespace != MATTERHORN_NAMESPACE:
        LOG.info('Not updating record for wrong namespace')
        return

    # Get or create the associated MatterhornRecord
    matterhorn_record, created = models.MatterhornRecord.objects.get_or_create(record=record)
    if created:
        LOG.info('Created matterhorn record for %s', record.identifier)

    # OK, so it's a bit unpleasant that we re-parse the XML here even though sickle will already
    # have parsed it. OTOH, I really like the fact that the parsing of specialised record types is
    # decoupled from creation so I'm living with it for the moment. -- RJW
    root = etree.fromstring(record.xml)

    # lxml requires that all tags have their namespaces be specified. One can do this with
    # something like element.find('{http://alice.local/ns1}foo/{http://bob.local/ns2}bar') but that
    # quickly gets unwieldy. This mapping can be passed to all find() functions to allow namespaces
    # to be specified via short names like they are in XML itself. So, with the namespace
    # configuration below, one can search for a "mediapackage" tag from the media package namespace
    # which is contained within an "metadata" tag from the OAI namespace using the more friendly
    # search path 'oai:metadata/m:mediapackage' rather than having to, e.g. use
    # f'{{{OAI_NAMESPACE}}}metadata/{{{MEDIAPACKAGE_NAMESPACE}}}mediapackage'.
    namespaces = {
        'oai': OAI_NAMESPACE,
        'm': MEDIAPACKAGE_NAMESPACE,
    }

    # Find the media package element
    mediapackage = root.find('./oai:metadata/m:mediapackage', namespaces=namespaces)
    if mediapackage is None:
        raise RuntimeError(f'No media package found in record {record.identifier}')

    # A dictionary which holds attributes to be set on the record.
    attrs = {}

    # Get title/description of package.
    attrs['title'] = mediapackage.findtext('./m:title', namespaces=namespaces) or ''
    attrs['description'] = mediapackage.findtext('./m:description', namespaces=namespaces) or ''

    # Update record if necessary
    if any(getattr(matterhorn_record, k) != v for k, v in attrs.items()):
        LOG.info('Updating record "%s"', record.identifier)
        for k, v in attrs.items():
            setattr(matterhorn_record, k, v)
        matterhorn_record.save()

    return matterhorn_record, created