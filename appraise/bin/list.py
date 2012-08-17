#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM
from django.contrib.auth.models import User

querySets = {
      "corpora":corpusM.Corpus
    , "languages":corpusM.Language
    , "sourceDocuments":corpusM.SourceDocument
    , "translatedDocuments":corpusM.TranslatedDocument
    , "translationSystems":corpusM.TranslationSystem

    , "tasks":evalM.EvaluationTask

    , "users":User
}

optionParser = optparse.OptionParser(usage="%s <object> [queries]" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
(options, args) = optionParser.parse_args()

if len(args) == 0:
    optionParser.error("You have to specify which objects to list")
try:
    querySet = querySets[args[0]]
except KeyError:
    optionParser.error("Object \"%s\" not recognized" % args[0])

queries = {}
for a in args[1:]:
    (key, value) = a.split("=")
    queries[key] = value

out = sys.stdout
if not queries:
    objects = querySet.objects.all()
else:
    objects = querySet.objects.filter(**queries)
for o in objects:
    out.write("%s\n" % o)
