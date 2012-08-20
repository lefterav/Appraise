#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM

order = [
      "taskId"
    , "taskName"
    , "sourceDocument"
    , "sourceSentence"
    , "user"
    , "duration"
    , "results"
]

baseQueryObjects = {
      "ranking":evalM.RankingResult
    , "post-editing":evalM.PosteditingResult
}

def formatRankingResult(r, fields):
    for rank in r.results.all():
        system = corpusM.TranslatedDocument.objects.get(id=rank.translation.document.id).translation_system
        fields.append(":".join([system.name, str(rank.rank)]))

def formatPosteditingResult(r, fields):
    if r.fromScratch:
        fields.append("fromScratch:YES")
    else:
        fields.append("fromScratch:NO")
    #system = corpusM.TranslatedDocument.objects.get(id=r.system)
    fields.append(r.system.name)
    fields.append(r.sentence)

formatFunctions = {
      "ranking":formatRankingResult
    , "post-editing":formatPosteditingResult
}

optionParser = optparse.OptionParser(usage="%s <options> [<queries>]" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
optionParser.add_option("-H", "--header", help="Show header", action="store_true", dest="showHeader")
optionParser.add_option("-d", "--delimiter", help="Delimiter for fields (default: #)",
                        metavar="SEP", default=" # ")
(options, args) = optionParser.parse_args()

out = sys.stdout

if options.showHeader:
    string = options.delimiter.join(order)
    out.write("%s\n" % string)
    out.write("%s\n" % ("-" * len(string.expandtabs())))
    sys.exit(0)

if len(args) == 0:
    optionParser.error("You have to specify which kind of task")

taskType = args[0].lower()
if taskType not in baseQueryObjects.keys():
    optionParser.error("Task type \"%s\" not recognized" % args[0])

if len(args) == 1:
    results = baseQueryObjects[taskType].objects.all()
else:
    queries = {}
    for a in args:
        (key, value) = a.split("=")
        queries[key] = value
    results = baseQueryObjects.objects.filter(**queries)
    
for r in results:
    evalItem = r.item
    evalTask = evalItem.task
    sourceSentence = evalItem.source_sentence
    sourceDocument = corpusM.SourceDocument.objects.get(id=sourceSentence.document.id)
    fields = []

    fields.append(evalTask.task_id)
    fields.append(evalTask.task_name)
    
    fields.append(sourceDocument.custom_id)
    
    fields.append(sourceSentence.custom_id)
    
    fields.append(r.user.username)
    
    fields.append('{}'.format(r.duration))
    
    if r.skipped:
        fields.append("__SKIPPED__")
    else:
        formatFunctions[taskType](r, fields)
    
    out.write("%s\n" % options.delimiter.join(fields))
