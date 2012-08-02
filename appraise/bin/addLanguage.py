#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as models

optionParser = optparse.OptionParser(usage="%s <options> <document>" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
optionParser.add_option("-i", "--id", dest="id", help="language id (2 characters)", metavar="ID")
optionParser.add_option("-l", "--language", dest="language", help="language name", metavar="LANG")
optionParser.add_option("-n", "--native", dest="native", help="native language name", metavar="LANG")
(options, args) = optionParser.parse_args()

if not options.id:
    optionParser.error("No language id given")
if not options.language:
    optionParser.error("No language name given")
if not options.native:
    sys.stderr.write("Warning: no native language name given, taking english name")
    options.native = options.language

log = sys.stdout

if models.Language.objects.filter(name=options.id).exists():
    sys.stderr.write("Error: language \"%s\" already exists in the database\n" % options.id)
    sys.exit(1)

l = models.Language(name=options.id, english_name=options.language, native_name=options.native)
l.save()
log.write("Language %s => %s added to the database\n" % (l.name, l.english_name))
