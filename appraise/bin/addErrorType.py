#!/usr/bin/env python2

import argparse

import os

import evaluation.models as evalM

argParser = argparse.ArgumentParser(prog=os.environ["ESMT_PROG_NAME"], add_help=False)
argParser.add_argument("-h", "--help", action="help", help=argparse.SUPPRESS)
argParser.add_argument("name", help="Name for the error type")
args = argParser.parse_args()

if evalM.ErrorClassificationType.objects.filter(name=args.name):
    argParser.error("Error class \"%s\" already exists in the database" % args.name)

errorType = evalM.ErrorClassificationType(name=args.name)
errorType.save()
