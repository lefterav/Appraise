#!/usr/bin/env python2

import argparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM
from django.contrib.auth.models import User

# Correspondence between names and "appraise ids"
taskTypes = {"qualitychecking":"1",
             "ranking":"2",
             "select-and-post-edit":"3",
             "error-classification":"4",
             "3-wayranking":"5",
             "post-edit-all":"6"
             
}
taskFactory = {"ranking":evalM.RankingTask
               , "select-and-post-edit":evalM.SelectAndPostEditTask
               , "error-classification":evalM.ErrorClassificationTask
               , "post-edit-all":evalM.PostEditAllTask
               , "qualitychecking":evalM.QualityTask
               
}
appraiseTaskNames = ["1", "2", "2", "3", "4", "5"]
 
def dbNotFound(type, name):
        argParser.error("%s \"%s\" not found in the database" % (type, name))

argListSplit = lambda x : x.split(',')

argParser = argparse.ArgumentParser(prog=os.environ["ESMT_PROG_NAME"], add_help=False,
                                    formatter_class=argparse.RawDescriptionHelpFormatter,
                                    epilog="Following task types are recognized:\n"
                                            + "\n".join(["\t%s" % t for t in taskTypes.keys()])
                                            + "\nNote that the types are case-insensitive")
argParser.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
argParser.add_argument("-n", "--name", dest="name", help="unique descriptive name for this evaluation task", required=True)
argParser.add_argument("-t", "--task-type", dest="taskType", help="type choice for this evaluation task", required=True)
argParser.add_argument("-s", "--systems", dest="systems", help="comma separated list of systems in this evaluation task", required=True, type=argListSplit)
argParser.add_argument("-l", "--language", dest="language", help="target language", required=True)
argParser.add_argument("-c", "--corpus", dest="corpus", help="corpus to evaluate",  required=True)
argParser.add_argument("-u", "--users", dest="users", help="users allowed to work on the evaluation task", required=True, type=argListSplit)
argParser.add_argument("-e", "--error-types", dest="errorTypes", help="error types to include in the task (error classification only)", type=argListSplit)
argParser.add_argument("-R", "--no-random", dest="random", help="do not use random order", action="store_false", default=True)
argParser.add_argument("-A", "--no-active", dest="active", help="do not activate the task", action="store_false", default=True)

args = argParser.parse_args()

if evalM.EvaluationTask.objects.filter(task_name=args.name).exists():
    argParser.error("A task with name \"%s\" already exists" % args.name)

try:
    optTaskType = args.taskType.lower()
    taskType = taskTypes[optTaskType]
    isErrorClassification = (taskType == taskTypes["error-classification"])
except KeyError:
    argParser.error("Unknown task type \"%s\"" % args.taskType)

if isErrorClassification:
    if not args.errorTypes:
        argParser.error("When adding an error classification task you have to specify the error types")
    errorTypes = []
    for t in args.errorTypes:
        try:
            errorTypes.append(evalM.ErrorClassificationType.objects.get(name=t))
        except evalM.ErrorClassificationType.DoesNotExist:
            dbNotFound("Error type", t)

systems = []
for s in args.systems:
    try:
        systems.append(corpusM.TranslationSystem.objects.get(name=s))
    except corpusM.TranslationSystem.DoesNotExist:
        dbNotFound("System", s)

try:
    language = corpusM.Language.objects.get(name=args.language)
except corpusM.Language.DoesNotExist:
    dbNotFound("Language", args.language)

users=[]
for u in args.users:
    try:
        users.append(User.objects.get(username=u))
    except User.DoesNotExist: 
        dbNotFound("User", u)

try:
    corpus = corpusM.Corpus.objects.get(custom_id = args.corpus)
except corpusM.Corpus.DoesNotExist:
    dbNotFound("Corpus", args.corpus)

# Check if we have translation for all the systems (we report all the
# missing translations as to be more convenient for status checking
missingTranslations = [] # This will be a list of (document, system) pairs
for d in corpus.documents.all():
    document2corpuses = corpusM.Document2Corpus.objects.filter(corpus=corpus)
    for d2c in document2corpuses:
        for s in systems:
            document = d2c.document
            if not corpusM.TranslatedDocument.objects.filter(source=document, translation_system=s, language=language).exists():
                missingTranslations.append((document, s))
if missingTranslations:
    argParser.error("Missing translations for following documents and systems:\n%s" %
                       "\n".join(["\t%s\t%s" % (d.custom_id, s.name) for (d,s) in missingTranslations]))


# All tests done :)
task = taskFactory[args.taskType](
            task_name = args.name
          , task_type = taskType
          , corpus = corpus
          , targetLanguage = language
          , active = args.active
          , random_order = args.random
	  , context_length = 0
       )
task.save()
for s in systems:
    task.systems.add(s)
for u in users:
    task.users.add(u)
if isErrorClassification:
    task.errorTypes = errorTypes
task.save()
task.generateItems()

nItems = evalM.EvaluationItem.objects.filter(task=task).count()
print "Task \"%s\" (type: %s) generated with %d items" % (task.task_name, args.taskType, nItems)
