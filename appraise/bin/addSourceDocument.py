#!/usr/bin/env python2

import codecs
import optparse
import os.path
import sys

import corpus.models as models

optionParser = optparse.OptionParser(usage="%s [options] -l LANG <file>" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
optionParser.add_option("-l", "--language", dest="language", help="source language (required)", metavar="LANG")
optionParser.add_option("-i", "--id", dest="id", help="id of the document (if not given, the filename will be taken)",
                  metavar="ID")
optionParser.add_option("-u", "--unique-sentence-id", help="create a (hopefully) unique sentence id for each sentence in the corpus", dest="uniqueSentenceId", action="store_true")
optionParser.add_option("-C", "--no-corpus", dest="noCorpus", help="do not create a corpus for this document", action="store_true")
(options, args) = optionParser.parse_args()

if len(args) == 0:
    optionParser.error("You have to give a file to import data from")
if len(args) > 1:
    optionParser.error("Importing more than one document at a time is not supported yet")
if not options.language:
    optionParser.error("No language given")
if not options.id:
    options.id = os.path.basename(args[0])

log = sys.stdout

try:
    language = models.Language.objects.get(name=options.language)
except models.Language.DoesNotExist:
    sys.stderr.write("Error: language \"%s\" not found in the database!\n" % options.language)
    sys.exit(1)

if models.SourceDocument.objects.filter(custom_id=options.id, language=language):
    sys.stderr.write("Error: document \"%s\" (%s) already exists in the database!\n"
                     % (options.id, language.english_name))
    sys.exit(1)

fp = codecs.open(args[0], encoding="utf8")

# Document creation
log.write("Importing corpus \"%s\" from %s (language: %s)...\n" % (options.id, args[0], language.english_name))
d = models.SourceDocument(custom_id=options.id, language=language)
d.save()

# Adding the sentences
for (n, l) in enumerate(fp):
    #s = d.sourcesentence_set.create(text=l.strip())
    s = models.SourceSentence(text=l.strip())
    s.document = d
    if not options.uniqueSentenceId:
        s.custom_id = "%d" % (n+1)
    else:
        s.custom_id = "%s__%d" % (d.custom_id, (n+1))
    s.save()
d.save()
log.write("Document \"%s\" stored in database with %d sentences.\n" % (d.custom_id, len(d.sentence_set.all())))

# Corpus creation
if not options.noCorpus:
    c = models.Corpus(custom_id=options.id, language=language)
    c.save()
    c2d = models.Document2Corpus(document=d, corpus=c, order=0)
    c2d.save()
    log.write("Created corpus \"%s\" with this document.\n" % options.id)
