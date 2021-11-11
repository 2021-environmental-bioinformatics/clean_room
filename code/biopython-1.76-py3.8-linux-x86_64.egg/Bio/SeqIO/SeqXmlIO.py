# Copyright 2010 by Thomas Schmitt.
#
# This file is part of the Biopython distribution and governed by your
# choice of the "Biopython License Agreement" or the "BSD 3-Clause License".
# Please see the LICENSE file that should have been included as part of this
# package.
"""Bio.SeqIO support for the "seqxml" file format, SeqXML.

This module is for reading and writing SeqXML format files as
SeqRecord objects, and is expected to be used via the Bio.SeqIO API.

SeqXML is a lightweight XML format which is supposed be an alternative for
FASTA files. For more Information see http://www.seqXML.org and Schmitt et al
(2011), https://doi.org/10.1093/bib/bbr025
"""

import sys

from xml.sax.saxutils import XMLGenerator
from xml.sax.xmlreader import AttributesImpl
from xml.sax import handler
from xml import sax

from Bio._py3k import basestring


from Bio import Alphabet
from Bio.Seq import Seq
from Bio.Seq import UnknownSeq
from Bio.SeqRecord import SeqRecord
from .Interfaces import SequentialSequenceWriter


class ContentHandler(handler.ContentHandler):
    """Handles XML events generated by the parser (PRIVATE)."""

    def __init__(self):
        """Create a handler to handle XML events."""
        handler.ContentHandler.__init__(self)
        self.source = None
        self.sourceVersion = None
        self.seqXMLversion = None
        self.ncbiTaxID = None
        self.speciesName = None
        self.startElementNS = None
        self.data = None
        self.records = []

    def startDocument(self):
        """Set XML handlers when an XML declaration is found."""
        self.startElementNS = self.startSeqXMLElement

    def startSeqXMLElement(self, name, qname, attrs):
        """Handle start of a seqXML element."""
        if name != (None, "seqXML"):
            raise ValueError("Failed to find the start of seqXML element")
        if qname is not None:
            raise RuntimeError("Unexpected qname for seqXML element")
        schema = None
        for key, value in attrs.items():
            namespace, localname = key
            if namespace is None:
                if localname == "source":
                    self.source = value
                elif localname == "sourceVersion":
                    self.sourceVersion = value
                elif localname == "seqXMLversion":
                    self.seqXMLversion = value
                elif localname == "ncbiTaxID":
                    # check if it is an integer, but store as string
                    number = int(value)
                    self.ncbiTaxID = value
                elif localname == "speciesName":
                    self.speciesName = value
                else:
                    raise ValueError("Unexpected attribute for XML Schema")
            elif namespace == "http://www.w3.org/2001/XMLSchema-instance":
                if localname == "noNamespaceSchemaLocation":
                    schema = value
                else:
                    raise ValueError("Unexpected attribute for XML Schema in namespace")
            else:
                raise ValueError("Unexpected namespace '%s' for seqXML attribute" % namespace)
        if self.seqXMLversion is None:
            raise ValueError("Failed to find seqXMLversion")
        url = "http://www.seqxml.org/%s/seqxml.xsd" % self.seqXMLversion
        if schema != url:
            raise ValueError("XML Schema '%s' found not consistent with reported seqXML version %s" % (schema, self.seqXMLversion))
        self.endElementNS = self.endSeqXMLElement
        self.startElementNS = self.startEntryElement

    def endSeqXMLElement(self, name, qname):
        """Handle end of the seqXML element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for seqXML end" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for seqXML end" % qname)
        if localname != "seqXML":
            raise RuntimeError("Failed to find end of seqXML element")
        self.startElementNS = None
        self.endElementNS = None

    def startEntryElement(self, name, qname, attrs):
        """Set new entry with id and the optional entry source (PRIVATE)."""
        if name != (None, "entry"):
            raise ValueError("Expected to find the start of an entry element")
        if qname is not None:
            raise RuntimeError("Unexpected qname for entry element")
        record = SeqRecord("", id=None)
        if self.speciesName is not None:
            record.annotations["organism"] = self.speciesName
        if self.ncbiTaxID is not None:
            record.annotations["ncbi_taxid"] = self.ncbiTaxID
        record.annotations["source"] = self.source
        for key, value in attrs.items():
            namespace, localname = key
            if namespace is None:
                if localname == "id":
                    record.id = value
                elif localname == "source":
                    record.annotations["source"] = value
                else:
                    raise ValueError("Unexpected attribute %s in entry element" % localname)
            else:
                raise ValueError("Unexpected namespace '%s' for entry attribute" % namespace)
        if record.id is None:
            raise ValueError("Failed to find entry ID")
        self.records.append(record)
        self.startElementNS = self.startEntryFieldElement
        self.endElementNS = self.endEntryElement

    def endEntryElement(self, name, qname):
        """Handle end of an entry element."""
        if name != (None, "entry"):
            raise ValueError("Expected to find the end of an entry element")
        if qname is not None:
            raise RuntimeError("Unexpected qname for entry element")
        self.startElementNS = self.startEntryElement
        self.endElementNS = self.endSeqXMLElement

    def startEntryFieldElement(self, name, qname, attrs):
        """Receive a field of an entry element and forward it."""
        namespace, localname = name
        if namespace is not None:
            raise ValueError("Unexpected namespace '%s' for %s element" % (namespace, localname))
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for %s element" % (qname, localname))
        if localname == "species":
            return self.startSpeciesElement(attrs)
        if localname == "description":
            return self.startDescriptionElement(attrs)
        if localname in ("DNAseq", "RNAseq", "AAseq"):
            return self.startSequenceElement(attrs)
        if localname == "DBRef":
            return self.startDBRefElement(attrs)
        if localname == "property":
            return self.startPropertyElement(attrs)
        raise ValueError("Unexpected field %s in entry" % localname)

    def startSpeciesElement(self, attrs):
        """Parse the species information."""
        name = None
        ncbiTaxID = None
        for key, value in attrs.items():
            namespace, localname = key
            if namespace is None:
                if localname == "name":
                    name = value
                elif localname == "ncbiTaxID":
                    # check if it is an integer, but store as string
                    number = int(value)
                    ncbiTaxID = value
                else:
                    raise ValueError("Unexpected attribute '%s' found in species tag", key)
            else:
                raise ValueError("Unexpected namespace '%s' for species attribute" % namespace)
        # The attributes "name" and "ncbiTaxID" are required:
        if name is None:
            raise ValueError("Failed to find species name")
        if ncbiTaxID is None:
            raise ValueError("Failed to find ncbiTaxId")
        record = self.records[-1]
        # The keywords for the species annotation are taken from SwissIO
        record.annotations["organism"] = name
        # TODO - Should have been a list to match SwissProt parser:
        record.annotations["ncbi_taxid"] = ncbiTaxID
        self.endElementNS = self.endSpeciesElement

    def endSpeciesElement(self, name, qname):
        """Handle end of a species element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for species end" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for species end" % qname)
        if localname != "species":
            raise RuntimeError("Failed to find end of species element")
        self.endElementNS = self.endEntryElement

    def startDescriptionElement(self, attrs):
        """Parse the description."""
        if attrs:
            raise ValueError("Unexpected attributes found in description element")
        if self.data is not None:
            raise RuntimeError("Unexpected data found: '%s'" % self.data)
        self.data = ""
        self.endElementNS = self.endDescriptionElement

    def endDescriptionElement(self, name, qname):
        """Handle the end of a description element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for description end" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for description end" % qname)
        if localname != "description":
            raise RuntimeError("Failed to find end of description element")
        record = self.records[-1]
        description = self.data
        if description:  # ignore if empty string
            record.description = description
        self.data = None
        self.endElementNS = self.endEntryElement

    def startSequenceElement(self, attrs):
        """Parse DNA, RNA, or protein sequence."""
        if attrs:
            raise ValueError("Unexpected attributes found in sequence element")
        if self.data is not None:
            raise RuntimeError("Unexpected data found: '%s'" % self.data)
        self.data = ""
        self.endElementNS = self.endSequenceElement

    def endSequenceElement(self, name, qname):
        """Handle the end of a sequence element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for sequence end" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for sequence end" % qname)
        if localname == "DNAseq":
            alphabet = Alphabet.generic_dna
        elif localname == "RNAseq":
            alphabet = Alphabet.generic_rna
        elif localname == "AAseq":
            alphabet = Alphabet.generic_protein
        else:
            raise RuntimeError("Failed to find end of sequence (localname = %s)" % localname)
        record = self.records[-1]
        record.seq = Seq(self.data, alphabet)
        self.data = None
        self.endElementNS = self.endEntryElement

    def startDBRefElement(self, attrs):
        """Parse a database cross reference."""
        source = None
        ID = None
        for key, value in attrs.items():
            namespace, localname = key
            if namespace is None:
                if localname == "source":
                    source = value
                elif localname == "id":
                    ID = value
                else:
                    raise ValueError("Unexpected attribute '%s' found for DBRef element", key)
            else:
                raise ValueError("Unexpected namespace '%s' for DBRef attribute" % namespace)
        # The attributes "source" and "id" are required:
        if source is None:
            raise ValueError("Failed to find source for DBRef element")
        if ID is None:
            raise ValueError("Failed to find id for DBRef element")
        if self.data is not None:
            raise RuntimeError("Unexpected data found: '%s'" % self.data)
        self.data = ""
        record = self.records[-1]
        dbxref = "%s:%s" % (source, ID)
        if dbxref not in record.dbxrefs:
            record.dbxrefs.append(dbxref)
        self.endElementNS = self.endDBRefElement

    def endDBRefElement(self, name, qname):
        """Handle the end of a DBRef element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for DBRef element" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for DBRef element" % qname)
        if localname != "DBRef":
            raise RuntimeError("Unexpected localname '%s' for DBRef element" % localname)
        if self.data:
            raise RuntimeError("Unexpected data received for DBRef element: '%s'" % self.data)
        self.data = None
        self.endElementNS = self.endEntryElement

    def startPropertyElement(self, attrs):
        """Handle the start of a property element."""
        property_name = None
        property_value = None
        for key, value in attrs.items():
            namespace, localname = key
            if namespace is None:
                if localname == "name":
                    property_name = value
                elif localname == "value":
                    property_value = value
                else:
                    raise ValueError("Unexpected attribute '%s' found for property element", key)
            else:
                raise ValueError("Unexpected namespace '%s' for property attribute" % namespace)
        # The attribute "name" is required:
        if property_name is None:
            raise ValueError("Failed to find name for property element")
        record = self.records[-1]
        if property_name not in record.annotations:
            record.annotations[property_name] = []
        record.annotations[property_name].append(property_value)
        self.endElementNS = self.endPropertyElement

    def endPropertyElement(self, name, qname):
        """Handle the end of a property element."""
        namespace, localname = name
        if namespace is not None:
            raise RuntimeError("Unexpected namespace '%s' for property element" % namespace)
        if qname is not None:
            raise RuntimeError("Unexpected qname '%s' for property element" % qname)
        if localname != "property":
            raise RuntimeError("Unexpected localname '%s' for property element" % localname)
        self.endElementNS = self.endEntryElement

    def characters(self, data):
        """Handle character data."""
        if self.data is not None:
            self.data += data


class SeqXmlIterator(object):
    """Breaks seqXML file into SeqRecords.

    Assumes valid seqXML please validate beforehand.
    It is assumed that all information for one record can be found within a
    record element or above. Two types of methods are called when the start
    tag of an element is reached. To receive only the attributes of an
    element before its end tag is reached implement _attr_TAGNAME.
    To get an element and its children as a DOM tree implement _elem_TAGNAME.
    Everything that is part of the DOM tree will not trigger any further
    method calls.
    """

    BLOCK = 1024

    def __init__(self, stream_or_path, namespace=None):
        """Create the object and initialize the XML parser."""
        self.parser = sax.make_parser()
        content_handler = ContentHandler()
        self.parser.setContentHandler(content_handler)
        self.parser.setFeature(handler.feature_namespaces, True)
        try:
            handle = open(stream_or_path)
        except TypeError:  # not a path, assume we received a stream
            self.handle = stream_or_path
            self.should_close_handle = False
        else:  # we received a path
            self.handle = handle
            self.should_close_handle = True
        # Read until we see the seqXML element with the seqXMLversion
        BLOCK = self.BLOCK
        try:
            while True:
                # Read in another block of the file...
                text = self.handle.read(BLOCK)
                if not text:
                    if content_handler.startElementNS is None:
                        raise ValueError("Empty file.")
                    else:
                        raise ValueError("XML file contains no data.")
                self.parser.feed(text)
                seqXMLversion = content_handler.seqXMLversion
                if seqXMLversion is not None:
                    break
        except Exception:
            if self.should_close_handle:
                self.handle.close()
            raise
        self.seqXMLversion = seqXMLversion
        self.source = content_handler.source
        self.sourceVersion = content_handler.sourceVersion
        self.ncbiTaxID = content_handler.ncbiTaxID
        self.speciesName = content_handler.speciesName

    def __iter__(self):
        return self

    def __next__(self):
        """Iterate over the records in the XML file."""
        content_handler = self.parser.getContentHandler()
        records = content_handler.records
        BLOCK = self.BLOCK
        try:
            while True:
                # Read in another block of the file...
                text = self.handle.read(BLOCK)
                if not text:
                    break
                self.parser.feed(text)
                if len(records) > 1:
                    # Then at least the first record is finished
                    record = records.pop(0)
                    return record
        except Exception:
            if self.should_close_handle:
                self.handle.close()
            raise
        # We have reached the end of the XML file;
        # send out the remaining records
        try:
            record = records.pop(0)
        except IndexError:
            pass
        else:
            return record
        self.parser.close()
        if self.should_close_handle:
            self.handle.close()
        raise StopIteration

    if sys.version_info[0] < 3:  # python2

        def next(self):
            """Python 2 style alias for Python 3 style __next__ method."""
            return self.__next__()


class SeqXmlWriter(SequentialSequenceWriter):
    """Writes SeqRecords into seqXML file.

    SeqXML requires the sequence alphabet be explicitly RNA, DNA or protein,
    i.e. an instance or subclass of Bio.Alphapet.RNAAlphabet,
    Bio.Alphapet.DNAAlphabet or Bio.Alphapet.ProteinAlphabet.
    """

    def __init__(
        self, handle, source=None, source_version=None, species=None, ncbiTaxId=None
    ):
        """Create Object and start the xml generator."""
        SequentialSequenceWriter.__init__(self, handle)

        self.xml_generator = XMLGenerator(handle, "utf-8")
        self.xml_generator.startDocument()
        self.source = source
        self.source_version = source_version
        self.species = species
        self.ncbiTaxId = ncbiTaxId

    def write_header(self):
        """Write root node with document metadata."""
        SequentialSequenceWriter.write_header(self)

        attrs = {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:noNamespaceSchemaLocation": "http://www.seqxml.org/0.4/seqxml.xsd",
            "seqXMLversion": "0.4",
        }

        if self.source is not None:
            attrs["source"] = self.source
        if self.source_version is not None:
            attrs["sourceVersion"] = self.source_version
        if self.species is not None:
            if not isinstance(self.species, basestring):
                raise TypeError("species should be of type string")
            attrs["speciesName"] = self.species
        if self.ncbiTaxId is not None:
            if not isinstance(self.ncbiTaxId, (basestring, int)):
                raise TypeError("ncbiTaxID should be of type string or int")
            attrs["ncbiTaxID"] = self.ncbiTaxId

        self.xml_generator.startElement("seqXML", AttributesImpl(attrs))

    def write_record(self, record):
        """Write one record."""
        if not record.id or record.id == "<unknown id>":
            raise ValueError("SeqXML requires identifier")

        if not isinstance(record.id, basestring):
            raise TypeError("Identifier should be of type string")

        attrb = {"id": record.id}

        if (
            "source" in record.annotations
            and self.source != record.annotations["source"]
        ):
            if not isinstance(record.annotations["source"], basestring):
                raise TypeError("source should be of type string")
            attrb["source"] = record.annotations["source"]

        self.xml_generator.startElement("entry", AttributesImpl(attrb))
        self._write_species(record)
        self._write_description(record)
        self._write_seq(record)
        self._write_dbxrefs(record)
        self._write_properties(record)
        self.xml_generator.endElement("entry")

    def write_footer(self):
        """Close the root node and finish the XML document."""
        SequentialSequenceWriter.write_footer(self)

        self.xml_generator.endElement("seqXML")
        self.xml_generator.endDocument()

    def _write_species(self, record):
        """Write the species if given (PRIVATE)."""
        local_ncbi_taxid = None
        if "ncbi_taxid" in record.annotations:
            local_ncbi_taxid = record.annotations["ncbi_taxid"]
            if isinstance(local_ncbi_taxid, list):
                # SwissProt parser uses a list (which could cope with chimeras)
                if len(local_ncbi_taxid) == 1:
                    local_ncbi_taxid = local_ncbi_taxid[0]
                elif len(local_ncbi_taxid) == 0:
                    local_ncbi_taxid = None
                else:
                    ValueError(
                        "Multiple entries for record.annotations['ncbi_taxid'], %r"
                        % local_ncbi_taxid
                    )
        if "organism" in record.annotations and local_ncbi_taxid:
            local_org = record.annotations["organism"]

            if not isinstance(local_org, basestring):
                raise TypeError("organism should be of type string")

            if not isinstance(local_ncbi_taxid, (basestring, int)):
                raise TypeError("ncbiTaxID should be of type string or int")

            # The local species definition is only written if it differs from the global species definition
            if local_org != self.species or local_ncbi_taxid != self.ncbiTaxId:

                attr = {"name": local_org, "ncbiTaxID": str(local_ncbi_taxid)}
                self.xml_generator.startElement("species", AttributesImpl(attr))
                self.xml_generator.endElement("species")

    def _write_description(self, record):
        """Write the description if given (PRIVATE)."""
        if record.description:

            if not isinstance(record.description, basestring):
                raise TypeError("Description should be of type string")

            description = record.description
            if description == "<unknown description>":
                description = ""

            if len(record.description) > 0:
                self.xml_generator.startElement("description", AttributesImpl({}))
                self.xml_generator.characters(description)
                self.xml_generator.endElement("description")

    def _write_seq(self, record):
        """Write the sequence (PRIVATE).

        Note that SeqXML requires a DNA, RNA or protein alphabet.
        """
        if isinstance(record.seq, UnknownSeq):
            raise TypeError("Sequence type is UnknownSeq but SeqXML requires sequence")

        seq = str(record.seq)

        if not len(seq) > 0:
            raise ValueError("The sequence length should be greater than 0")

        # Get the base alphabet (underneath any Gapped or StopCodon encoding)
        alpha = Alphabet._get_base_alphabet(record.seq.alphabet)
        if isinstance(alpha, Alphabet.RNAAlphabet):
            seqElem = "RNAseq"
        elif isinstance(alpha, Alphabet.DNAAlphabet):
            seqElem = "DNAseq"
        elif isinstance(alpha, Alphabet.ProteinAlphabet):
            seqElem = "AAseq"
        else:
            raise ValueError("Need a DNA, RNA or Protein alphabet")

        self.xml_generator.startElement(seqElem, AttributesImpl({}))
        self.xml_generator.characters(seq)
        self.xml_generator.endElement(seqElem)

    def _write_dbxrefs(self, record):
        """Write all database cross references (PRIVATE)."""
        if record.dbxrefs is not None:

            for dbxref in record.dbxrefs:

                if not isinstance(dbxref, basestring):
                    raise TypeError("dbxrefs should be of type list of string")
                if dbxref.find(":") < 1:
                    raise ValueError(
                        "dbxrefs should be in the form ['source:id', 'source:id' ]"
                    )

                dbsource, dbid = dbxref.split(":", 1)

                attr = {"source": dbsource, "id": dbid}
                self.xml_generator.startElement("DBRef", AttributesImpl(attr))
                self.xml_generator.endElement("DBRef")

    def _write_properties(self, record):
        """Write all annotations that are key value pairs with values of a primitive type or list of primitive types (PRIVATE)."""
        for key, value in record.annotations.items():

            if key not in ("organism", "ncbi_taxid", "source"):

                if value is None:

                    attr = {"name": key}
                    self.xml_generator.startElement("property", AttributesImpl(attr))
                    self.xml_generator.endElement("property")

                elif isinstance(value, list):

                    for v in value:
                        if isinstance(value, (int, float, basestring)):
                            attr = {"name": key, "value": v}
                            self.xml_generator.startElement(
                                "property", AttributesImpl(attr)
                            )
                            self.xml_generator.endElement("property")

                elif isinstance(value, (int, float, basestring)):

                    attr = {"name": key, "value": str(value)}
                    self.xml_generator.startElement("property", AttributesImpl(attr))
                    self.xml_generator.endElement("property")