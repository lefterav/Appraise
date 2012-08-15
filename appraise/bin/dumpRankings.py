#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM

optionParser = optparse.OptionParser(usage="%s <options>" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-s", "--separator", help="Separator for fields (default: tab)",
                        metavar="SEP", default="\t")
(options, args) = optionParser.parse_args()

rankings = evalM.RankingResult.objects.all()
for r in rankings:
    evalItem = r.item
    evalTask = evalItem.task
    sourceSentence = evalItem.source_sentence
    sourceDocument = corpusM.SourceDocument.objects.get(id=sourceSentence.document.id)
    fields = []

    fields.append(evalTask.task_id)
    fields.append(evalTask.task_name)

    fields.append(sourceDocument.custom_id)

    fields.append(sourceSentence.custom_id)

    if r.skipped:
        fields.append("__SKIPPED__")
    else:
        for rank in r.results.all():
            system = corpusM.TranslatedDocument.objects.get(id=rank.translation.document.id).translation_system
            fields.append(":".join([system.name, str(rank.rank)]))
    
    print options.separator.join(fields)

