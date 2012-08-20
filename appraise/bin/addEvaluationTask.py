#!/usr/bin/env python2

import optparse
import os
import sys

import corpus.models as corpusM
import evaluation.models as evalM
from django.contrib.auth.models import User

validTaskTypes = ["QualityChecking", "Ranking", "Post-editing", "ErrorClassification", "3-WayRanking"]
appraiseTaskNames = ["1", "2", "3", "4", "5"]
 

class customHelpOptionParser(optparse.OptionParser):
    def print_help(self):
        optparse.OptionParser.print_help(self)
        out = sys.stdout
        out.write("\nFollowing task types are recognized:\n")
        out.write("\n".join(["\t%s" % t for t in validTaskTypes]))
        out.write("\nNote that the types are case-insensitive\n")

optionParser = customHelpOptionParser(usage="%s [options] -n <NAME> -t <TASKTYPE> -s <SYSTEMS> -l <LANGUAGE> -c <CORPUS> -u <USERS>" % os.environ["ESMT_PROG_NAME"], add_help_option=False)
optionParser.add_option("-h", "--help", action="help", help=optparse.SUPPRESS_HELP)
optionParser.add_option("-n", "--name", dest="name", help="unique descriptive name for this evaluation task")
optionParser.add_option("-t", "--task-type", dest="taskType", help="type choice for this evaluation task")
optionParser.add_option("-s", "--systems", dest="systems", help="comma separated list of systems in this evaluation task")
optionParser.add_option("-l", "--language", dest="language", help="target language")
optionParser.add_option("-c", "--corpus", dest="corpus", help="corpus to evaluate")
optionParser.add_option("-u", "--users", dest="users", help="users allowed to work on the evaluation task")
optionParser.add_option("-R", "--no-random", dest="random", help="do not use random order", action="store_false", default=True)
optionParser.add_option("-A", "--no-active", dest="active", help="do not activate the task", action="store_false", default=True)

(options, args) = optionParser.parse_args()

if not options.name:
    optionParser.error("You have to provide a name for the task")
if evalM.EvaluationTask.objects.filter(task_name=options.name).exists():
    optionParser.error("A task with name \"%s\" already exists" % options.name)

if not options.taskType:
    optionParser.error("You have to provide a type for the task")
posOfType = [n for n,t in enumerate([x.lower() for x in validTaskTypes]) if t == options.taskType.lower()]
if not posOfType:
    optionParser.error("Unknown task type \"%s\"" % options.taskType)
taskType = appraiseTaskNames[posOfType[0]] # Note: posOfType is still a list

if not options.systems:
    optionParser.error("You have to provide systems for this evaluation task")
systems = []
for s in options.systems.split(","):
    try:
        systems.append(corpusM.TranslationSystem.objects.get(name=s))
    except corpusM.TranslationSystem.DoesNotExist:
        optionParser.error("System \"%s\" not found in the database" % s)

if not options.language:
    optionParser.error("You have to specify a target language")
try:
    language = corpusM.Language.objects.get(name=options.language)
except corpusM.Language.DoesNotExist:
    optionParser.error("Language \"%s\" does not exist" % options.language)

if not options.users:
    optionParser.error("You have to specify users for this evaluation task")
for u in options.users.split(","):
    users=[]
    try:
        users.append(User.objects.get(username=u))
    except User.DoesNotExist: 
        optionParser.error("User \"%s\" not found" % u)

if not options.corpus:
    optionParser.error("You have to provide a corpus for this evaluation task")
try:
    corpus = corpusM.Corpus.objects.get(custom_id = options.corpus)
except corpusM.Corpus.DoesNotExist:
    optionParser.error("Corpus \"%s\" not found in the database" % s)

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
    optionParser.error("Missing translations for following documents and systems:\n%s" %
                       "\n".join(["\t%s\t%s" % (d.custom_id, s.name) for (d,s) in missingTranslations]))


# All tests done :)
task = evalM.EvaluationTask(
            task_name = options.name
          , task_type = taskType
          , corpus = corpus
          , targetLanguage = language
          , active = options.active
          , random_order = options.random
       )
task.save()
for s in systems:
    task.systems.add(s)
for u in users:
    task.users.add(u)
task.save()
